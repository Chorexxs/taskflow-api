# Bloqueos de despliegue

Fecha: 2026-11-09

Estos bloqueos requieren credenciales o acciones manuales que no están disponibles en el entorno del agente.

---

## B-01 — InsForge: RESUELTO

**Proyecto:** `c7578dc0-d532-4463-88f1-09c6e54356f7`
**URL:** `https://wrm6rjkp.eu-central.insforge.app`
**DB host:** `wrm6rjkp.eu-central.database.insforge.app`
**Región:** `eu-central`

La `ik_` key es una **project API key**, no una `uak_` de usuario. Se enlazó correctamente con:

```bash
npx @insforge/cli link \
  --api-base-url https://wrm6rjkp.eu-central.insforge.app \
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

- `alembic current` → `d4e5f6a7b8c9 (head)`.
- 11 tablas creadas (`users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens`, `alembic_version`).
- Smoke test real contra InsForge: **12/12 checks** (health, registro, login, equipo, proyecto, tarea, comentario, subida/descarga de adjunto, búsqueda, notificaciones, error envelope).
- La app puede conectarse con SQLAlchemy usando `DB_SSLMODE=require`.

**Nota:** la `DATABASE_URL` real está en `.env` (ignorado por git) y debe configurarse en Render.

---

## B-02 — Vercel: sesión no iniciada

**Comando ejecutado:**

```bash
npx vercel whoami
```

**Salida:**

```text
> Logged out.
```

También se intentó un despliegue temporal:

```bash
npx vercel deploy --temporary --yes --build-env VITE_API_URL=https://taskflow-api-gkgl.onrender.com
```

**Salida:**

```text
> Temporary deployments aren't available for this attempt. Log in to continue.
> No existing credentials found. Starting login flow...
```

**Workaround verificado:** el despliegue vía InsForge sí funciona y publicó un preview en:

```text
https://wrm6rjkp.insforge.site
```

El deployment de Vercel quedó `READY` (id `2b6e8f98-...`), pero pertenece a un proyecto Vercel gestionado por InsForge, no al proyecto `chorexxs-projects/taskflow-api`.

**Qué necesito:** ejecutar `vercel login` o proporcionar un `VERCEL_TOKEN` con acceso al proyecto `chorexxs-projects/taskflow-api` si se quiere actualizar ese proyecto concreto.

**Impacto:** el preview de InsForge está online, pero la URL `taskflow-api-tau.vercel.app` sigue sirviendo el build anterior hasta que se autentique Vercel.

---

## B-03 — Render: RESUELTO

Se actualizaron las variables del servicio `srv-d82qnghj2pic73aqr5l0`:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://postgres:<db-password>@wrm6rjkp.eu-central.database.insforge.app:5432/insforge?sslmode=require
DB_SSLMODE=require
CORS_ORIGINS=https://taskflow-api-tau.vercel.app,https://wrm6rjkp.insforge.site
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
Origin https://wrm6rjkp.insforge.site → permitido
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

## Lo que sí está verificado

- `pytest -q` → **101 tests passed** (última ejecución completa).
- `npm run test` → **12 tests passed**.
- `npm run build` → correcto.
- `alembic upgrade head` + `downgrade base` sobre SQLite temporal → correcto.
- `npm audit --omit=dev` → **0 vulnerabilities**.
- `python scripts/export_openapi.py --check` → snapshot al día.
