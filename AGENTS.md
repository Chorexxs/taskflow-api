# AGENTS.md — TaskFlow API Developer Guide

Este documento es la guía operativa para agentes y personas que trabajan en el repositorio. La **fuente de verdad funcional** es [`specs/taskflow/spec.md`](./specs/taskflow/spec.md); la arquitectura y las decisiones están en [`specs/taskflow/plan.md`](./specs/taskflow/plan.md).

---

## Project Overview

TaskFlow es una API REST para gestión de tareas en equipo, con frontend React. Incluye:

- Autenticación JWT con refresh rotativo, bloqueo de cuenta y rate limiting.
- Equipos con roles `admin` / `member`.
- Proyectos y tareas con tablero Kanban.
- Comentarios, adjuntos, notificaciones y activity log.
- Búsqueda dentro del equipo.
- Caché Redis opcional y Sentry opcional.

### Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2, PostgreSQL, Alembic, Pydantic v2.
- **Frontend:** React 18, Vite 8, Vitest 5, React Router 7, TanStack Query 5, Tailwind CSS 4.
- **Tests:** pytest (backend), Vitest + Testing Library (frontend).
- **Deploy:** Render (API), Vercel (frontend), InsForge (PostgreSQL).

---

## Flujo SDD (obligatorio)

1. Lee `specs/taskflow/constitution.md`.
2. Identifica la tarea `T-###` y el requisito `FR-###`/hallazgo `BL-##`.
3. Implementa el cambio **con tests**.
4. Actualiza `spec.md`, `contracts/api.md` o `data-model.md` si cambia el comportamiento o el contrato.
5. Referencia `T-###` en el PR.

No se acepta código sin spec ni cambios de contrato sin actualizar la documentación.

### Auditorías bajo demanda

Los specs de auditoría viven en [`specs/audit/`](./specs/audit/) y **no se
ejecutan de forma autónoma**. Solo se activan cuando el usuario lo ordena:

| Spec | Activación | Comando OpenCode |
|---|---|---|
| [`code-audit.md`](./specs/audit/code-audit.md) | `audita el código` | `/audit-code [alcance]` |
| [`security-audit.md`](./specs/audit/security-audit.md) | `audita la seguridad` | `/audit-security [alcance]` |

Reglas:

1. Leer estos specs no es una orden de ejecución.
2. La auditoría es de solo lectura; no modifica código ni credenciales.
3. No se ataca producción ni se exfiltran datos.
4. Los secretos se reportan redactados.
5. Un hallazgo `CA-0`/`SEC-0` se reporta de inmediato.

---

## Build / Lint / Test Commands

```bash
# Instalar dependencias
pip install -r requirements.txt

# Desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m uvicorn app.main:app --reload
python -m app.main

# Tests
pytest
pytest tests/test_auth.py
pytest tests/test_auth.py::test_register_user
pytest -v
pytest --cov=app --cov-report=html

# Lint / tipos
ruff check app tests
ruff format --check app tests
mypy app
pre-commit run --all-files

# Migraciones
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "descripcion"

# Drill de backup/restore (T-102)
python scripts/backup_restore_drill.py --source-url "$env:DATABASE_URL" `
  --target-url postgresql://postgres@127.0.0.1:5432/taskflow_restore `
  --pg-bin "C:/Program Files/PostgreSQL/16/bin" --schema public

# Pre-commit completo (requiere gitleaks en PATH; ver .pre-commit-config.yaml)
pre-commit install
pre-commit run --all-files

# Frontend
cd frontend
npm install
npm run dev
npm run test
npm run test:coverage
npm run build
npm run lint
```

### Docker

```bash
docker compose up -d       # PostgreSQL + Redis + API
docker compose down
```

---

## Environment Setup

```bash
cp .env.example .env
# Editar DATABASE_URL y SECRET_KEY
```

Variables críticas:

```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
```

Opcionales: `SECRET_KEY_PREVIOUS`, `REDIS_URL`, `RATE_LIMIT_ENABLED`, `RATE_LIMIT_STORAGE_URI`, `FORWARDED_ALLOW_IPS`, `SSE_POLL_SECONDS`, `SSE_FALLBACK_POLL_SECONDS`, `SSE_HEARTBEAT_SECONDS`, `SSE_MAX_CONNECTIONS`, `SSE_MAX_CONNECTIONS_PER_USER`, `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `STORAGE_BACKEND`, `INSFORGE_URL`, `INSFORGE_API_KEY`, `INSFORGE_STORAGE_BUCKET`, `MAX_UPLOAD_SIZE`, `UPLOAD_DIR`, `ALLOWED_UPLOAD_EXTENSIONS`, `CLAMAV_HOST`, `CLAMAV_PORT`, `CLAMAV_TIMEOUT_SECONDS`, `CLAMAV_REQUIRED`, `POOL_SIZE`, `MAX_OVERFLOW`, `NOTIFICATION_RETENTION_DAYS`, `ACTIVITY_RETENTION_DAYS`, `IDEMPOTENCY_KEY_TTL_HOURS`.

