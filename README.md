# TaskFlow API

API REST completa para gestión de tareas en equipo con autenticación JWT, equipos, proyectos y más.

[![Tests](https://img.shields.io/badge/tests-54%20passed-brightgreen)](https://github.com/anomalyco/taskflow-api/actions)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-blue)](https://fastapi.tiangolo.com/)

---

## Probar online

| Servicio     | URL                                                | Descripción                  |
| ------------ | -------------------------------------------------- | ---------------------------- |
| **Frontend** | https://taskflow-api-tau.vercel.app                | Interfaz de usuario completa |
| **API**      | https://web-production-053e1.up.railway.app        | Backend REST con Swagger     |
| **Health**   | https://web-production-053e1.up.railway.app/health | Estado del servidor          |

### Endpoints públicos

- `GET /` - Mensaje de bienvenida
- `GET /health` - Health check (BD, Redis, disco)
- `GET /docs` - Documentación Swagger interactiva

---

## Arquitectura

```
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│   Frontend      │ ───▶ │      TaskFlow API   │ ───▶ │   PostgreSQL    │
│   (Vercel)      │      │     (Railway)       │      │   (Database)    │
│                 │      │                     │      │                 │
│  React + Vite   │      │  FastAPI + JWT      │      │  SQLAlchemy     │
│  Tailwind CSS   │      │  Pydantic v2        │      │  Alembic        │
└─────────────────┘      └─────────────────────┘      └─────────────────┘
                                 │
                                 ▼
                          ┌─────────────────┐
                          │     Redis       │
                          │  (Rate Limit)   │
                          └─────────────────┘
```

### Stack tecnológico

| Capa              | Tecnología           | Justificación                                                                             |
| ----------------- | -------------------- | ----------------------------------------------------------------------------------------- |
| **Backend**       | FastAPI              | Alto rendimiento, validación automática con Pydantic, documentación interactiva integrada |
| **ORM**           | SQLAlchemy 2.0       | Maduro, type-safe con el nuevo API, previene SQL injection                                |
| **Base de datos** | PostgreSQL           | Robusto, relacional, ideal para datos estructurados de equipos/tareas                     |
| **Autenticación** | JWT + Refresh Tokens | Sin estado, segura, con rotación de tokens para mayor seguridad                           |
| **Rate Limiting** | SlowAPI              | Implementación simple de límite por IP                                                    |
| **Frontend**      | React + Vite         | Carga rápida, HMR, ecosistema maduro                                                      |
| **Estilos**       | Tailwind CSS         | Utility-first, consistente, rápido de prototipar                                          |
| **Deployment**    | Railway + Vercel     | CI/CD automático, escalable, free tier generoso                                           |

---

## Características

### Autenticación y Seguridad

- JWT con access y refresh tokens con rotación automática
- Rate limiting por IP (10 requests/minuto en login)
- Hash de contraseñas con bcrypt
- Headers de seguridad (X-Content-Type-Options, X-Frame-Options, HSTS)
- Logging estructurado con structlog y request_id
- Caching con Redis (degrada gracefully si no está disponible)
- Integración con Sentry para monitoreo de errores en producción

### Gestión de Equipos

- Equipos con membresías y roles (admin, member)
- Búsqueda de proyectos y tareas dentro del equipo
  - Invite de miembros por email
  - Actualización de roles y removal de miembros

### Proyectos

- Proyectos dentro de equipos
- Estados: active, archived
- Edición de proyectos (solo admins del equipo)
- Registro de actividad (creación, archival)

### Tareas

- Estados: todo, in_progress, done
- Prioridades: high, medium, low
- Asignación a miembros del equipo
- Fechas de vencimiento
- Filtros y paginación
- Registro de actividad completo
- Edición de tareas (solo creador o admin pueden editar)

### Colaboración

- Comentarios en tareas (muestra email del autor)
  - Editar comentarios (solo el autor)
  - Eliminar comentarios (autor o admin del equipo)
- Adjuntos de archivos (upload, download, delete)
- Notificaciones en tiempo real
- Activity log detallado (tareas y proyectos)

---

## Decisiones Técnicas

### 1. FastAPI + Pydantic v2

**Decisión:** Usar FastAPI como framework principal con Pydantic v2 para validación.

**Justificación:**

- Validación automática de request/response - reduce bugs y código repetitivo
- Documentación Swagger/OpenAPI automática - developers pueden probar inmediatamente
- Alto rendimiento async - ideal para I/O bound operations como API calls
- Type hints integrados con Python - mejor DX y autocompletado

### 2. SQLAlchemy con joinedload

**Decisión:** Usar `joinedload()` para relaciones eager loading.

**Justificación:**

- Previene el problema N+1 queries - cada tarea con su assignee hace 1 query en lugar de N+1
- Ejemplo: listar 20 tareas con assignees = 1 query en lugar de 21
- Mejor rendimiento en producción y menor carga en BD

```python
# Antes: N+1 queries
tasks = db.query(Task).filter(...).all()  # 1 query
for task in tasks:
    print(task.assignee.email)  # N queries adicionales

# Después: 1 query con join
tasks = db.query(Task).options(joinedload(Task.assignee)).filter(...).all()
```

### 3. JWT con refresh tokens y rotación

**Decisión:** Implementar sistema de tokens duales con rotación.

**Justificación:**

- Access tokens cortos (30 min) = menor ventana de vulnerabilidad si roban token
- Refresh tokens permiten sesión larga sin mantener access token válido
- Rotación = cada refresh genera nuevos tokens, invalida el anterior
- Si alguien roba refresh token, se invalida en el próximo uso legítimo

### 4. Rate limiting con SlowAPI

**Decisión:** Limitar requests por IP.

**Justificación:**

- Previene ataques de fuerza bruta en endpoints de login
- Protege contra DDoS básico
- Implementado a nivel de aplicación, no requiere infraestructura adicional
- 10 requests/minuto es restrictivo para usuarios reales pero efectivo contra bots

---

## 📡 API Reference

### Autenticación

| Método | Endpoint                | Descripción                            |
| ------ | ----------------------- | -------------------------------------- |
| POST   | `/api/v1/auth/register` | Registrar nuevo usuario                |
| POST   | `/api/v1/auth/login`    | Login (retorna access + refresh token) |
| POST   | `/api/v1/auth/refresh`  | Refrescar access token                 |
| POST   | `/api/v1/auth/logout`   | Logout e invalidar refresh token       |

### Equipos

| Método | Endpoint                               | Descripción                |
| ------ | -------------------------------------- | -------------------------- |
| POST   | `/api/v1/teams/`                       | Crear equipo               |
| GET    | `/api/v1/teams/`                       | Listar equipos del usuario |
| GET    | `/api/v1/teams/{id}`                   | Ver equipo con miembros    |
| GET    | `/api/v1/teams/{id}/search`            | Buscar proyectos/tareas    |
| POST   | `/api/v1/teams/{id}/members`           | Invitar miembro (admin)    |
| GET    | `/api/v1/teams/{id}/members`           | Listar miembros            |
| PATCH  | `/api/v1/teams/{id}/members/{user_id}` | Actualizar rol (admin)     |
| DELETE | `/api/v1/teams/{id}/members/{user_id}` | Remover miembro (admin)    |

### Proyectos

| Método | Endpoint                                      | Descripción                 |
| ------ | --------------------------------------------- | --------------------------- |
| POST   | `/api/v1/teams/{team}/projects/`              | Crear proyecto              |
| GET    | `/api/v1/teams/{team}/projects/`              | Listar proyectos            |
| GET    | `/api/v1/teams/{team}/projects/{id}`          | Ver proyecto                |
| PATCH  | `/api/v1/teams/{team}/projects/{id}`          | Actualizar proyecto (admin) |
| DELETE | `/api/v1/teams/{team}/projects/{id}`          | Eliminar proyecto (admin)   |
| GET    | `/api/v1/teams/{team}/projects/{id}/activity` | Ver actividad del proyecto  |

### Tareas

| Método | Endpoint                                                      | Descripción                     |
| ------ | ------------------------------------------------------------- | ------------------------------- |
| POST   | `/api/v1/teams/{team}/projects/{project}/tasks/`              | Crear tarea                     |
| GET    | `/api/v1/teams/{team}/projects/{project}/tasks/`              | Listar tareas (soporta filtros) |
| GET    | `/api/v1/teams/{team}/projects/{project}/tasks/{id}`          | Ver tarea específica            |
| PATCH  | `/api/v1/teams/{team}/projects/{project}/tasks/{id}`          | Actualizar tarea                |
| DELETE | `/api/v1/teams/{team}/projects/{project}/tasks/{id}`          | Eliminar tarea                  |
| PATCH  | `/api/v1/teams/{team}/projects/{project}/tasks/{id}/assign`   | Asignar tarea (admin)           |
| GET    | `/api/v1/teams/{team}/projects/{project}/tasks/{id}/activity` | Ver actividad de la tarea       |

### Filtros de tareas

- `status` - todo, in_progress, done
- `priority` - high, medium, low
- `assigned_to` - user_id
- `due_before`, `due_after` - fechas
- `sort_by` - created_at, title, priority, due_date
- `page`, `page_size` - paginación

### Otros recursos

- **Comentarios:** `/api/v1/teams/{team}/projects/{project}/tasks/{task}/comments/` (list, create, PATCH update, DELETE)
- **Adjuntos:** `/api/v1/teams/{team}/projects/{project}/tasks/{task}/attachments/` (upload, list, download, delete)
- **Notificaciones:** `/api/v1/notifications/` (list, mark read, mark all read)
- **Actividad:** `/api/v1/teams/{team}/projects/{project}/tasks/{task}/activity`

> Documentación completa e interactiva disponible en `/docs`

---

## Tests

### Backend (pytest)

```bash
# Ejecutar todos los tests
pytest -v

# Tests por módulo
pytest tests/test_auth.py -v
pytest tests/test_tasks.py -v
pytest tests/test_teams.py -v

# Con coverage
pytest --cov=app --cov-report=html
```

### Frontend (vitest)

```bash
# Tests interactivos
npm run test:watch

# Tests una vez
npm run test
```

### Cobertura actual: 54 tests

| Módulo        | Tests |
| ------------- | ----- |
| Auth          | 8     |
| Teams         | 8     |
| Projects      | 7     |
| Tasks         | 8     |
| Comments      | 6     |
| Filters       | 5     |
| Activity      | 5     |
| Notifications | 5     |
| Attachments   | 5     |

---

## Frontend

El frontend es una aplicación React desplegada en Vercel:

- **Stack:** React 18 + Vite + Tailwind CSS 4
- **Estado:** React Query + Context API
- **Componentes:** Lucide React (icons), React Hot Toast
- **Drag & Drop:** @dnd-kit
- **URL:** https://taskflow-api-tau.vercel.app

### Características del Frontend

- **Login/Register**: Autenticación de usuarios
- **Dashboard**: Vista de equipos con acceso rápido a proyectos
- **TeamDetail**:
  - Ver equipo y proyectos
  - Búsqueda de proyectos y tareas dentro del equipo
- **ProjectBoard**:
  - Kanban board con drag-and-drop
  - Filtros por estado, prioridad y assignee
  - Crear tareas
  - Historial de actividad del proyecto
  - Editar y archivar proyecto (solo admins)
- **TaskDetail**:
  - Ver y editar tarea (solo creador/admin)
  - Comentarios con email del autor
  - Adjuntos de archivos (upload, download, delete)
  - Historial de actividad
- **Profile**:
  - Cambiar contraseña

### Estructura del frontend

```
frontend/
├── src/
│   ├── api/           # Cliente API (fetch wrapper)
│   ├── components/    # Componentes reutilizables
│   ├── context/       # AuthContext, ThemeContext
│   └── pages/         # Páginas principales
│       ├── Login.jsx
│       ├── Register.jsx
│       ├── Dashboard.jsx
│       ├── TeamDetail.jsx
│       ├── ProjectBoard.jsx
│       └── TaskDetail.jsx
```

### Variables de entorno

```bash
VITE_API_URL=https://web-production-053e1.up.railway.app
```

---

## Deployment

### Backend - Railway

```
URL: https://web-production-053e1.up.railway.app
RAM: 512MB
Disk: 1GB
```

**Variables requeridas:**

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SENTRY_DSN=optional
REDIS_URL=optional
```

**Dockerfile:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN mkdir -p /uploads
CMD ["python", "app/main.py"]
```

### Frontend - Vercel

```
URL: https://taskflow-api-tau.vercel.app
```

Desplegado desde la carpeta `frontend/` con configuración automática de Vite.

---

## Inicio rápido

### Con Docker (recomendado)

```bash
# Clonar el repositorio
git clone https://github.com/anomalyco/taskflow-api.git
cd taskflow-api

# Iniciar servicios
docker compose up -d

# La API estará disponible en http://localhost:8000
# Swagger: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

### Sin Docker

```bash
# Python 3.11+ requerido
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu configuración

uvicorn app.main:app --reload
```

### Variables de entorno (.env)

```bash
# Requerido
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow
SECRET_KEY=your-secret-key-at-least-32-characters-long

# Opcional
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
```

---

## Licencia

MIT License - ver [LICENSE](LICENSE) para más detalles.

---

## Contributing

1. Fork el repositorio
2. Crear branch para feature (`git checkout -b feature/amazing`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing`)
5. Crear Pull Request
