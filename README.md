# TaskFlow API

API REST con FastAPI y JWT para gestión de tareas con soporte para equipos, proyectos y más.

## Inicio rápido (un comando)

```bash
docker compose up
```

La API estará disponible en http://localhost:8000

## Características

- Autenticación JWT con refresh tokens y rotación
- Equipos y membresías con roles (admin, member, viewer)
- Proyectos con funcionalidad de archivo
- Tareas con estados, prioridades, assignees y fechas
- Comentarios en tareas
- Registro de actividad
- Filtros y búsqueda
- Archivos adjuntos (hasta 10MB)
- Notificaciones
- Rate limiting por IP
- Logging estructurado con request_id
- Health check completo (BD, Redis, disco)
- Sentry para errores en producción
- Versionado API (/api/v1/)

## Instalación local

```bash
# Con Docker
docker compose up

# Sin Docker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Documentación

- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

## Endpoints (todos con prefijo /api/v1/)

### Auth
- POST `/api/v1/auth/register` - Registro
- POST `/api/v1/auth/login` - Login
- POST `/api/v1/auth/refresh` - Refresh token
- POST `/api/v1/auth/logout` - Logout

### Equipos
- POST `/api/v1/teams/` - Crear equipo
- GET `/api/v1/teams/` - Listar equipos
- GET `/api/v1/teams/{id}` - Ver equipo

### Proyectos
- POST `/api/v1/teams/{team}/projects/` - Crear proyecto
- GET `/api/v1/teams/{team}/projects/` - Listar proyectos

### Tareas
- POST `/api/v1/teams/{team}/projects/{project}/tasks/` - Crear tarea
- GET `/api/v1/teams/{team}/projects/{project}/tasks/` - Listar tareas

### Más endpoints en `/api/v1/docs`

## Tests

```bash
pytest -v
```

## Despliegue

Desplegado en Railway: https://web-production-053e1.up.railway.app/

## Endpoints - Auditoría de Seguridad

### Endpoints Públicos (sin autenticación)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar nuevo usuario |
| POST | `/auth/login` | Login (rate limited: 10/min) |
| GET | `/` | Mensaje de bienvenida |
| GET | `/health` | Health check |
| GET | `/docs` | Documentación Swagger |

### Endpoints Protegidos (requieren JWT)

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| GET | `/users/me` | Cualquier usuario |
| PUT | `/users/me` | Cualquier usuario |
| POST | `/auth/refresh` | Usuario autenticado |
| POST | `/auth/logout` | Usuario autenticado |

### Endpoints de Equipos

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| POST | `/teams/` | Cualquier usuario |
| GET | `/teams/` | Cualquier usuario |
| GET | `/teams/{team_id_or_slug}` | Miembro |
| POST | `/teams/{team_id_or_slug}/members` | Admin |
| GET | `/teams/{team_id_or_slug}/members` | Miembro |
| DELETE | `/teams/{team_id_or_slug}/members/{user_id}` | Admin |
| PATCH | `/teams/{team_id_or_slug}/members/{user_id}` | Admin |
| GET | `/teams/{team_id_or_slug}/search` | Miembro |

### Endpoints de Proyectos

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| POST | `/teams/{team}/projects/` | Miembro |
| GET | `/teams/{team}/projects/` | Miembro |
| GET | `/teams/{team}/projects/{project_id_or_slug}` | Miembro |
| PATCH | `/teams/{team}/projects/{project_id_or_slug}` | Admin |
| DELETE | `/teams/{team}/projects/{project_id_or_slug}` | Admin |
| POST | `/teams/{team}/projects/{project_id_or_slug}/archive` | Admin |
| GET | `/teams/{team}/projects/{project_id_or_slug}/activity` | Miembro |

### Endpoints de Tareas

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| POST | `/teams/{team}/projects/{project}/tasks/` | Miembro |
| GET | `/teams/{team}/projects/{project}/tasks/` | Miembro |
| GET | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Miembro |
| PATCH | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Miembro |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Creador/Admin |
| PATCH | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}/assign` | Admin |
| GET | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}/activity` | Miembro |

### Endpoints de Comentarios

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| POST | `/teams/{team}/projects/{project}/tasks/{task}/comments/` | Miembro |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/comments/` | Miembro |
| PATCH | `/teams/{team}/projects/{project}/tasks/{task}/comments/{comment_id}` | Autor/Admin |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task}/comments/{comment_id}` | Autor/Admin |

### Endpoints de Archivos Adjuntos

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| POST | `/teams/{team}/projects/{project}/tasks/{task}/attachments/` | Miembro |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/attachments/` | Miembro |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task}/attachments/{attachment_id}` | Uploader/Admin |

### Endpoints de Notificaciones

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| GET | `/notifications/` | Cualquier usuario |
| PATCH | `/notifications/{notification_id}/read` | Dueño |
| PATCH | `/notifications/read-all` | Cualquier usuario |

## Documentación

Accede a `/docs` para ver la documentación Swagger interactiva.

## Despliegue

Desplegado en Railway: https://web-production-053e1.up.railway.app/

## Tests

```bash
pytest
```