**Producción:** `SECRET_KEY` y `DATABASE_URL` son obligatorias; la app falla al arrancar si faltan. `CORS_ORIGINS` debe ser una allowlist explícita.

---

## File Structure

```
app/
├── main.py              # App FastAPI, CORS, middleware, health, routers
├── config.py            # Settings centrales y fail-fast
├── auth.py              # JWT, bcrypt, lockout, revocación
├── database.py          # Engine, sesión, get_db
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Schemas Pydantic
├── crud.py              # Acceso a datos
├── dependencies.py      # Resolución de equipo y permisos
├── exceptions.py        # Excepciones de dominio
├── cache.py             # Redis opcional
├── logging_config.py    # structlog
├── middleware.py        # Request ID + logging
└── routers/             # auth, users, teams, projects, tasks,
                         # comments, attachments, notifications

frontend/src/
├── api/index.js         # Cliente fetch centralizado y errores tipados
├── components/          # Layout, TaskCard, NotificationsBell, Skeleton
├── context/             # AuthContext
├── pages/               # Login, Register, Dashboard, TeamDetail,
│                        # ProjectBoard, TaskDetail, Profile, NotFound
├── test/                # Setup y tests Vitest
├── App.jsx
└── main.jsx

specs/taskflow/          # SDD (constitution, baseline, spec, plan, tasks, data, API, threat-model)
specs/audit/             # Auditorías bajo demanda (código y ciberseguridad)
tests/                   # pytest
alembic/                 # migraciones
uploads/                 # adjuntos locales (dev; producción requiere storage)
```

---

## Code Style

### Imports

- Imports absolutos: `from app import crud`, no `from .. import crud`.
- Orden: standard library, third-party, local.
- Alfabético dentro de cada grupo.

### Types

- Python 3.10+ con `X | None`.
- `Annotated` para dependencias FastAPI.
- Anotar retornos en funciones públicas.
- Pydantic v2: usar `model_config = ConfigDict(from_attributes=True)`, no `class Config`.

### Naming

- Variables/funciones: `snake_case`.
- Clases: `PascalCase`.
- Constantes: `UPPER_SNAKE_CASE`.
- Privadas: `_private_function`.

### Errors

- Usar `HTTPException` con status correcto y mensajes claros.
- Los errores de auth incluyen `WWW-Authenticate: Bearer`.
- En el frontend, lanzar `ApiError` desde el cliente; no tratar errores como datos.
- No filtrar rutas internas, stack traces ni datos de otros usuarios.

### Database

- `timestamptz` en UTC.
- Enums como `VARCHAR + CHECK` (no enums nativos).
- Índices para filtros/orden usados.
- `joinedload` para relaciones que se serializan y evitan N+1.
- Alembic es la única fuente de esquema en producción. **No usar `create_all`.**

---

## Commits

- **Siempre en español**, incluidos el asunto y el cuerpo.
- Formato Conventional Commits: `tipo(alcance): resumen`.
- Tipos permitidos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `style`, `build`, `ci`.
- Asunto en imperativo, minúscula inicial tras los dos puntos, sin punto final y ≤ 72 caracteres.
- Cuerpo opcional en español: qué cambia y por qué; referencia `T-###`, `FR-###` o `BL-##`.
- Ejemplos:
  - `feat(tareas): añadir endpoint para cambiar solo el estado`
  - `fix(adjuntos): sanear el nombre antes de construir la ruta`
  - `docs(despliegue): marcar Vercel como verificado`

---

## Invariantes de autenticación y permisos

### Tokens

- Access token: 15 min por defecto; tipo `access`; no revocado.
- Refresh token: 7 días por defecto; tipo `refresh`; rotación en cada refresh.
- Refresh viaja en el **body** JSON, nunca en query string.
- Logout revoca access y refresh; es idempotente.
- Cambiar contraseña debe revocar sesiones (P2).
- `SECRET_KEY` nunca tiene fallback en producción. La rotación usa `SECRET_KEY_PREVIOUS` solo para verificar (ADR-012).

### Permisos (resumen)

| Acción | Admin | Creador | Asignado | Member |
|---|---:|---:|---:|---:|
| Ver equipo/proyectos/tareas | ✅ | ✅ | ✅ | ✅ |
| Editar/archivar equipo | ✅ | ❌ | ❌ | ❌ |
| Gestionar miembros | ✅ | ❌ | ❌ | ❌ |
| Crear proyecto/tarea | ✅ | ✅ | ✅ | ✅ |
| Editar todos los campos de tarea | ✅ | ✅ | ❌ | ❌ |
| Cambiar solo estado (Kanban) | ✅ | ✅ | ✅ | ✅ |
| Asignar tarea | ✅ | ✅ | ❌ | ❌ |
| Eliminar tarea | ✅ | ✅ | ❌ | ❌ |
| Comentar | ✅ | ✅ | ✅ | ✅ |
| Editar comentario | ❌ | solo propio | solo propio | solo propio |
| Eliminar comentario | ✅ | solo propio | solo propio | solo propio |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Eliminar adjunto | ✅ | solo propio | solo propio | solo propio |

