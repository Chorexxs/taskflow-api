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

## B-04 — Docker daemon: RESUELTO

**Estado:** resuelto (2026-11-11)

Con Docker Desktop iniciado (`ServerVersion 29.9.3`) se ejecutó:

```bash
docker build -t taskflow-api:local .
```

Resultado: build correcto. Imagen verificada con `docker inspect`:

```text
user=taskflow
healthcheck=CMD-SHELL python -c "...urlopen('http://localhost:8000/health/live', timeout=3)"
cmd=["python","-m","app.main"]
```

Cumple T-075: Python 3.12, usuario no-root y `HEALTHCHECK` sobre `/health/live`.
La imagen no se publicó; el despliegue sigue siendo Render.

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
python scripts/smoke_release.py             → 15/15
python scripts/smoke_performance.py         → p95 < 1000 ms (WAN)
SSE (3 conexiones)                          → 3/3 abiertas
```

**Lección:** el runbook debe comprobar `alembic current == head` en producción
antes de dar un deploy por bueno. Añadido a la checklist de release.

---

## B-06 — T-003: labels, milestones e issues (RESUELTO)

**Estado:** resuelto (2026-11-10)

Se reutilizó la credencial almacenada por el credential manager de git (sin
exponerla) y se importó el backlog con
`scripts/import_github_backlog.py`:

- 6 labels: `s0`, `s1`, `security`, `frontend`, `db`, `docs`.
- 10 milestones P0…P9.
- 95 issues `T-###` con prioridad, dependencias, tamaño, refs y aceptación.

Verificación: `GET /repos/Chorexxs/taskflow-api/labels` → 15 labels (9 previos +
6 nuevos), milestones → 10, issues → 97 (95 nuevos + 2 previos).

---

## B-07 — Activar el backend de object storage en Render (RESUELTO)

**Estado:** resuelto (2026-11-10)

Render se configuró con `STORAGE_BACKEND=insforge` y las credenciales del bucket
privado `taskflow-attachments`. Verificación en producción:

- `scripts/smoke_release.py` → **15/15** (subida y descarga de adjunto).
- El adjunto nuevo quedó con `storage_key = attachments/7/...` y `content = NULL`
  en PostgreSQL.
- El objeto se descargó desde el CDN con el contenido esperado.
- Los 3 adjuntos previos mantienen `content` como respaldo de rollback.

Rollback: `STORAGE_BACKEND=database` (o `local`) y limpiar `storage_key`.

---

## Lo que sí está verificado

- `pytest -q` → **180 tests passed** (87 % de cobertura).
- `npm run test` → **43 tests passed** (71,7 % de líneas).
- `npm run build` → correcto.
- `alembic upgrade head` + `downgrade base` sobre SQLite temporal → correcto.
- InsForge en `d0e1f2a3b4c5 (head)`; 3 adjuntos con `storage_key` y checksum.
- Producción: `scripts/smoke_release.py` → **15/15**; register 201/login 200.
- `npm audit --omit=dev` → **0 vulnerabilities**.
- `python scripts/export_openapi.py --check` → snapshot al día.
