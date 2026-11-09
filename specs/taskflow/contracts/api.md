# Contratos de API — TaskFlow

**Versión:** 1.0
**Base URL:** `/api/v1`
**Formato:** JSON UTF-8 (`application/json`) salvo uploads (`multipart/form-data`) y descargas (binario)
**Autenticación:** `Authorization: Bearer <access_token>`
**OpenAPI:** `/openapi.json` y `/docs` son parte del contrato. El snapshot se versiona y se valida en CI.

---

## 0. Estado de implementación

Implementado en P1:

- `POST /auth/refresh` acepta `{"refresh_token": "..."}` en el body y rota el token.
- `POST /auth/logout` revoca access + refresh y es idempotente (204).
- CORS con allowlist (`CORS_ORIGINS`).
- Uploads con nombre saneado, clave única, límite en streaming y allowlist MIME/extensión.
- `AttachmentOut` sin `file_path` ni `storage_key`.
- Asignación con `{user_id}` (no `{assigned_to}`).
- Cliente frontend con errores tipados (`ApiError`) y comprobación de `r.ok`.

Pendiente (P2–P3): envelope `{error:...}`, paginación uniforme, IDs/slugs, rate limit Redis, cookies/ADR-001 y SSE.

---

## 1. Convenciones

### 1.1 Versionado

- Todo endpoint público vive bajo `/api/v1`.
- Cambios incompatibles requieren `/api/v2` o deprecación documentada.
- Campos nuevos opcionales son compatibles; campos eliminados/renombrados no.
- Las deprecaciones se anuncian en la respuesta (`Deprecation`, `Sunset`) y en este documento.

### 1.2 Nombres y tipos

- JSON en `snake_case`.
- Fechas en ISO 8601 UTC (`2026-11-09T14:30:00Z`).
- IDs numéricos; slugs `[a-z0-9-]+`.
- Booleanos reales, no strings.
- `null` explícito para campos opcionales sin valor.

### 1.3 Content types

| Caso | Content-Type |
|---|---|
| JSON | `application/json` |
| Login | `application/x-www-form-urlencoded` (OAuth2 password flow) |
| Upload | `multipart/form-data` |
| Download | `application/octet-stream` o el MIME real |

---

## 2. Autenticación

### 2.1 Flujo de login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=secret
```

```json
200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Errores: `401` credenciales inválidas, `423` cuenta bloqueada, `429` rate limit.

### 2.2 Flujo de refresh

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJ..." }
```

```json
200 OK
{
  "access_token": "nuevo...",
  "refresh_token": "nuevo...",
  "token_type": "bearer"
}
```

Reglas:

- El refresh va en el **body**, nunca en query string.
- El token anterior se revoca y se emite uno nuevo (rotación).
- Si se reutiliza un refresh revocado → `401` y se revoca la familia.
- Si el usuario está inactivo/bloqueado → `401`.

### 2.3 Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <access>
Content-Type: application/json

{ "refresh_token": "eyJ..." }
```

```http
204 No Content
```

- Revoca access y refresh.
- Idempotente: repetir devuelve `204`.

### 2.4 Transporte en el navegador

- **P2:** Bearer + auto-refresh (transición).
- **Target (ADR-001):** refresh en cookie `HttpOnly; Secure; SameSite=Lax`; access en memoria. La API sigue aceptando Bearer para clientes programáticos.
- CSRF: `SameSite=Lax` + verificación de `Origin` en métodos mutables + header custom.

### 2.5 Reglas de autorización

Toda ruta anidada verifica en orden:

1. Token válido y no revocado.
2. Usuario activo.
3. Pertenencia al equipo.
4. Rol/ownership según la matriz de `spec.md`.

Un recurso de otro equipo se trata como `404` (no se filtra su existencia), salvo que el usuario sea miembro y solo le falte rol, que se trata como `403`.

---

## 3. Errores

### 3.1 Envelope

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task not found",
    "details": { "task_id": "123" },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

- `code`: estable, para programar.
- `message`: legible, sin datos sensibles.
- `details`: opcional, validación o contexto.
- `request_id`: mismo valor que `X-Request-ID`.

### 3.2 Status codes