Reglas:

1. Siempre debe quedar al menos un admin en el equipo.
2. Un ex-miembro no conserva acceso a nada.
3. La UI oculta acciones, pero **la API decide**.
4. Un recurso de otro equipo se trata como 404; la falta de rol como 403.

---

## API Conventions

- Base: `/api/v1`.
- JSON en `snake_case`; fechas ISO 8601 UTC.
- `Authorization: Bearer <access_token>`.
- Paginación de tareas: `{items,total,page,pages,has_next}` con `page`/`page_size` (máx. 100).
- Identificadores: preferir `id` y `slug`; nombre/título están deprecados.
- `DELETE /projects/{id}` **archiva**; documentarlo así.
- Errores actuales: `{"detail": "..."}`. El envelope `{error:{code,message,details,request_id}}` es el objetivo de P3.
- Contrato completo: `specs/taskflow/contracts/api.md`.

---

## Testing Guidelines

- Usar `TestClient` y fixtures de `tests/conftest.py`.
- Aislar cada test: la DB se recrea por función.
- Cubrir: 401 sin token, 403 sin permiso, 404 recurso ajeno, 422 validación y camino feliz.
- Para uploads, usar `tmp_path` y `monkeypatch` de `UPLOAD_DIR`/`MAX_FILE_SIZE`.
- No usar servicios externos reales.
- Frontend: Vitest + Testing Library + jsdom; mockear `../api` y `react-hot-toast`.
- Los tests de integración usan PostgreSQL vía `TEST_DATABASE_URL`, con el esquema creado por Alembic y tablas truncadas entre tests (ADR-008). `TEST_USE_SQLITE=1` es solo un atajo para runs unitarios.
- Cobertura obligatoria en CI: **80 % backend** (`--cov-fail-under`) y **70 % frontend** en líneas/sentencias (`vitest` thresholds), con **55 % de ramas** porque el proveedor v8 de Vitest 5 mide todos los archivos fuente. No bajar los umbrales sin justificarlo en el PR.

---

## Deployment

### Backend — Render

- Build: `pip install -r requirements.txt`
- Start: `python -m app.main`
- Ejecutar `alembic upgrade head` antes de desplegar.
- Configurar `ENVIRONMENT=production`, `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`.
- El filesystem es efímero: no confiar en `uploads/` para producción.

### Frontend — Vercel

- Directorio `frontend/`, build `npm run build`.
- `VITE_API_URL` apunta al backend.

### Base de datos — InsForge

- PostgreSQL gestionado; backups y restore documentados en `specs/taskflow/data-model.md`.

---

## Pitfalls conocidos

1. **Nunca** poner `allow_origins=["*"]` con `allow_credentials=True`.
2. **Nunca** usar `file.filename` directamente para construir rutas.
3. **Nunca** confiar en `file.size`; el límite se aplica en streaming.
4. **Nunca** llamar `create_all` fuera de tests.
5. React Query 5: `invalidateQueries({ queryKey: [...] })`, no `invalidateQueries([...])`.
6. El payload de assign es `{user_id}`, no `{assigned_to}`.
7. Access token expirado: el refresh va en body y el frontend lo renueva proactivamente 60 s antes de expirar.
8. El `DELETE` de proyectos archiva; usa `/archive` y `/restore` para la semántica explícita.
9. Los adjuntos usan PostgreSQL por defecto (`STORAGE_BACKEND=database`); `local` solo para desarrollo.
10. La UI es solo oscura (ADR-006); no hay `ThemeContext`.

---

## Definition of Done

- [ ] Cumple los criterios de aceptación de `spec.md`.
- [ ] Tests nuevos/actualizados y suite verde.
- [ ] Lint/tipos/build sin errores (cuando aplique).
- [ ] Sin secretos ni PII en logs.
- [ ] Permisos verificados en servidor.
- [ ] Spec/contrato/modelo actualizados si cambió el comportamiento.
- [ ] Nota de despliegue/rollback si toca DB, auth o storage.
- [ ] PR referencia `T-###` y `FR-###`/`BL-##`.

---

## Required Environment Variables

```bash
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
CORS_ORIGINS=http://localhost:5173
```

---

## Tech Stack Reference

- FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PostgreSQL.
- JWT (`PyJWT`), bcrypt, slowapi, structlog, Sentry, Redis.
- React 18, Vite, React Router, TanStack Query, Tailwind CSS 4, Lucide, React Hot Toast, @dnd-kit.
- pytest, Vitest, Testing Library, GitHub Actions.
