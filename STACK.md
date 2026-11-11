# TaskFlow — Stack tecnológico

> Documento de referencia rápida. La fuente de verdad es [`specs/taskflow/plan.md`](./specs/taskflow/plan.md) (arquitectura y ADRs) y [`specs/taskflow/spec.md`](./specs/taskflow/spec.md) (requisitos).

## Backend

### Core

- **Python 3.12** — runtime en Docker/CI.
- **FastAPI** — framework HTTP async, OpenAPI automático.
- **Uvicorn** — servidor ASGI.

### Datos

- **PostgreSQL 15** — base de datos relacional (InsForge en producción).
- **SQLAlchemy 2** — ORM y sesiones.
- **Alembic** — migraciones; única fuente de esquema en producción.
- **psycopg2-binary** — driver PostgreSQL.

### Validación y configuración

- **Pydantic v2** — schemas request/response.
- **pydantic-settings** — configuración desde entorno y `.env`.
- **python-dotenv** — carga de `.env` en desarrollo.

### Autenticación y seguridad

- **PyJWT** — JWT HS256.
- **bcrypt** — hashing de contraseñas.
- **email-validator** — validación de emails.
- **slowapi** — rate limiting por IP.
- **Headers de seguridad** — middleware propio (HSTS, nosniff, X-Frame-Options, XSS).

### Observabilidad

- **structlog** — logs JSON con `request_id`.
- **sentry-sdk[fastapi]** — errores (opcional).
- **Redis** — cache/rate limiting cuando está disponible (degradación controlada).

### Utilidades

- **python-multipart** — uploads.
- **aiofiles** — operaciones de archivo async.
- **httpx** — cliente HTTP async (tests).

### Testing

- **pytest**, **pytest-cov**, **pytest-asyncio**.
- Tests de integración con `TestClient` y SQLite en memoria (P6: PostgreSQL).

---

## Frontend

### Core

- **React 18** — UI.
- **React Router 7** — routing SPA.
- **Vite 8** - dev server y build.

### Estado y datos

- **TanStack React Query 5** — fetching, caché y mutaciones.
- **fetch nativo** — cliente centralizado en `src/api/index.js` (sin axios).

### UI

- **Tailwind CSS 4** — estilos utility-first.
- **Lucide React** — iconos.
- **React Hot Toast** — toasts.
- **@dnd-kit/core / sortable / utilities** — Kanban drag & drop.

### Testing

- **Vitest**, **Testing Library**, **jsdom**.
- 6 tests de componentes/flujos.

---

## Infraestructura

| Servicio | Uso |
|---|---|
| **Render** | Backend FastAPI |
| **Vercel** | Frontend React |
| **InsForge** | PostgreSQL gestionado |
| **GitHub Actions** | Tests backend + Codecov |
| **Docker / docker-compose** | PostgreSQL + Redis + API local |

### Variables clave

```bash
ENVIRONMENT=development
SECRET_KEY=...
DATABASE_URL=postgresql://...
CORS_ORIGINS=http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379/0        # opcional
SENTRY_DSN=...                            # opcional
MAX_UPLOAD_SIZE=10485760
UPLOAD_DIR=uploads
```

---

## Deuda técnica conocida

- Migrar tests de integración a PostgreSQL.
- Auto-refresh de sesión en el frontend.
- Object storage para adjuntos (hoy disco local).
- Paginación uniforme y envelope de errores.
- Ruff/mypy/pre-commit y lockfiles.
- SSE para notificaciones (hoy polling).

Ver [`specs/taskflow/baseline.md`](./specs/taskflow/baseline.md) y [`specs/taskflow/tasks.md`](./specs/taskflow/tasks.md).
