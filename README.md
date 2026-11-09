# TaskFlow API

API REST para gestión de tareas en equipo con autenticación JWT, equipos, proyectos, tablero Kanban, comentarios, adjuntos, notificaciones y registro de actividad.

[![Tests](https://img.shields.io/badge/backend%20tests-101%20passed-brightgreen)](./tests)
[![Frontend](https://img.shields.io/badge/frontend%20tests-12%20passed-brightgreen)](./frontend/src/test)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-blue)](https://fastapi.tiangolo.com/)

> **Documentación de producto y arquitectura:** [`specs/taskflow/`](./specs/taskflow/). La spec es la fuente de verdad; el código se implementa contra ella.

---

## Probar online

| Servicio | URL | Descripción |
|---|---|---|
| **Frontend** | https://taskflow-api-tau.vercel.app | Interfaz React |
| **API** | https://taskflow-api-gkgl.onrender.com/api/v1 | Backend REST |
| **Swagger** | https://taskflow-api-gkgl.onrender.com/docs | Documentación interactiva |
| **Health** | https://taskflow-api-gkgl.onrender.com/health | Estado del servidor |
| **Liveness** | https://taskflow-api-gkgl.onrender.com/health/live | Proceso vivo |
| **Readiness** | https://taskflow-api-gkgl.onrender.com/health/ready | DB accesible |

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
                                                  ├── Redis opcional (rate limiting/cache)
                                                  ├── Sentry opcional (errores)
                                                  └── Object storage (P4; hoy disco local)
```

### Stack

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **ORM / DB** | SQLAlchemy 2, PostgreSQL 15, Alembic |
| **Validación** | Pydantic v2, pydantic-settings |
| **Auth** | JWT (`python-jose`), bcrypt, access 15 min + refresh 7 días |
| **Seguridad** | SlowAPI, headers de seguridad, lockout de cuenta, CORS por allowlist |
| **Observabilidad** | structlog (JSON + request ID), Sentry opcional |
| **Frontend** | React 18, Vite 5, React Router 7 |
| **Datos front** | TanStack React Query 5, `fetch` |
| **UI** | Tailwind CSS 4, Lucide React, React Hot Toast, `@dnd-kit` |
| **Tests** | pytest + pytest-cov (101), Vitest + Testing Library (12) |
| **CI/CD** | GitHub Actions, Render, Vercel, InsForge |
| **Contenedores** | Docker, docker-compose (PostgreSQL + Redis + API) |

Los adjuntos se guardan por defecto en PostgreSQL (`STORAGE_BACKEND=database`) para sobrevivir a los discos efímeros de Render. En desarrollo se puede usar `STORAGE_BACKEND=local`.

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
- Fail-fast en producción si falta `SECRET_KEY` o `DATABASE_URL`.
- Headers de seguridad: `X-Content-Type-Options`, `X-Frame-Options`, HSTS, XSS.
- Cambio de contraseña desde el perfil.
- Logging estructurado con `request_id` y `X-Request-ID`.

> El refresco automático en el cliente está planificado en P2. Hoy el endpoint funciona, pero el frontend aún no renueva la sesión por sí solo.

### Equipos

- Crear/listar equipos y consultarlos por **ID o slug**.
- Miembros con roles `admin` / `member`.
- Añadir un usuario registrado por email (no es una invitación por correo).
- Listar miembros, cambiar rol y expulsar.
- Un miembro puede salir del equipo.
- **Siempre debe quedar al menos un admin** (guard de último admin).
- Búsqueda de proyectos y tareas dentro del equipo.

### Proyectos

- Proyectos dentro de un equipo, con estado `active` / `archived`.
- Crear (cualquier miembro), editar/archivar (solo admin).
- `DELETE /projects/{id}` **archiva** el proyecto; no lo borra físicamente.
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

- **Comentarios**: crear, listar, editar (autor) y borrar (autor o admin).
- **Adjuntos**: subir, listar, descargar y borrar.
  - Límite de 10 MB configurable.
  - Allowlist de extensiones/MIME.
  - Nombres saneados y claves de almacenamiento únicas (sin path traversal).
  - Solo el uploader o un admin puede borrar.
- **Notificaciones** in-app al asignar una tarea o comentar una tarea asignada.
- Campana con contador de no leídas; refresco cada 30 s (polling; SSE planificado en P4).
- **Activity log** de tareas, proyectos, comentarios y adjuntos.

### Frontend

- **Login / Register**.
- **Dashboard**: equipos, crear equipo.
- **TeamDetail**: proyectos, miembros, roles, búsqueda, crear/editar proyecto.
- **ProjectBoard**: Kanban con drag & drop, filtros en URL, búsqueda local, crear tarea, actividad, editar/archivar proyecto.
- **TaskDetail**: editar tarea, comentarios, adjuntos, actividad.
- **Profile**: cambio de contraseña.
- Toasts, skeletons, estados de carga/vacío y 404.

---

## API

Base: `/api/v1`. Contrato completo en [`specs/taskflow/contracts/api.md`](./specs/taskflow/contracts/api.md).

| Grupo | Endpoints principales |
|---|---|
| **Auth** | `POST /auth/register`, `/login`, `/refresh`, `/logout` |
| **Users** | `GET /users/me`, `PUT /users/me` |
| **Teams** | `POST/GET /teams/`, `GET /teams/{id}`, `GET /teams/{id}/search`, `POST/GET/PATCH/DELETE /teams/{id}/members` |
| **Projects** | `POST/GET /teams/{id}/projects/`, `GET/PATCH/DELETE /teams/{id}/projects/{id}`, `GET .../activity` |
| **Tasks** | `POST/GET .../tasks/`, `GET/PATCH/DELETE .../tasks/{id}`, `PATCH .../assign`, `GET .../activity` |
| **Comments** | `POST/GET .../comments/`, `PATCH/DELETE .../comments/{id}` |
| **Attachments** | `POST/GET .../attachments/`, `GET .../{id}/download`, `DELETE .../{id}` |
| **Notifications** | `GET /notifications/`, `PATCH /{id}/read`, `PATCH /read-all` |

Documentación interactiva: `/docs`. OpenAPI: `/openapi.json`.

### Errores

```json
{
  "detail": "Mensaje de error"
}
```

Los errores incluyen el envelope estable `{error: {code, message, details, request_id}}` y mantienen `detail` por compatibilidad.

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

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
npm run dev                  # http://localhost:5173
```

### Variables de entorno

Ver [`.env.example`](./.env.example). Las críticas:

```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
```

Opcionales: `REDIS_URL`, `SENTRY_DSN`, `MAX_UPLOAD_SIZE`, `UPLOAD_DIR`, `ALLOWED_UPLOAD_EXTENSIONS`.

---

## Base de datos y migraciones

Alembic es la única fuente de esquema en producción. La aplicación **no** crea tablas al arrancar.

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "descripcion"
```

Modelo actual: `users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens`.

El modelo objetivo (slugs, storage, sesiones, índices) está en [`specs/taskflow/data-model.md`](./specs/taskflow/data-model.md).

---

## Tests

```bash
# Backend
pytest -v
pytest --cov=app --cov-report=html

# Un archivo / test
pytest tests/test_auth.py
pytest tests/test_auth.py::test_register_user

# Frontend
cd frontend
npm run test
npm run build
```

Estado actual: **101 tests backend** y **12 tests frontend**. Los tests de integración usan SQLite en memoria; P6 los migrará a PostgreSQL (ADR-008).

---

## Deployment

### Backend — Render

- Build: `pip install -r requirements.txt`
- Start: `python -m app.main` (o `uvicorn app.main:app`)
- Variables: `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS=https://taskflow-api-tau.vercel.app`, opcionales `REDIS_URL`, `SENTRY_DSN`.
  - Si usas un dominio propio en Vercel, añádelo separado por comas.
  - Sin `CORS_ORIGINS`, la app **no arranca en producción** (fail-fast).
- Ejecutar `alembic upgrade head` antes del despliegue. `alembic/env.py` usa `DATABASE_URL`.
- Los adjuntos se guardan en PostgreSQL por defecto (`STORAGE_BACKEND=database`), por lo que sobreviven a los redeploys. Cambiar a `local` solo para desarrollo.

### Frontend — Vercel

- Directorio: `frontend/`
- Variable: `VITE_API_URL=https://taskflow-api-gkgl.onrender.com`
- `vercel.json` reescribe rutas SPA a `/`.

### Base de datos — InsForge

PostgreSQL gestionado. Guardar backups y probar restore (ver `specs/taskflow/data-model.md`).

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

specs/taskflow/          # SDD: constitución, baseline, spec, plan, tasks, datos, API
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

---

## Limitaciones conocidas y próximos pasos

- Auto-refresh de sesión en el frontend (P2).
- Migración a cookies `httpOnly` o decisión formal (ADR-001).
- Adjuntos en object storage S3-compatible (P4).
- Notificaciones en tiempo real con SSE (P4).
- Paginación uniforme, envelope de errores y permisos por endpoint (P3).
- Tests de integración contra PostgreSQL y CI de frontend (P6).
- Tema: solo oscuro en este ciclo; el `ThemeContext` muerto se eliminó (ADR-006).

El detalle y el orden están en [`specs/taskflow/tasks.md`](./specs/taskflow/tasks.md).

---

## Contributing

1. Lee [`specs/taskflow/constitution.md`](./specs/taskflow/constitution.md).
2. Toma una tarea `T-###` del backlog.
3. Crea una rama `feature/T-###-descripcion`.
4. Añade tests y actualiza la spec/contrato si cambia el comportamiento.
5. Abre un PR referenciando `T-###` y los `FR-###`/`BL-##` cubiertos.

## Licencia

MIT — ver [`LICENSE`](./LICENSE).