| Status | Uso |
|---|---|
| `200` | Lectura/actualización exitosa |
| `201` | Creación |
| `204` | Borrado/acción sin cuerpo |
| `400` | Petición inválida no cubierta por 422 |
| `401` | No autenticado / token inválido |
| `403` | Autenticado sin permiso |
| `404` | Recurso inexistente o de otro ámbito |
| `409` | Conflicto (duplicado, último admin, estado incompatible) |
| `413` | Archivo demasiado grande |
| `415` | MIME/extensión no soportada |
| `422` | Validación de esquema |
| `423` | Cuenta bloqueada |
| `429` | Rate limit |
| `500` | Error interno |

### 3.3 Catálogo de códigos

| Code | Status | Cuándo |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Pydantic/validación |
| `UNAUTHORIZED` | 401 | Sin token |
| `INVALID_TOKEN` | 401 | Token malformado, tipo incorrecto o revocado |
| `TOKEN_EXPIRED` | 401 | Expiración |
| `FORBIDDEN` | 403 | Permiso genérico |
| `NOT_A_MEMBER` | 403 | No pertenece al equipo |
| `NOT_TEAM_ADMIN` | 403 | Requiere admin |
| `USER_NOT_FOUND` | 404 | Usuario inexistente |
| `TEAM_NOT_FOUND` | 404 | Equipo inexistente |
| `PROJECT_NOT_FOUND` | 404 | Proyecto inexistente |
| `TASK_NOT_FOUND` | 404 | Tarea inexistente |
| `COMMENT_NOT_FOUND` | 404 | Comentario inexistente |
| `ATTACHMENT_NOT_FOUND` | 404 | Adjunto inexistente |
| `NOTIFICATION_NOT_FOUND` | 404 | Notificación inexistente |
| `EMAIL_ALREADY_REGISTERED` | 409 | Registro duplicado |
| `ALREADY_MEMBER` | 409 | Membresía duplicada |
| `LAST_ADMIN` | 409 | Operación deja el equipo sin admin |
| `CONFLICT` | 409 | Conflicto de estado |
| `ACCOUNT_LOCKED` | 423 | Bloqueo por intentos |
| `FILE_TOO_LARGE` | 413 | Upload > límite |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | MIME/extensión no permitida |
| `RATE_LIMITED` | 429 | Límite excedido |
| `INTERNAL_ERROR` | 500 | Error no controlado |

---

## 4. Paginación

### 4.1 Query

```http
?page=1&page_size=20
```

- `page`: entero ≥ 1, default 1.
- `page_size`: 1–100, default 20.

