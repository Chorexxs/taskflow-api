# TaskFlow API

API REST con FastAPI y JWT para gestión de tareas con soporte para equipos, proyectos y más.

## Características

- Autenticación JWT
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

## Instalación local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Ejecutar servidor
uvicorn app.main:app --reload
```

## Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar nuevo usuario |
| POST | `/auth/login` | Login y obtener token JWT |

### Usuarios
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/users/me` | Obtener perfil del usuario actual |
| PUT | `/users/me` | Actualizar perfil del usuario |

### Equipos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/teams/` | Crear equipo |
| GET | `/teams/` | Listar equipos del usuario |
| GET | `/teams/{team_id_or_slug}` | Obtener equipo por ID o slug |
| PUT | `/teams/{team_id_or_slug}` | Actualizar equipo |
| POST | `/teams/{team_id_or_slug}/members` | Invitar miembro |
| DELETE | `/teams/{team_id_or_slug}/members/{user_id}` | Eliminar miembro |
| PUT | `/teams/{team_id_or_slug}/members/{user_id}/role` | Actualizar rol |
| GET | `/teams/{team_id_or_slug}/search` | Buscar tareas/proyectos |

### Proyectos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/teams/{team}/projects/` | Crear proyecto |
| GET | `/teams/{team}/projects/` | Listar proyectos |
| GET | `/teams/{team}/projects/{project_id_or_slug}` | Obtener proyecto |
| PUT | `/teams/{team}/projects/{project_id_or_slug}` | Actualizar proyecto |
| DELETE | `/teams/{team}/projects/{project_id_or_slug}` | Eliminar proyecto |
| POST | `/teams/{team}/projects/{project_id_or_slug}/archive` | Archivar proyecto |
| GET | `/teams/{team}/projects/{project_id_or_slug}/activity` | Ver actividad |

### Tareas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/teams/{team}/projects/{project}/tasks/` | Crear tarea |
| GET | `/teams/{team}/projects/{project}/tasks/` | Listar tareas |
| GET | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Obtener tarea |
| PUT | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Actualizar tarea |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task_id_or_title}` | Eliminar tarea |

### Comentarios
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/teams/{team}/projects/{project}/tasks/{task}/comments/` | Crear comentario |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/comments/` | Listar comentarios |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task}/comments/{comment_id}` | Eliminar comentario |

### Archivos Adjuntos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/teams/{team}/projects/{project}/tasks/{task}/attachments/` | Subir archivo |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/attachments/` | Listar archivos |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/attachments/{attachment_id}` | Descargar archivo |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task}/attachments/{attachment_id}` | Eliminar archivo |

### Notificaciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/notifications/` | Listar notificaciones |
| PATCH | `/notifications/{notification_id}/read` | Marcar como leída |
| PATCH | `/notifications/read-all` | Marcar todas como leídas |

### Sistema
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Mensaje de bienvenida |
| GET | `/health` | Health check |

## Documentación

Accede a `/docs` para ver la documentación Swagger interactiva.

## Despliegue

Desplegado en Railway: https://web-production-053e1.up.railway.app/

## Tests

```bash
pytest
```
