# Bloqueos de despliegue

Fecha: 2026-11-09

Estos bloqueos requieren credenciales o acciones manuales que no están disponibles en el entorno del agente.

---

## B-01 — InsForge: RESUELTO

**Proyecto:** `c7578dc0-d532-4463-88f1-09c6e54356f7`
**URL:** `https://<insforge-project-id>.eu-central.insforge.app`
**DB host:** `<insforge-project-id>.eu-central.database.insforge.app`
**Región:** `eu-central`

La `ik_` key es una **project API key**, no una `uak_` de usuario. Se enlazó correctamente con:

```bash
npx @insforge/cli link \
  --api-base-url https://<insforge-project-id>.eu-central.insforge.app \
  --api-key ik_...
```

`db connection-string` devolvía una URL con una contraseña enmascarada/placeholder (8 caracteres). La contraseña real (32 caracteres) se obtiene de:

```text
GET /api/metadata/database-password
```

y se inserta en la URL de:

```text
GET /api/metadata/database-connection-string
```

**Estado verificado:**

- `alembic current` → `c9d0e1f2a3b4 (head)` (actualizado el 2026-11-10 desde `d4e5f6a7b8c9`).
- 11 tablas creadas (`users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens`, `alembic_version`).
- Smoke test real contra InsForge: **12/12 checks** (health, registro, login, equipo, proyecto, tarea, comentario, subida/descarga de adjunto, búsqueda, notificaciones, error envelope).
- La app puede conectarse con SQLAlchemy usando `DB_SSLMODE=require`.

**Nota:** la `DATABASE_URL` real está en `.env` (ignorado por git) y debe configurarse en Render.

---

## B-02 — Vercel: RESUELTO

**Estado verificado:** 2026-11-10

- CLI autenticada como `chorexxs` (`vercel whoami`).
- Proyecto `chorexxs-projects/taskflow-api` vinculado.
- Root Directory: `frontend`; framework Vite; build `npm run build`; output `dist`.
- `VITE_API_URL=https://taskflow-api-gkgl.onrender.com` en Production, Preview y Development.
- Repositorio `Chorexxs/taskflow-api` ya conectado a Vercel.
- Deploy de producción `dpl_73iXa7KraFmfrN9KEvpoFULU2Pog` → `https://taskflow-api-tau.vercel.app` (`READY`).
- `frontend/vercel.json` incluye rewrite SPA y headers de seguridad (CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- `.vercelignore` evita subir `.env`, `.env.local`, backend, tests y specs.
- Verificado con navegador: `/login` carga, fuentes y assets `200`, `POST /api/v1/auth/login` fallido devuelve `401` sin errores CSP y CORS correcto.

**Pendiente (no bloqueante):** autenticar el MCP de Vercel en OpenCode (`/mcps` → `vercel` → sign in). El servidor ya está configurado y aparece como `needs authentication`.

---

## B-03 — Render: RESUELTO

Se actualizaron las variables del servicio `srv-d82qnghj2pic73aqr5l0`:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://postgres:<db-password>@<insforge-project-id>.eu-central.database.insforge.app:5432/insforge?sslmode=require
DB_SSLMODE=require
CORS_ORIGINS=https://taskflow-api-tau.vercel.app,https://<insforge-project-id>.insforge.site
STORAGE_BACKEND=database
```

Deploy `dep-dbpetfo8v5cc73e2lgug` → **live**.

**Verificado:**

```text
GET https://taskflow-api-gkgl.onrender.com/health/ready
→ 200 {"status":"ready","database":"connected"}
```

Smoke test de producción: **13/13** (health, registro, login, equipo, proyecto, tarea, comentario, adjunto, descarga, búsqueda, notificaciones, perfil, error envelope).

CORS:

```text
Origin https://<insforge-project-id>.insforge.site → permitido
Origin https://taskflow-api-tau.vercel.app → permitido
Origin https://evil.example → sin cabecera CORS
```

---

## B-04 — Docker daemon

**Comando ejecutado:**

```bash
docker build -t taskflow-api:local .
```

**Salida:**

```text
ERROR: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Docker Desktop no está iniciado, así que la imagen no se pudo construir localmente. El `Dockerfile` se actualizó a Python 3.12, usuario no-root y `HEALTHCHECK`; CI puede validarlo cuando el runner tenga Docker o se use un build de Render.

---

## B-05 — Producción desincronizada (RESUELTO)

**Estado:** resuelto (2026-11-10)
**Severidad:** fue S0 en producción

Síntoma: `POST /api/v1/auth/register` y login con credenciales válidas devolvían
**500**; `/health` sí respondía 200.

Causa raíz (dos problemas acumulados):

1. **Rate limiting (T-093):** con el limiter activo, slowapi lanzaba
   `parameter 'response' must be an instance of starlette.responses.Response` al
   inyectar cabeceras en respuestas 2xx. Corregido en `eb9815b`.
2. **Migraciones desfasadas:** InsForge estaba en `d4e5f6a7b8c9` y el código
   esperaba `c9d0e1f2a3b4`. Faltaban `projects.slug`,
   `users.muted_notification_types` y `notifications.dedupe_key`, por lo que el
   INSERT de registro y el SELECT de login fallaban.

Resolución aplicada:

- Backup comprimido antes de migrar (`pg_dump -Fc`, 292 KB).
- `alembic upgrade head` sobre InsForge → `c9d0e1f2a3b4 (head)`.
- Redeploy de Render desde `main` (`641fb26`).

Verificación:

```text
GET  /health/ready                          → 200
POST /api/v1/auth/register                  → 201 + X-RateLimit-Limit: 5
POST /api/v1/auth/login                     → 200
python scripts/smoke_release.py             → 14/14
python scripts/smoke_performance.py         → p95 < 1000 ms (WAN)
SSE (3 conexiones)                          → 3/3 abiertas
```

**Lección:** el runbook debe comprobar `alembic current == head` en producción
antes de dar un deploy por bueno. Añadido a la checklist de release.

---

## B-06 — T-003: labels, milestones e issues requieren credenciales de GitHub

**Estado:** abierto (2026-11-10)
**Severidad:** gobernanza (no bloquea runtime)

T-003 pide crear labels (`s0/s1/security/db/frontend/docs`), milestones e issues
`T-###` en `Chorexxs/taskflow-api`. El entorno no tiene `gh` instalado,
`GITHUB_TOKEN` ni ningún credential helper con sesión de GitHub:

```text
gh -> CommandNotFoundException
GITHUB_TOKEN -> no definido
%APPDATA%\GitHub CLI\hosts.yml -> no existe
```

**Acción manual requerida:** con una sesión autenticada, ejecutar la importación
del backlog o crearlo desde la UI. Labels mínimos:

```bash
gh label create s0 --color B60205 --description "Critico"
gh label create s1 --color D93F0B --description "Alto"
gh label create security --color 0E8A16
gh label create frontend --color 1D76DB
gh label create db --color 5319E7
gh label create docs --color FBCA04
```

Después, crear un milestone por fase (P0…P9, P7 opcional) e importar una issue
por cada `T-###` de `specs/taskflow/tasks.md`.

---

## Lo que sí está verificado

- `pytest -q` → **101 tests passed** (última ejecución completa).
- `npm run test` → **12 tests passed**.
- `npm run build` → correcto.
- `alembic upgrade head` + `downgrade base` sobre SQLite temporal → correcto.
- `npm audit --omit=dev` → **0 vulnerabilities**.
- `python scripts/export_openapi.py --check` → snapshot al día.
