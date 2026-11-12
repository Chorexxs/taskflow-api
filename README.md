# TaskFlow API

API REST para gestión de tareas en equipo con autenticación JWT, equipos, proyectos, tablero Kanban, comentarios, adjuntos, notificaciones y registro de actividad.

[![Tests](https://img.shields.io/badge/backend%20tests-263%20passed-brightgreen)](./tests)
[![Frontend](https://img.shields.io/badge/frontend%20tests-74%20passed-brightgreen)](./frontend/src/test)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-blue)](https://fastapi.tiangolo.com/)

> **Documentación de producto y arquitectura:** [`specs/taskflow/`](./specs/taskflow/). La spec es la fuente de verdad; el código se implementa contra ella.

---

## Probar online

| Servicio | URL | Descripción |
|---|---|---|
| **Frontend** | https://taskflow-api-tau.vercel.app | Interfaz React |
| **Preview InsForge** | https://<insforge-project-id>.insforge.site | Último build desplegado vía InsForge/Vercel |
| **API** | https://taskflow-api-gkgl.onrender.com/api/v1 | Backend REST |
| **Swagger** | https://taskflow-api-gkgl.onrender.com/docs | Documentación interactiva |
| **Health** | https://taskflow-api-gkgl.onrender.com/health | Estado del servidor |
| **Liveness** | https://taskflow-api-gkgl.onrender.com/health/live | Proceso vivo |
| **Readiness** | https://taskflow-api-gkgl.onrender.com/health/ready | DB accesible |

> **Estado de despliegue:** API de Render **live** contra InsForge (`/health/ready` → 200) y frontend Vercel **live** en `https://taskflow-api-tau.vercel.app`. Producción verificada el 2026-11-10: **register 201**, **login 200**, smoke de release **15/15**, performance p95 < 1000 ms (WAN), SSE 3/3 y **object storage activo** (`taskflow-attachments`). Detalles en [`specs/taskflow/blockers.md`](./specs/taskflow/blockers.md).

---

## Arquitectura

```
┌─────────────────┐      HTTPS/JSON       ┌─────────────────────┐      ┌─────────────────┐
│   Frontend      │ ────────────────────▶ │   TaskFlow API      │ ───▶ │   PostgreSQL    │
│   (Vercel)      │ ◀──────────────────── │   (Render)          │      │   (InsForge)    │
│                 │                       │                     │      │                 │
│  React + Vite   │                       │  FastAPI + JWT      │      │  SQLAlchemy     │
│  Tailwind CSS   │                       │  Pydantic v2        │      │  Alembic        │
└─────────────────┘                       └─────────────────────┘      └─────────────────┘
                                                  │
                                                  ├── Redis opcional (rate limiting/cache/SSE pub-sub)
                                                  ├── Sentry opcional (errores)
                                                  ├── InsForge Storage opcional (adjuntos en object storage)
```

### Stack

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **ORM / DB** | SQLAlchemy 2, PostgreSQL 15, Alembic |
| **Validación** | Pydantic v2, pydantic-settings |
| **Auth** | JWT (`PyJWT`), bcrypt, access 15 min + refresh 7 días |
| **Seguridad** | SlowAPI, headers de seguridad, lockout de cuenta, CORS por allowlist |
| **Observabilidad** | structlog (JSON + request ID), Sentry opcional |
| **Frontend** | React 18, Vite 8, React Router 7 |
| **Datos front** | TanStack React Query 5, `fetch` |
| **UI** | Tailwind CSS 4, Lucide React, React Hot Toast, `@dnd-kit` |
| **Tests** | pytest + pytest-cov (263, 88,5 %), Vitest + Testing Library (74, 72,6 %) |
| **CI/CD** | GitHub Actions, Render, Vercel, InsForge |
| **Contenedores** | Docker, docker-compose (PostgreSQL + Redis + API) |

Los adjuntos se guardan por defecto en PostgreSQL (`STORAGE_BACKEND=database`) para sobrevivir a los discos efímeros de Render. `STORAGE_BACKEND=insforge` usa el bucket privado de InsForge Storage (object storage) y `local` queda para desarrollo. Los adjuntos existentes se migran con `scripts/backfill_attachments_object_storage.py`.

---

## Características

### Autenticación y seguridad

- Registro y login con email/contraseña; hash bcrypt.
- JWT con access token corto y refresh token rotativo.
- **Refresh operativo vía JSON body** (`{"refresh_token": "..."}`); la rotación revoca el token anterior.
- **Logout revoca access y refresh** en el servidor.
- Bloqueo de cuenta tras 5 intentos fallidos durante 15 minutos.
- Rate limiting por IP en registro/login (5/min y 10/min).
- CORS con allowlist (`CORS_ORIGINS`), sin `*` con credenciales.
- Fail-fast en producción si falta `SECRET_KEY`, `DATABASE_URL` o `CORS_ORIGINS`.
- Headers de seguridad: CSP, `Referrer-Policy`, `Permissions-Policy`, HSTS, `X-Content-Type-Options`, `X-Frame-Options` y XSS.
- Contraseñas de 8–128 caracteres; el cambio exige la contraseña actual.
- **Revocación global de sesiones** al cambiar credenciales mediante `token_version`.
- **Auto-refresh proactivo** en el frontend 60 s antes de expirar, con sincronización entre pestañas.
- Logging estructurado con `request_id` y `X-Request-ID`.
- Errores con envelope `{error: {code, message, details, request_id}}` y `detail` compatible.

> El refresh viaja siempre en el body JSON. El access token dura 15 minutos y el refresh 7 días por defecto.

### Equipos

- Crear/listar equipos y consultarlos por **ID o slug**.
- Editar nombre/descripción del equipo (solo admin).
- Miembros con roles `admin` / `member`.
- Añadir un usuario registrado por email (no es una invitación por correo).
- Listar miembros, cambiar rol y expulsar.
- Un miembro puede salir del equipo.
- **Siempre debe quedar al menos un admin** (guard de último admin).
- Búsqueda por nombre/título/descripción con escape de comodines y paginación.

### Proyectos

- Proyectos dentro de un equipo, con estado `active` / `archived`.
- Crear (cualquier miembro), editar/archivar/restaurar (solo admin).
- Endpoints explícitos `POST .../archive` y `POST .../restore`; `DELETE` se mantiene como alias de archivado.
- Listado con `include_archived=true` y badge de estado en la UI.
- Registro de actividad por proyecto.

### Tareas

- Título, descripción, estado, prioridad, asignado y fecha límite.
- Estados: `todo`, `in_progress`, `done`; prioridades: `low`, `medium`, `high`.
- Crear, listar, ver, editar, eliminar y asignar.
- **Creador o admin** pueden editar todos los campos.
- **Cualquier miembro** puede cambiar solo el estado (Kanban).
- El asignado debe ser miembro del equipo (también al crear).
- Filtros por estado, prioridad, asignado y rango de fechas.
- Ordenación y paginación (máx. 100).
- Referencia por ID o título (el título está deprecado como identificador).

### Colaboración

- **Comentarios**: crear, listar paginado, editar (autor y miembro actual) y borrar (autor o admin).
- **Menciones** `@email` en comentarios, con notificación solo a miembros del equipo.
- **Adjuntos**: subir, listar, descargar y borrar.
  - Límite de 10 MB configurable.
  - Allowlist de extensiones/MIME.
  - Nombres saneados y claves de almacenamiento únicas (sin path traversal).
  - Almacenamiento persistente en PostgreSQL por defecto; `local` para desarrollo.
  - Solo el uploader o un admin puede borrar.
- **Notificaciones** in-app al asignar, comentar o mencionar.
- Campana con contador de no leídas consultado a `/notifications/unread-count`.
- **SSE event-driven** con Redis pub/sub y fallback en proceso; reconciliación cada 30 s, heartbeats, `Last-Event-ID`, reconexión con backoff y polling de respaldo. Límite de 500 conexiones totales y 5 por usuario (503 + `Retry-After`).
- **Activity log** paginado con actor (`actor.email`) de tareas, proyectos, comentarios y adjuntos.

### Frontend

- **Login / Register**.
- **Dashboard**: equipos, crear equipo.
- **TeamDetail**: proyectos, miembros, roles, búsqueda con debounce, crear/editar equipo y proyecto, ver/restaurar archivados.
- **ProjectBoard**: Kanban con drag & drop, filtros en URL, búsqueda local, crear tarea, actividad paginada, editar/archivar proyecto.
- **TaskDetail**: editar tarea, comentarios paginados, adjuntos, actividad.
- **Profile**: cambio de contraseña con contraseña actual y re-login forzado.
- **Accesibilidad**: focus visible, `prefers-reduced-motion`, `aria-label` en iconos y modales como diálogos.
- Toasts, skeletons, estados de carga/vacío y 404.

---

## API

Base: `/api/v1`. Contrato completo en [`specs/taskflow/contracts/api.md`](./specs/taskflow/contracts/api.md).

| Grupo | Endpoints principales |
|---|---|
| **Auth** | `POST /auth/register`, `/login`, `/refresh`, `/logout` |
| **Users** | `GET /users/me`, `PUT /users/me` |
| **Teams** | `POST/GET /teams/`, `GET/PATCH /teams/{id}`, `GET /teams/{id}/search`, `POST/GET/PATCH/DELETE /teams/{id}/members` |
| **Projects** | `POST/GET /teams/{id}/projects/`, `GET/PATCH/DELETE /teams/{id}/projects/{id}`, `POST .../archive`, `POST .../restore`, `GET .../activity` |
| **Tasks** | `POST/GET .../tasks/`, `GET/PATCH/DELETE .../tasks/{id}`, `PATCH .../assign`, `GET .../activity` |
| **Comments** | `POST/GET .../comments/`, `PATCH/DELETE .../comments/{id}` |
| **Attachments** | `POST/GET .../attachments/`, `GET .../{id}/download`, `DELETE .../{id}` |
| **Notifications** | `GET /notifications/`, `GET /notifications/unread-count`, `PATCH /{id}/read`, `PATCH /read-all` |
| **Health** | `GET /health`, `GET /health/live`, `GET /health/ready` |

Documentación interactiva: `/docs`. OpenAPI: `/openapi.json`.

### Errores

```json
{
  "detail": "Mensaje de error",
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Mensaje de error",
    "details": null,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

`detail` se mantiene por compatibilidad; los clientes nuevos deben usar `error.code` y `error.message`.

---

## Inicio rápido

### Con Docker (recomendado)

```bash
docker compose up -d

# API:      http://localhost:8000
# Swagger:  http://localhost:8000/docs
# Frontend: cd frontend && npm install && npm run dev
```

### Sin Docker

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Editar .env con DATABASE_URL y SECRET_KEY

alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

Requiere **Node ≥ 22.12** (CI usa Node 24; Vite 8 y Vitest 5 no soportan Node 20).

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
npm run dev                  # http://localhost:5173
```

### Pre-commit (opcional pero recomendado)

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Los hooks ejecutan `ruff check`, `ruff format`, `gitleaks`, eslint y mypy. El
hook de secretos necesita el binario `gitleaks` en `PATH` (`brew`, `scoop`,
`winget` o `go install github.com/gitleaks/gitleaks/v8@v8.30.1`); el CI usa la
acción oficial y no depende de esa instalación local.

### Variables de entorno

Ver [`.env.example`](./.env.example). Las críticas:

```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow
DB_SSLMODE=prefer
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
STORAGE_BACKEND=database
```

Opcionales: `REDIS_URL`, `SENTRY_DSN`, `MAX_UPLOAD_SIZE`, `UPLOAD_DIR`, `ALLOWED_UPLOAD_EXTENSIONS`, `SSE_FALLBACK_POLL_SECONDS`, `SSE_HEARTBEAT_SECONDS`, `SSE_MAX_CONNECTIONS`, `SSE_MAX_CONNECTIONS_PER_USER`. En InsForge usar `DB_SSLMODE=require`.

---

## Base de datos y migraciones

Alembic es la única fuente de esquema en producción. La aplicación **no** crea tablas al arrancar.

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "descripcion"
```

Modelo actual: `users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens`.

Migraciones añadidas en este ciclo: `token_version` en `users` y `attachments.content` (LargeBinary) para almacenamiento persistente. El modelo objetivo (slugs, sesiones, índices) está en [`specs/taskflow/data-model.md`](./specs/taskflow/data-model.md).

---

## Tests

Los tests de integración usan **PostgreSQL** (ADR-008), nunca SQLite. El esquema
se crea con Alembic y cada test arranca con las tablas vacías.

```bash
# 1. Base de datos desechable para tests
docker compose up -d postgres
docker compose exec postgres createdb -U taskflow taskflow_test

# 2. Backend (PowerShell: $env:TEST_DATABASE_URL="...")
export TEST_DATABASE_URL=postgresql://taskflow:taskflow@localhost:5432/taskflow_test
python -m pytest -v
python -m pytest --cov=app --cov-report=html

# Un archivo / test
python -m pytest tests/test_auth.py
python -m pytest tests/test_auth.py::test_register_user

# Frontend
cd frontend
npm run test
npm run test:coverage   # umbrales: 70 % líneas/sentencias, 55 % ramas, 40 % funciones
npm run lint
npm run build
```

`TEST_USE_SQLITE=1` existe solo como atajo para runs unitarios rápidos sin
Postgres; no vale para validar un release. `TEST_SKIP_MIGRATIONS=1` reutiliza un
esquema ya migrado.

La suite fija `DB_SSLMODE` a partir de `TEST_DATABASE_URL` (o de
`TEST_DB_SSLMODE` si la defines) para que un `.env` de producción con
`DB_SSLMODE=require` no intente TLS contra el contenedor local (T-114).

Estado actual: **263 tests backend** (88,5 % de cobertura, verdes sobre PostgreSQL)
y **74 tests frontend** (72,6 % de líneas). El CI falla por debajo de **80 %** en
backend y **70 %** en frontend.

Además se ejecutó un **smoke test end-to-end contra InsForge real** (12/12) y otro contra la **API de producción en Render** (15/15): health, registro, login, equipo, proyecto, tarea, comentario, adjunto (object storage), descarga, búsqueda, notificaciones, perfil y error envelope. También se verificó CORS para las dos URLs de frontend y el rechazo de un origen no permitido.

---

## Deployment

### Backend — Render

- Build: `pip install -r requirements.txt`
- Start: `python -m app.main` (o `uvicorn app.main:app`)
- Variables: `DATABASE_URL`, `DB_SSLMODE=require`, `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS=https://taskflow-api-tau.vercel.app`, `STORAGE_BACKEND=insforge`, `INSFORGE_URL`, `INSFORGE_API_KEY`, `INSFORGE_STORAGE_BUCKET=taskflow-attachments`; opcionales `SECRET_KEY_PREVIOUS` (solo durante la rotación), `REDIS_URL`, `SENTRY_DSN`.
  - Si usas un dominio propio en Vercel, añádelo separado por comas.
  - Sin `CORS_ORIGINS`, la app **no arranca en producción** (fail-fast).
- Ejecutar `alembic upgrade head` antes del despliegue. `alembic/env.py` usa `DATABASE_URL`.
- Los adjuntos se guardan por defecto en PostgreSQL (`STORAGE_BACKEND=database`). En producción está activo `STORAGE_BACKEND=insforge` con el bucket privado `taskflow-attachments`; los objetos migrados conservan `content` como respaldo de rollback.
- Estado actual: `/health/ready` → `200`, base de datos en `d0e1f2a3b4c5 (head)`, registro/login y smoke de release **15/15** verificados.

### Frontend — Vercel

- Proyecto: `chorexxs-projects/taskflow-api`.
- Root Directory: `frontend`; framework Vite; build `npm run build`; output `dist`.
- Variable: `VITE_API_URL=https://taskflow-api-gkgl.onrender.com` (Production, Preview y Development).
- Git: `Chorexxs/taskflow-api` conectado; un push a `main` despliega automáticamente.
- `vercel.json`: rewrite SPA a `/` + headers de seguridad (CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- `.vercelignore`: excluye secretos, `.env.local`, backend, tests y specs del upload.
- Preview alternativo: `https://<insforge-project-id>.insforge.site` (mismo build).

```bash
# Deploy manual desde la raíz del repositorio
vercel deploy --prod --yes --project taskflow-api --scope chorexxs-projects
```

Estado: **live y verificado** (B-02 resuelto).

### Base de datos — InsForge

PostgreSQL gestionado. Proyecto nuevo: `c7578dc0-d532-4463-88f1-09c6e54356f7`.

- **URL del proyecto:** `https://<insforge-project-id>.eu-central.insforge.app`
- **DB host:** `<insforge-project-id>.eu-central.database.insforge.app`
- **Región:** `eu-central`
- **Estado:** esquema migrado a `c9d0e1f2a3b4` (head; 11 tablas + columnas de slug, preferencias, checksum y auditoría).

```bash
# Project API key (ik_) + URL del proyecto:
npx @insforge/cli link \
  --api-base-url https://<insforge-project-id>.eu-central.insforge.app \
  --api-key ik_...

# La contraseña real de la DB:
curl -H "Authorization: Bearer $INSFORGE_API_KEY" \
  https://<insforge-project-id>.eu-central.insforge.app/api/metadata/database-password
```

Con un **user API key** (`uak_`) también se puede usar el flujo de plataforma:

```bash
npx @insforge/cli login --user-api-key uak_...
npx @insforge/cli link --project-id c7578dc0-d532-4463-88f1-09c6e54356f7
npx @insforge/cli db connection-string
```

Guardar backups y probar restore (ver `specs/taskflow/data-model.md`).

---

## Estructura del proyecto

```
app/
├── main.py              # App FastAPI, CORS, middleware, health, routers
├── config.py            # Configuración central validada (fail-fast)
├── auth.py              # JWT, bcrypt, lockout, revocación
├── database.py          # Engine, sesión, dependencia get_db
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Schemas Pydantic
├── crud.py              # Acceso a datos
├── dependencies.py      # Resolución de equipo y permisos
├── exceptions.py        # Excepciones de dominio
├── cache.py             # Redis opcional
├── logging_config.py    # structlog
├── middleware.py        # Request ID y logging
└── routers/
    ├── auth.py
    ├── users.py
    ├── teams.py
    ├── projects.py
    ├── tasks.py
    ├── comments.py
    ├── attachments.py
    └── notifications.py

frontend/src/
├── api/index.js         # Cliente API único (fetch + errores tipados)
├── components/          # Layout, TaskCard, NotificationsBell, Skeleton
├── context/             # AuthContext
├── pages/               # Login, Register, Dashboard, TeamDetail,
│                        # ProjectBoard, TaskDetail, Profile, NotFound
├── App.jsx
└── main.jsx

specs/taskflow/          # SDD: constitución, baseline, spec, plan, tasks, datos, API, threat-model
specs/audit/             # Auditorías bajo demanda: código y ciberseguridad
tests/                   # pytest
alembic/                 # migraciones
```

---

## Documentación SDD

| Documento | Contenido |
|---|---|
| [`constitution.md`](./specs/taskflow/constitution.md) | Principios y quality gates |
| [`baseline.md`](./specs/taskflow/baseline.md) | Auditoría as-is y hallazgos |
| [`spec.md`](./specs/taskflow/spec.md) | Requisitos funcionales/no funcionales y permisos |
| [`plan.md`](./specs/taskflow/plan.md) | Arquitectura objetivo, ADRs y fases |
| [`tasks.md`](./specs/taskflow/tasks.md) | Backlog accionable |
| [`data-model.md`](./specs/taskflow/data-model.md) | Modelo actual/objetivo y migraciones |
| [`contracts/api.md`](./specs/taskflow/contracts/api.md) | Contrato HTTP |
| [`contracts/openapi.json`](./specs/taskflow/contracts/openapi.json) | Snapshot OpenAPI verificado en CI |
| [`blockers.md`](./specs/taskflow/blockers.md) | Bloqueos de despliegue y credenciales |
| [`environments.md`](./specs/taskflow/environments.md) | Local, CI, preview, staging y producción |
| [`release-checklist.md`](./specs/taskflow/release-checklist.md) | Checklist de release y smoke de performance |
| [`threat-model.md`](./specs/taskflow/threat-model.md) | Modelo STRIDE, mitigaciones y riesgos residuales |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Ramas, PR, release y rollback |

### Auditorías bajo demanda

| Spec | Contenido | Activación |
|---|---|---|
| [`specs/audit/code-audit.md`](./specs/audit/code-audit.md) | Calidad, arquitectura, escalabilidad, tests y contratos | `audita el código` o `/audit-code` |
| [`specs/audit/security-audit.md`](./specs/audit/security-audit.md) | Secretos, authn/authz, uploads, dependencias, CI/CD y privacidad | `audita la seguridad` o `/audit-security` |

> Estos specs **no se ejecutan solos**: solo cuando el usuario da la orden.
> Son de solo lectura y nunca atacan producción.

---

## Limitaciones conocidas y próximos pasos

- **MCP de Vercel:** el servidor `vercel` está configurado en OpenCode pero requiere autenticación OAuth (`/mcps` → `vercel` → sign in). El deploy por CLI y la integración con Git ya funcionan.
- Transporte de tokens (ADR-001): decisión final en T-097; se mantiene Bearer + auto-refresh porque el frontend y la API son sitios distintos y la cookie de refresh requeriría cookies de terceros. Riesgo residual y disparadores de reapertura en `specs/taskflow/security-checklist.md`.
- Adjuntos en object storage: `StorageService` con backend InsForge Storage (`STORAGE_BACKEND=insforge`), bucket privado, backfill con checksum y rollback documentado (T-054).
- SSE implementado con Redis pub/sub, límites de conexión y prueba de 500 conexiones (T-081); el polling queda como respaldo.
- Orden estable del Kanban con `tasks.position` y migración `f0e1f2a3b4c5` (T-096).
- Rate limiting con Redis para múltiples instancias implementado (T-030/T-031); fallback en memoria si Redis no responde.
- Auditoría WCAG completa y tema claro/oscuro (P5); la UI es dark-only.
- Gates de seguridad en CI: `gitleaks` (pre-commit y CI), `pip-audit` y dependencias al día (P8).

El detalle y el orden están en [`specs/taskflow/tasks.md`](./specs/taskflow/tasks.md).

---

## Contributing

1. Lee [`specs/taskflow/constitution.md`](./specs/taskflow/constitution.md).
2. Toma una tarea `T-###` del backlog.
3. Crea una rama `feat/T-###-descripcion` (ver [`CONTRIBUTING.md`](./CONTRIBUTING.md)).
4. Añade tests y actualiza la spec/contrato si cambia el comportamiento.
5. Abre un PR referenciando `T-###` y los `FR-###`/`BL-##` cubiertos.

La política completa de ramas, PR, release y rollback está en
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Licencia

MIT — ver [`LICENSE`](./LICENSE).