### 4.2 Respuesta

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "pages": 0,
  "has_next": false
}
```

Aplicable a: equipos, miembros, proyectos, tareas, comentarios, adjuntos, notificaciones y actividad.

> `tasks` ya usa este envelope; el resto se alinea en P3.

---

## 5. Filtros, orden y búsqueda

### Tareas

| Parámetro | Valores | Default |
|---|---|---|
| `status` | `todo`, `in_progress`, `done` | — |
| `priority` | `low`, `medium`, `high` | — |
| `assigned_to` | user id | — |
| `due_before` | ISO 8601 | — |
| `due_after` | ISO 8601 | — |
| `q` | texto (título/descripción) | — |
| `sort_by` | `created_at`, `title`, `priority`, `due_date`, `position` | `created_at` |
| `order` | `asc`, `desc` | `desc` |

### Proyectos

| Parámetro | Valores | Default |
|---|---|---|
| `status` | `active`, `archived` | — |
| `include_archived` | `true`/`false` | `false` |
| `q` | texto | — |

### Notificaciones

| Parámetro | Valores | Default |
|---|---|---|
| `is_read` | `true`/`false` | — |

### Búsqueda de equipo

- `q` obligatorio, mínimo 2 caracteres.
- Busca nombre de proyecto y título de tarea; opcionalmente descripción.
- Escapa `%` y `_` de `LIKE`.
- Devuelve proyectos y tareas paginados.

---

## 6. Rate limits

| Endpoint | Límite | Ventana |
|---|---|---|
| `POST /auth/register` | 5 | 1 minuto/IP |
| `POST /auth/login` | 10 | 1 minuto/IP |
| `POST /auth/refresh` | 30 | 1 minuto/IP |
| Uploads | 20 | 1 minuto/usuario |
| Resto | 300 | 1 minuto/IP |

Respuesta `429`:

```http
Retry-After: 60
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1762704000
```

---

## 7. Catálogo de endpoints

Leyenda de permisos: **Público**, **Auth** (cualquier autenticado), **Member**, **Admin**, **Owner**, **Creator**.

### 7.1 Auth

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `/auth/register` | Público | `{email, password}` | `UserOut` | 201, 409, 422, 429 |
| POST | `/auth/login` | Público | form `username,password` | `Token` | 200, 401, 423, 429 |
| POST | `/auth/refresh` | Público (refresh) | `{refresh_token}` | `Token` | 200, 401, 429 |
| POST | `/auth/logout` | Auth | `{refresh_token}` | — | 204, 401 |

### 7.2 Users

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `/users/me` | Auth | — | `UserOut` | 200, 401 |
| PUT | `/users/me` | Owner | `{email?, password?, current_password?}` | `UserOut` | 200, 401, 409, 422 |

> Target: `current_password` obligatorio para cambiar contraseña/email; al cambiar contraseña se revocan sesiones.

### 7.3 Teams

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `/teams/` | Auth | `{name, description?, slug?}` | `TeamOut` | 201, 409, 422 |
| GET | `/teams/` | Auth | `page,page_size` | `Paginated<TeamOut>` | 200 |
| GET | `/teams/{team}` | Member | — | `TeamOut` | 200, 403, 404 |
| PATCH | `/teams/{team}` | Admin | `{name?,description?}` | `TeamOut` | 200, 400, 403, 404 |
| GET | `/teams/{team}/search` | Member | `q,page,page_size` | `{projects,tasks}` | 200, 422 |
| POST | `/teams/{team}/members` | Admin | `{email, role}` | `TeamMemberOut` | 201, 404, 409 |
| GET | `/teams/{team}/members` | Member | `page,page_size` | `Paginated<TeamMemberOut>` | 200, 403 |
| PATCH | `/teams/{team}/members/{user_id}` | Admin | `{role}` | `TeamMemberOut` | 200, 403, 404, 409 |
| DELETE | `/teams/{team}/members/{user_id}` | Admin o self | — | — | 204, 403, 409 |

**Target (P3):**

| Método | Ruta | Permiso | Nota |
|---|---|---|---|
| PATCH | `/teams/{team}` | Admin | Editar nombre/descripción |
| POST | `/teams/{team}/archive` | Admin | Archivar equipo |
| POST | `/teams/{team}/leave` | Member | Salir, salvo último admin |

### 7.4 Projects

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `/teams/{team}/projects/` | Member | `{name, description?}` | `ProjectOut` | 201, 422 |
| GET | `/teams/{team}/projects/` | Member | `status,include_archived,page,page_size` | `Paginated<ProjectOut>` | 200 |
| GET | `/teams/{team}/projects/{project}` | Member | — | `ProjectOut` | 200, 404 |
| PATCH | `/teams/{team}/projects/{project}` | Admin | `{name?,description?,status?}` | `ProjectOut` | 200, 403, 404 |
| DELETE | `/teams/{team}/projects/{project}` | Admin | — | — | 204, 403 |
| POST | `/teams/{team}/projects/{project}/archive` | Admin | — | `ProjectOut` | 200, 403, 404 |
| POST | `/teams/{team}/projects/{project}/restore` | Admin | — | `ProjectOut` | 200, 403, 404 |
| GET | `/teams/{team}/projects/{project}/activity` | Member | `page,page_size` | `Paginated<ActivityLogOut>` | 200, 403 |

**Semántica actual:** `DELETE` **archiva** (`status=archived`).

**Target (P3):**

| Método | Ruta | Permiso | Nota |
|---|---|---|---|
| POST | `/teams/{team}/projects/{project}/archive` | Admin | Archivado explícito |
| POST | `/teams/{team}/projects/{project}/restore` | Admin | Restaurar |
| DELETE | `/teams/{team}/projects/{project}?hard=true` | Admin | Borrado definitivo (Could) |

`DELETE` sin `hard=true` queda como alias deprecado de archive hasta v2.

### 7.5 Tasks

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `/teams/{team}/projects/{project}/tasks/` | Member | `{title,description?,priority?,due_date?,assigned_to?}` | `TaskOut` | 201, 400, 422 |
| GET | `/teams/{team}/projects/{project}/tasks/` | Member | filtros + paginación | `Paginated<TaskOut>` | 200 |
| GET | `/teams/{team}/projects/{project}/tasks/{task}` | Member | — | `TaskOut` | 200, 404 |
| PATCH | `/teams/{team}/projects/{project}/tasks/{task}` | Creator/Admin (todos los campos); Member (solo status) | `{title?,description?,status?,priority?,due_date?}` | `TaskOut` | 200, 403, 404, 422 |
| DELETE | `/teams/{team}/projects/{project}/tasks/{task}` | Creator/Admin | — | — | 204, 403, 404 |
| PATCH | `/teams/{team}/projects/{project}/tasks/{task}/assign` | Admin/Creator | `{user_id}` | `TaskOut` | 200, 400, 403, 404 |
| GET | `/teams/{team}/projects/{project}/tasks/{task}/activity` | Member | `page,page_size` | `Paginated<ActivityLogOut>` | 200, 403 |

**Target (P3):**

| Método | Ruta | Permiso | Nota |
|---|---|---|---|
| PATCH | `.../tasks/{task}/status` | Member | Solo `status` (+ `position` si Kanban) |
| PATCH | `.../tasks/{task}` | Creator/Admin | Resto de campos |

`assigned_to` en creación y `user_id` en assign deben ser miembros del equipo. El payload de assign es `{user_id}` (no `{assigned_to}`).

### 7.6 Comments

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `.../tasks/{task}/comments/` | Member | `{content}` | `CommentOut` | 201, 422 |
| GET | `.../tasks/{task}/comments/` | Member | `page,page_size` | `Paginated<CommentOut>` | 200 |
| PATCH | `.../tasks/{task}/comments/{comment}` | Author (miembro) | `{content}` | `CommentOut` | 200, 403, 404 |
| DELETE | `.../tasks/{task}/comments/{comment}` | Author/Admin | — | — | 204, 403, 404 |

### 7.7 Attachments

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| POST | `.../tasks/{task}/attachments/` | Member | `multipart file` | `AttachmentOut` | 201, 413, 415 |
| GET | `.../tasks/{task}/attachments/` | Member | `page,page_size` | `Paginated<AttachmentOut>` | 200 |
| GET | `.../tasks/{task}/attachments/{id}/download` | Member | — | binario | 200, 404 |
| DELETE | `.../tasks/{task}/attachments/{id}` | Uploader/Admin | — | — | 204, 403, 404 |

`AttachmentOut` **no** incluye `file_path` ni `storage_key`. Incluye: `id`, `task_id`, `uploaded_by`, `filename`, `file_size`, `mime_type`, `checksum`, `created_at`.

### 7.8 Notifications

| Método | Ruta | Permiso | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `/notifications/` | Owner | `is_read,page,page_size` | `Paginated<NotificationOut>` | 200 |
| GET | `/notifications/unread-count` | Owner | — | `{count}` | 200 |

| PATCH | `/notifications/{id}/read` | Owner | — | `NotificationOut` | 200, 403, 404 |
| PATCH | `/notifications/read-all` | Owner | — | — | 204 |
| GET | `/notifications/stream` | Owner | — | `text/event-stream` | 200 (P4) |

### 7.9 Sistema

| Método | Ruta | Permiso | Response |
|---|---|---|---|
| GET | `/` | Público | `{message}` |
| GET | `/health` | Público | `{status,database,redis,disk}` 200/503 |
| GET | `/health/live` | Público | `{status}` 200 |
| GET | `/health/ready` | Público | `{status,checks}` 200/503 |

---

## 8. Schemas principales

### `UserOut`

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-11-09T14:30:00Z"
}
```

