# Bloqueos de despliegue

Fecha: 2026-11-09

Estos bloqueos requieren credenciales o acciones manuales que no están disponibles en el entorno del agente.

---

## B-01 — InsForge: API key inválida/revocada

**Objetivo:** enlazar el proyecto `c7578dc0-d532-4463-88f1-09c6e54356f7` y obtener su `DATABASE_URL`.

**Comando ejecutado:**

```bash
npx @insforge/cli --yes link --project-id c7578dc0-d532-4463-88f1-09c6e54356f7
```

**Salida:**

```text
Error: API key is invalid or revoked. Run `npx @insforge/cli login --user-api-key <new-key>` again.
```

El CLI sigue apuntando al proyecto antiguo `ac9e6df1-…` (appkey `m9f56tky`), cuya conexión PostgreSQL también falla:

```text
psycopg2.OperationalError: connection to server at "m9f56tky.us-east.database.insforge.app", port 5432 failed: SSL connection has been closed unexpectedly
```

**Qué necesito:**

1. Un **user API key válido** de InsForge, o ejecutar en tu máquina:
   ```bash
   npx @insforge/cli login --user-api-key <USER_API_KEY>
   npx @insforge/cli link --project-id c7578dc0-d532-4463-88f1-09c6e54356f7
   npx @insforge/cli db connection-string
   ```
2. Compartir la `DATABASE_URL` resultante (o configurarla en Render) y ejecutar:
   ```bash
   alembic upgrade head
   ```
   con `DB_SSLMODE=require`.

**Impacto:** no se pueden aplicar las migraciones nuevas (`token_version`, `attachments.content`) contra la base de datos de producción ni verificar el arranque real con PostgreSQL.

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

**Qué necesito:** ejecutar `vercel login` o proporcionar un `VERCEL_TOKEN` con acceso al proyecto `chorexxs-projects/taskflow-api`.

**Impacto:** no se puede desplegar el frontend actualizado en el proyecto existente de Vercel ni verificar el deploy real.

---

## B-03 — Render: variables de entorno

El backend necesita, en el servicio de Render:

```bash
ENVIRONMENT=production
SECRET_KEY=<32+ caracteres>
DATABASE_URL=<connection string de InsForge>
DB_SSLMODE=require
CORS_ORIGINS=https://taskflow-api-tau.vercel.app
STORAGE_BACKEND=database
```

Sin `CORS_ORIGINS`, la app falla al arrancar por diseño (fail-fast).

**Impacto:** no se puede verificar el despliegue real de la API.

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
