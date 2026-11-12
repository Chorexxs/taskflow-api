# TaskFlow API

API REST para gestión de tareas en equipo con autenticación JWT, equipos, proyectos, tablero Kanban, comentarios, adjuntos, notificaciones en tiempo real y registro de actividad.

[![Tests](https://img.shields.io/badge/backend%20tests-279%20passed-brightgreen)](./tests)
[![Frontend](https://img.shields.io/badge/frontend%20tests-82%20passed-brightgreen)](./frontend/src/test)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-blue)](https://fastapi.tiangolo.com/)
[![Node](https://img.shields.io/badge/Node-%E2%89%A522.12-339933)](https://nodejs.org/)

> **Documentación de producto y arquitectura:** [`specs/taskflow/`](./specs/taskflow/). La spec es la fuente de verdad; el código se implementa contra ella siguiendo el flujo SDD.

---

## Estado actual

**Actualizado:** 2026-11-12 · **Rama:** `main` · **Backlog `T-001…T-129` ejecutado**, sin tareas funcionales pendientes; solo queda deuda aceptada y decisiones de infraestructura.

| Comprobación | Resultado |
|---|---|
| Tests backend (PostgreSQL 16) | **279 passed**, 0 fallos, **91 %** de cobertura |
| Tests frontend (Vitest 5 + Testing Library) | **82 passed**, 74,8 % líneas / 61,5 % ramas |
| Lint y tipos | `ruff`, `ruff format`, `mypy`, eslint: limpios |
| Build frontend | `npm run build` correcto |
| Migraciones | `upgrade` / `downgrade -1` / `upgrade` reversibles |
| OpenAPI | snapshot versionado y verificado en CI |
| Producción | API Render **live**, frontend Vercel **live**, InsForge en `c1d2e3f4a5b6 (head)` |
| Smoke de release | **15/15** contra producción (incluye subida/descarga de adjunto) |

**Trabajo reciente de rendimiento (T-128 / T-129):** se redujeron los round trips SQL por acción (auth + membresía en una sola consulta, sin lookups duplicados, `expire_on_commit=False`, una única transacción al crear tareas) y se eliminó el `/users/me` duplicado del frontend. Medición WAN desde España:

| Acción | Antes | Ahora |
|---|---:|---:|
| Abrir tablero | 1.796 ms | **1.231 ms** |
| Mover tarea | 2.376 ms | **1.392 ms** |
| Crear tarea (con `Idempotency-Key`) | 3.400 ms | **2.394 ms** |
| Login | 2.900 ms | ~2.600 ms (bcrypt + CPU del plan) |

> El coste restante es de infraestructura: Render y la base de datos están en regiones distintas (~140 ms por statement) y el plan free limita la CPU de bcrypt. El código ya no añade trabajo evitable.

---

## Probar online

| Servicio | URL | Descripción |
|---|---|---|
| **Frontend** | https://taskflow-api-tau.vercel.app | Interfaz React (Vercel) |
| **API** | https://taskflow-api-gkgl.onrender.com/api/v1 | Backend REST (Render) |
| **Health** | https://taskflow-api-gkgl.onrender.com/health | Estado de DB/Redis/disco |
| **Liveness** | https://taskflow-api-gkgl.onrender.com/health/live | Proceso vivo |
| **Readiness** | https://taskflow-api-gkgl.onrender.com/health/ready | Base de datos accesible |

> **Swagger/OpenAPI están deshabilitados en producción** (T-086) para no exponer la superficie de la API. En local están disponibles en `/docs`, `/redoc` y `/openapi.json`.

---

## Arquitectura

```
┌─────────────────┐      HTTPS/JSON       ┌─────────────────────┐      ┌─────────────────┐
│   Frontend      │ ────────────────────▶ │   TaskFlow API      │ ───▶ │   PostgreSQL    │
│   (Vercel)      │ ◀──────────────────── │   (Render)          │      │   (InsForge)    │
│                 │                       │                     │      │                 │
│  React + Vite   │                       │  FastAPI + JWT      │      │  SQLAlchemy 2   │
│  Tailwind CSS 4 │                       │  Pydantic v2        │      │  Alembic        │
└─────────────────┘                       └─────────────────────┘      └─────────────────┘
                                                  │
                                                  ├── Redis (rate limiting + pub/sub de SSE, opcional)
                                                  ├── InsForge Storage (adjuntos, opcional)
                                                  ├── ClamAV (antimalware, opcional)
                                                  └── Sentry (errores/trazas, opcional)
```

Los adjuntos se guardan por defecto en PostgreSQL (`STORAGE_BACKEND=database`) para sobrevivir a los discos efímeros de Render. En producción está activo `STORAGE_BACKEND=insforge` con el bucket privado `taskflow-attachments`; `local` queda para desarrollo. Existe backfill con checksum y rollback documentado (`scripts/backfill_attachments_object_storage.py`).

### Stack

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.12, FastAPI 0.135, Uvicorn 0.42 |
| **ORM / DB** | SQLAlchemy 2.0, PostgreSQL (15 local / InsForge en producción), Alembic 1.18 |
| **Validación** | Pydantic 2.12, pydantic-settings |
| **Auth** | JWT (`PyJWT`), bcrypt, access 15 min + refresh 7 días |
| **Seguridad** | slowapi, headers, lockout, CORS por allowlist, gitleaks, pip-audit, SBOM |
| **Observabilidad** | structlog (JSON + `request_id`), Sentry opcional |
| **Frontend** | React 18.3, Vite 8.3, Vitest 5.1, React Router 7 |
| **Datos front** | TanStack React Query 5, `fetch` con refresh single-flight |
| **UI** | Tailwind CSS 4, Lucide, React Hot Toast, `@dnd-kit` |
| **CI/CD** | GitHub Actions, Render, Vercel, InsForge |
| **Contenedores** | Docker (non-root + HEALTHCHECK), docker-compose (PostgreSQL + Redis + API) |

---

## Características

### Autenticación y sesión

- Registro y login con email/contraseña; hash **bcrypt**.
- **Access token 15 min** y **refresh token 7 días** con rotación en cada refresh.
- El refresh viaja **solo en el body JSON** (`{"refresh_token": "..."}`); nunca en query string.
- **Logout** revoca access y refresh en el servidor (idempotente).
- **Detección de reutilización de refresh**: revoca la familia de sesiones.
- **Bloqueo de cuenta** tras 5 intentos fallidos durante 15 min; al bloquear se revocan las sesiones previas (`token_version`).
- **Verificación de email** con token de un solo uso, endpoints `verify-email` / `resend-verification`, backend `log` (desarrollo) o SMTP.
- **Cambio de contraseña** exige la actual y revoca todas las sesiones.
- **Auto-refresh proactivo** en el frontend 60 s antes de expirar, single-flight entre peticiones y sincronizado entre pestañas.
- Rotación de `SECRET_KEY` con clave dual (`SECRET_KEY_PREVIOUS` solo verifica, ADR-012).
- Política de contraseñas 8–128, sin caracteres de control.
- Rate limiting por IP (Redis compartido con fallback en memoria) y `429` con `Retry-After`.
- Envelope de errores `{error: {code, message, details, request_id}}` con `detail` compatible.
- Headers de seguridad: CSP, HSTS, `Referrer-Policy`, `Permissions-Policy`, `X-Content-Type-Options`, `X-Frame-Options`.

### Equipos

- Crear/listar y consultar por **ID o slug**; el listado incluye `role` y `project_count`.
- El slug se genera en el servidor desde el nombre (sufijo determinista ante colisión).
- Miembros con roles `admin` / `member`.
- Añadir un usuario ya registrado por email (no es una invitación por correo).
- Listar miembros, cambiar rol y expulsar; un miembro puede salir.
- **Siempre queda al menos un admin**: guard de último admin y `SELECT … FOR UPDATE` al cambiar membresías para evitar carreras.
- Búsqueda en el equipo (proyectos, tareas, comentarios) con escape de comodines y paginación.

### Proyectos

- Dentro de un equipo, con estado `active` / `archived` y slug único por equipo.
- Crear (cualquier miembro); editar/archivar/restaurar (solo admin).
- Endpoints explícitos `POST .../archive` y `POST .../restore`; `DELETE` **archiva**.
- Listado con `include_archived=true` y badge de estado en la UI.
- Actividad paginada por proyecto.

### Tareas y Kanban

- Título, descripción, estado, prioridad, asignado y fecha límite.
- Estados `todo` / `in_progress` / `done`; prioridades `low` / `medium` / `high`.
- Crear, listar, ver, editar, eliminar y asignar.
- **Creador o admin** editan todos los campos; **cualquier miembro** puede cambiar solo el estado.
- `PATCH .../status` atómico con `status` + `position` para el orden estable del Kanban.
- El asignado debe ser miembro del equipo (también al crear).
- Filtros por estado, prioridad, asignado y rango de fechas; ordenación y paginación (máx. 100).
- Referencia por `id`; el título queda como identificador deprecado.
- **Idempotencia** opcional en `POST` críticos con `Idempotency-Key`: replay de la respuesta original, `422` si la clave se reutiliza con otro payload, `409` si está en vuelo y purga a 24 h.

### Colaboración

- **Comentarios** paginados con orden configurable; edición solo por el autor y pertenencia actual al equipo.
- **Menciones** `@email` en comentarios, con notificación solo a miembros del equipo.
- **Adjuntos**: subir, listar, descargar y borrar.
  - Límite de 10 MB configurable aplicado en streaming.
  - Allowlist de extensiones/MIME, validación de **magic bytes** y rechazo de ejecutables.
  - Escaneo **ClamAV** opcional con política fail-closed.
  - Nombres saneados, claves únicas, checksum SHA-256 y limpieza al borrar tareas.
  - Solo el uploader o un admin puede borrar.
- **Notificaciones** in-app con paginación, contador de no leídas, deduplicación por evento y preferencias por tipo (silenciar).
- **SSE** autenticado con Redis pub/sub y fallback en proceso: heartbeat, `Last-Event-ID`, reconciliación por polling, backoff, 500 conexiones totales y 5 por usuario (`503` + `Retry-After`).
- **Activity log** paginado con actor (`actor.email`) de tareas, proyectos, comentarios y adjuntos.
- **Retención de datos**: purga idempotente de notificaciones > 90 d y actividad > 1 año (al arrancar y con `scripts/purge_retention.py`).

### Frontend

- **Login**, **Register** y **VerifyEmail**.
- **Dashboard**: equipos, rol, número de proyectos y creación de equipo.
- **TeamDetail**: proyectos, miembros, roles, búsqueda con debounce, crear/editar equipo y proyecto, archivados.
- **ProjectBoard**: Kanban con drag & drop, actualización optimista, filtros en URL, búsqueda local, crear tarea, actividad paginada, ajustes del proyecto.
- **TaskDetail**: editar tarea, comentarios paginados, adjuntos, actividad.
- **Profile**: cambio de contraseña y preferencias de notificación.
- **Accesibilidad**: focus visible, `prefers-reduced-motion`, `aria-label`, modales como diálogos con focus trap y cierre con `Escape`.
- Toasts, skeletons, estados de carga/vacío/error con reintento y 404.
- Tema **dark-only** (ADR-006).

---

## API

Base: `/api/v1`. Contrato completo en [`specs/taskflow/contracts/api.md`](./specs/taskflow/contracts/api.md) y snapshot en [`contracts/openapi.json`](./specs/taskflow/contracts/openapi.json).

| Grupo | Endpoints principales |
|---|---|
| **Auth** | `POST /auth/register`, `/auth/login` (form OAuth2), `/auth/refresh` (JSON body), `/auth/logout`, `/auth/verify-email`, `/auth/resend-verification` |
| **Users** | `GET/PUT /users/me`, `GET/PUT /users/me/notification-preferences` |
| **Teams** | `POST/GET /teams/`, `GET/PATCH /teams/{id_o_slug}`, `GET /teams/{id}/search`, `POST/GET /teams/{id}/members`, `PATCH/DELETE /teams/{id}/members/{user_id}` |
| **Projects** | `POST/GET /teams/{id}/projects/`, `GET/PATCH/DELETE /teams/{id}/projects/{id_o_slug}`, `POST .../archive`, `POST .../restore`, `GET .../activity` |
| **Tasks** | `POST/GET .../tasks/`, `GET/PATCH/DELETE .../tasks/{id}`, `PATCH .../status`, `PATCH .../assign`, `GET .../activity` |
| **Comments** | `POST/GET .../comments/`, `PATCH/DELETE .../comments/{id}` |
| **Attachments** | `POST/GET .../attachments/`, `GET .../{id}/download`, `DELETE .../{id}` |
| **Notifications** | `GET /notifications/`, `GET /notifications/unread-count`, `GET /notifications/stream` (SSE), `PATCH /{id}/read`, `PATCH /read-all` |
| **Health** | `GET /health`, `GET /health/live`, `GET /health/ready` |

Convenciones:

- JSON en `snake_case`; fechas ISO 8601 UTC.
- `Authorization: Bearer <access_token>`.
- Paginación `{items, total, page, pages, has_next}` con `page` / `page_size` (máx. 100).
- Identificadores por `id` y `slug`; nombre/título deprecados.
- `DELETE /projects/{id}` **archiva**, no borra.
- `Idempotency-Key` opcional en `POST` críticos.

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

### Pre-commit (recomendado)

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Los hooks ejecutan `ruff check`, `ruff format`, `gitleaks`, eslint y mypy. El hook de secretos necesita el binario `gitleaks` en `PATH` (`brew`, `scoop`, `winget` o `go install github.com/gitleaks/gitleaks/v8`). El CI usa la acción oficial y no depende de esa instalación local.

### Variables de entorno

Ver [`.env.example`](./.env.example). Las críticas:

```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow
DB_SSLMODE=prefer          # require en InsForge
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
STORAGE_BACKEND=database   # database | local | insforge
```

Opcionales y de operación:

```bash
# Auth / sesión
SECRET_KEY_PREVIOUS, ALGORITHM, MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES
# Pool
POOL_SIZE, MAX_OVERFLOW, POOL_PRE_PING
# Rate limiting y proxy
REDIS_URL, RATE_LIMIT_ENABLED, RATE_LIMIT_STORAGE_URI, FORWARDED_ALLOW_IPS
# SSE
SSE_POLL_SECONDS, SSE_FALLBACK_POLL_SECONDS, SSE_HEARTBEAT_SECONDS,
SSE_MAX_CONNECTIONS, SSE_MAX_CONNECTIONS_PER_USER
# Observabilidad
SENTRY_DSN, SENTRY_TRACES_SAMPLE_RATE, LOG_LEVEL
# Adjuntos
MAX_UPLOAD_SIZE, UPLOAD_DIR, ALLOWED_UPLOAD_EXTENSIONS,
INSFORGE_URL, INSFORGE_API_KEY, INSFORGE_STORAGE_BUCKET,
CLAMAV_HOST, CLAMAV_PORT, CLAMAV_TIMEOUT_SECONDS, CLAMAV_REQUIRED
# Email
FRONTEND_URL, EMAIL_VERIFICATION_REQUIRED, EMAIL_VERIFICATION_TTL_HOURS,
EMAIL_BACKEND, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
SMTP_FROM, SMTP_USE_TLS, SMTP_USE_SSL
# Retención e idempotencia
NOTIFICATION_RETENTION_DAYS, ACTIVITY_RETENTION_DAYS, IDEMPOTENCY_KEY_TTL_HOURS
```

**Producción:** `SECRET_KEY`, `DATABASE_URL` y `CORS_ORIGINS` son obligatorias; la app falla al arrancar si faltan, y `DB_SSLMODE` debe exigir TLS.

---

## Base de datos y migraciones

Alembic es la única fuente de esquema en producción. La aplicación **no** crea tablas al arrancar.

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "descripcion"
```

**Head actual:** `c1d2e3f4a5b6` (verificación de email). Producción verificada en esa revisión.

Tablas: `users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens`, `idempotency_keys`, `email_verification_tokens` (+ `alembic_version`).

El detalle de columnas, índices, constraints y migraciones está en [`specs/taskflow/data-model.md`](./specs/taskflow/data-model.md). Backups y drill de restore: `scripts/backup_restore_drill.py`.

---

## Tests

Los tests de integración usan **PostgreSQL** (ADR-008), nunca SQLite. El esquema se crea con Alembic y cada test arranca con las tablas vacías.

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
npm run test:coverage
npm run lint
npm run build
```

`TEST_USE_SQLITE=1` existe solo como atajo para runs unitarios rápidos sin Postgres; no vale para validar un release. `TEST_SKIP_MIGRATIONS=1` reutiliza un esquema ya migrado.

La suite fija `DB_SSLMODE` a partir de `TEST_DATABASE_URL` (o de `TEST_DB_SSLMODE`) para que un `.env` de producción con `DB_SSLMODE=require` no intente TLS contra el contenedor local (T-114).

**Estado actual:** 279 tests backend (91 % de cobertura) y 82 tests frontend (74,8 % líneas / 61,5 % ramas / 65,3 % funciones). El CI falla por debajo de **80 %** en backend y **70 %** de líneas en frontend.

Además: smoke end-to-end contra InsForge (12/12) y contra producción en Render (15/15), smoke de performance de lectura y escritura, prueba de carga SSE (500/500) y drill de backup/restore verificado.

---

## Deployment

### Backend — Render

- Build: `pip install -r requirements.txt`
- Start: `python -m app.main`
- Variables mínimas: `ENVIRONMENT=production`, `SECRET_KEY`, `DATABASE_URL`, `DB_SSLMODE=require`, `CORS_ORIGINS`, `STORAGE_BACKEND=insforge`, `INSFORGE_URL`, `INSFORGE_API_KEY`, `INSFORGE_STORAGE_BUCKET=taskflow-attachments`.
- Opcionales: `SECRET_KEY_PREVIOUS` (solo durante rotación), `REDIS_URL`, `SENTRY_DSN`, SMTP.
- Ejecutar `alembic upgrade head` **antes** de desplegar y comprobar `alembic current == head`.
- `/docs`, `/redoc` y `/openapi.json` se sirven solo fuera de producción.
- Healthchecks: `/health/live` (proceso) y `/health/ready` (DB).

### Frontend — Vercel

- Proyecto: `chorexxs-projects/taskflow-api`; Root Directory `frontend`; build `npm run build`; output `dist`.
- `VITE_API_URL=https://taskflow-api-gkgl.onrender.com` en Production, Preview y Development.
- Un push a `main` despliega automáticamente.
- `vercel.json`: rewrite SPA y headers de seguridad.
- `.vercelignore`: excluye secretos, backend, tests y specs.

```bash
vercel deploy --prod --yes --project taskflow-api --scope chorexxs-projects
```

### Base de datos — InsForge

PostgreSQL gestionado en `eu-central`.

- **URL del proyecto:** `https://<insforge-project-id>.eu-central.insforge.app`
- **DB host:** `<insforge-project-id>.eu-central.database.insforge.app`
- **Estado:** `c1d2e3f4a5b6 (head)`; 12 tablas de dominio.

```bash
npx @insforge/cli link \
  --api-base-url https://<insforge-project-id>.eu-central.insforge.app \
  --api-key ik_...
```

> **Nota de rendimiento:** API y base de datos están en regiones distintas. Cada round trip SQL cuesta ~140 ms y bcrypt ~2,3 s en el plan free. El código ya minimiza statements y transacciones; mover Render a `eu-central` y subir la CPU es la mejora pendiente de mayor impacto.

---

## Estructura del proyecto

```
app/
├── main.py              # App FastAPI, CORS, middleware, health, routers
├── config.py            # Settings centrales y fail-fast
├── auth.py              # JWT, bcrypt, lockout, revocación
├── database.py          # Engine, sesión, get_db
├── models.py            # Modelos SQLAlchemy
├── dependencies.py      # Equipo + membresía + permisos en una consulta
├── exceptions.py        # Excepciones de dominio
├── idempotency.py       # Idempotency-Key (reserva, replay, release)
├── logging_config.py    # structlog
├── middleware.py        # Request ID, logging y límite de body
├── storage.py           # StorageService (database/local/InsForge)
├── uploads.py           # Validación de subidas (tipo, tamaño, magic bytes)
├── schemas/             # Schemas Pydantic por dominio
├── crud/                # Acceso a datos por dominio
├── services/            # Casos de uso (subida de adjuntos)
├── events.py            # Bus SSE y pub/sub
└── routers/
    ├── auth.py, users.py, teams.py, projects.py, tasks.py
    ├── comments.py, attachments.py, notifications.py

frontend/src/
├── api/                 # Cliente único (fetch, refresh, errores, tokens)
├── components/
│   ├── board/           # Diálogos y columnas del Kanban
│   ├── tasks/           # Adjuntos y panel de actividad
│   ├── teams/           # Diálogos de proyecto y miembros
│   └── Layout, TaskCard, NotificationsBell, Skeleton, QueryError
├── context/             # AuthContext
├── pages/               # Login, Register, VerifyEmail, Dashboard,
│                        # TeamDetail, ProjectBoard, TaskDetail, Profile, NotFound
├── test/                # Vitest + Testing Library + MSW
├── App.jsx
└── main.jsx

specs/taskflow/          # SDD: constitución, baseline, spec, plan, tasks, datos, API, threat-model
specs/audit/             # Auditorías bajo demanda (código y ciberseguridad)
alembic/                 # Migraciones
scripts/                 # Smoke, performance, backup/restore, retención, OpenAPI, SSE
tests/                   # pytest
```

---

## Documentación SDD

| Documento | Contenido |
|---|---|
| [`constitution.md`](./specs/taskflow/constitution.md) | Principios y quality gates |
| [`baseline.md`](./specs/taskflow/baseline.md) | Auditoría as-is y hallazgos |
| [`spec.md`](./specs/taskflow/spec.md) | Requisitos funcionales/no funcionales y permisos |
| [`plan.md`](./specs/taskflow/plan.md) | Arquitectura objetivo, ADRs y fases |
| [`tasks.md`](./specs/taskflow/tasks.md) | Backlog accionable y estado de ejecución |
| [`data-model.md`](./specs/taskflow/data-model.md) | Modelo actual/objetivo y migraciones |
| [`contracts/api.md`](./specs/taskflow/contracts/api.md) | Contrato HTTP |
| [`contracts/openapi.json`](./specs/taskflow/contracts/openapi.json) | Snapshot OpenAPI verificado en CI |
| [`security-checklist.md`](./specs/taskflow/security-checklist.md) | Checklist ASVS L2 y deuda aceptada |
| [`threat-model.md`](./specs/taskflow/threat-model.md) | Modelo STRIDE, mitigaciones y riesgos residuales |
| [`blockers.md`](./specs/taskflow/blockers.md) | Bloqueos de entorno y credenciales |
| [`environments.md`](./specs/taskflow/environments.md) | Local, CI, preview, staging y producción |
| [`release-checklist.md`](./specs/taskflow/release-checklist.md) | Checklist de release y smoke de performance |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Ramas, PR, release y rollback |

### Auditorías bajo demanda

| Spec | Contenido | Activación |
|---|---|---|
| [`specs/audit/code-audit.md`](./specs/audit/code-audit.md) | Calidad, arquitectura, escalabilidad, tests y contratos | `audita el código` o `/audit-code` |
| [`specs/audit/security-audit.md`](./specs/audit/security-audit.md) | Secretos, authn/authz, uploads, dependencias, CI/CD y privacidad | `audita la seguridad` o `/audit-security` |

> Estos specs **no se ejecutan solos**: solo cuando el usuario da la orden. Son de solo lectura y nunca atacan producción.

---

## Limitaciones conocidas y próximos pasos

- **Latencia de producción:** Render y la base de datos están en regiones distintas y el plan free limita la CPU. Las optimizaciones de T-128/T-129 redujeron un 30–40 % las acciones principales; el siguiente salto requiere mover Render a `eu-central` y/o subir de plan.
- **Carga inicial del tablero:** el frontend lanza varias consultas en paralelo (tareas, miembros, proyecto y notificaciones) que compiten por la instancia; está identificado como siguiente optimización (cargar notificaciones bajo demanda y agrupar rol/proyecto).
- **Transporte de tokens (ADR-001):** se mantiene Bearer + auto-refresh porque frontend y API son orígenes distintos; las cookies `httpOnly` exigirían un BFF. Riesgo residual y disparadores de reapertura en `security-checklist.md`.
- **MCP de Vercel:** configurado en OpenCode pero requiere autenticación OAuth (`/mcps` → `vercel` → sign in); el deploy por CLI y Git ya funcionan.
- **UI dark-only** (ADR-006), sin `ThemeContext`.
- **Sin invitaciones por email:** se añade un usuario ya registrado por email.

El detalle está en [`specs/taskflow/tasks.md`](./specs/taskflow/tasks.md) y [`specs/taskflow/security-checklist.md`](./specs/taskflow/security-checklist.md).

---

## Contributing

1. Lee [`specs/taskflow/constitution.md`](./specs/taskflow/constitution.md).
2. Toma una tarea `T-###` del backlog y sus `FR-###`/`BL-##`.
3. Crea una rama `feat/T-###-descripcion` (ver [`CONTRIBUTING.md`](./CONTRIBUTING.md)).
4. Añade tests y actualiza la spec/contrato si cambia el comportamiento.
5. Abre un PR referenciando `T-###` y los `FR-###`/`BL-##` cubiertos.

Commits en español con Conventional Commits (`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `chore`, `ci`).

## Licencia

MIT — ver [`LICENSE`](./LICENSE).