### `Token`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### `TeamOut`

```json
{
  "id": 1,
  "name": "Product",
  "slug": "product",
  "description": "Equipo de producto",
  "created_by": 1,
  "created_at": "2026-11-09T14:30:00Z"
}
```

### `ProjectOut`

```json
{
  "id": 10,
  "team_id": 1,
  "name": "Website",
  "slug": "website",
  "description": "Rediseño",
  "status": "active",
  "created_by": 1,
  "created_at": "2026-11-09T14:30:00Z"
}
```

### `TaskOut`

```json
{
  "id": 100,
  "project_id": 10,
  "title": "Fix login",
  "description": "El refresh falla",
  "status": "todo",
  "priority": "high",
  "position": 0,
  "assigned_to": 2,
  "assignee": { "id": 2, "email": "dev@example.com" },
  "due_date": "2026-11-15T00:00:00Z",
  "created_by": 1,
  "created_at": "2026-11-09T14:30:00Z",
  "updated_at": "2026-11-09T14:30:00Z"
}
```

### `AttachmentOut`

```json
{
  "id": 5,
  "task_id": 100,
  "uploaded_by": 1,
  "filename": "captura.png",
  "file_size": 102400,
  "mime_type": "image/png",
  "checksum": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "created_at": "2026-11-09T14:30:00Z"
}
```

