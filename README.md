# TaskFlow API

API REST con FastAPI y JWT para gestión de tareas con soporte para equipos, proyectos y más.

## Características

- Autenticación JWT con refresh tokens
- Equipos y membresías con roles (admin, member, viewer)
- Proyectos con funcionalidad de archivo
- Tareas con estados, prioridades, assignees y fechas
- Comentarios en tareas
- Registro de actividad
- Filtros y búsqueda
- Archivos adjuntos (hasta 10MB)
- Notificaciones
- Rate limiting
- CORS habilitado
- Health check endpoint
- Cabeceras de seguridad HTTP
- Bloqueo de cuenta tras intentos fallidos
- Sanitización de campos de texto

## Instalación local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

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