### `NotificationOut`

```json
{
  "id": 7,
  "user_id": 2,
  "type": "assigned",
  "entity_type": "task",
  "entity_id": 100,
  "message": "You have been assigned to task: Fix login",
  "is_read": false,
  "read_at": null,
  "created_at": "2026-11-09T14:30:00Z"
}
```

### `ActivityLogOut`

```json
{
  "id": 20,
  "entity_type": "task",
  "entity_id": 100,
  "action": "updated_status",
  "changed_by": 1,
  "actor": { "id": 1, "email": "user@example.com" },
  "old_value": "todo",
  "new_value": "in_progress",
  "metadata": { "field": "status" },
  "created_at": "2026-11-09T14:30:00Z"
}
```

---

## 9. Deprecaciones y cambios de contrato

| Elemento | Estado actual | Target | Estrategia |
|---|---|---|---|
| Refresh body | Backend espera query; frontend envía body | Body JSON | Corregir backend; aceptar query con warning temporal |
| Logout | Solo revoca access | Revoca ambos | Añadir refresh en body; frontend actualizado |
| `DELETE /projects` | Archiva | Archive explícito + restore | Mantener alias; añadir endpoints; docs |
| Lookup por nombre/título | Soportado | id/slug | Warning + deprecación; retirar en v2 |
| `AttachmentOut.file_path` | Expuesto | Eliminado | Quitar en P1; frontend no lo usa |
| `detail` en errores | Usado | `error` envelope | Periodo de transición con ambos; retirar |
| `is_read` | Boolean | `read_at` | Mantener ambos temporalmente |
| `assigned_to` en assign | Frontend lo envía | `user_id` | Corregir frontend; backend solo `user_id` |
| `ThemeContext` | Código muerto | Eliminado o implementado | ADR-006 |
| `CursorPaginatedResponse` | Sin uso | Eliminar o implementar | Decidir en P3 |

---

## 10. Gobernanza de OpenAPI

1. `app/main.py` debe declarar `title`, `version`, `description` y tags coherentes.
2. Todo endpoint tiene `response_model`, `status_code`, summary y description.
3. Se versiona `openapi.json` en `contracts/openapi.json`.
4. CI compara el snapshot; un diff inesperado falla el build.
5. Los ejemplos de request/response se mantienen en este documento y en los schemas.
6. Los cambios de contrato se anuncian en el PR y en `CHANGELOG.md` (crear en P0/P6).

---

## 11. Checklist por endpoint

Antes de considerar un endpoint terminado:

- [ ] Método, ruta y permisos documentados aquí.
- [ ] `response_model` y status codes correctos.
- [ ] Validación de entrada con límites (longitud, enums, fechas).
- [ ] Verificación de pertenencia al equipo.
- [ ] Verificación de rol/ownership.
- [ ] Error envelope consistente.
- [ ] Paginación si devuelve lista.
- [ ] Test 401, 403, 404, 422 y camino feliz.
- [ ] Rate limit si es costoso o sensible.
- [ ] OpenAPI actualizado y snapshot revisado.
- [ ] Sin datos sensibles en response ni logs.
