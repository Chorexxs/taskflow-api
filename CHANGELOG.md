# Changelog

Todas las cambios relevantes del proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado semántico.

## [Unreleased]

### Añadido

- Paquete SDD completo en `specs/taskflow/`: constitución, baseline, spec, plan, tareas, modelo de datos y contrato de API.
- Configuración central en `app/config.py` con validación y fail-fast en producción.
- Tests de regresión para refresh, logout, permisos de equipo, Kanban, asignación y uploads (`tests/test_p1_hardening.py`).
- Tests frontend con Vitest + jsdom y configuración de `vite.config.js`.
- Job de frontend y verificación de migraciones en GitHub Actions.
- `LICENSE` MIT, `.env.example` actualizado y `frontend/.env.example`.
- `CHANGELOG.md`.

### Cambiado

- `POST /auth/refresh` acepta `{"refresh_token": "..."}` en el body y rota el token.
- `POST /auth/logout` revoca access y refresh, y es idempotente.
- Autenticación: comprobación de usuario activo y revocación idempotente.
- Auto-refresh proactivo en el frontend 60 s antes de expirar el access token.
- `AuthContext` expone `refreshToken` y limpia la sesión si el refresh falla.
- Política de contraseñas de 8–128 caracteres y `token_version` para revocar todas las sesiones al cambiar credenciales.
- El cambio de contraseña exige la contraseña actual y obliga a iniciar sesión de nuevo.
- Notificaciones paginadas (`items/total/page/pages/has_next`) y endpoint `/notifications/unread-count`.
- Edición de equipos (nombre/descripción) para admins.
- Endpoints explícitos de archivar/restaurar proyecto y filtro `include_archived`.
- Borrado de tareas con limpieza de archivos adjuntos y auditoría.
- Comentarios paginados y validación de pertenencia al equipo al editar.
- Actividad paginada con datos del actor (`actor.email`).
- Búsqueda de equipo por nombre/título/descripción, con escape de comodines y paginación.
- Búsqueda del frontend con debounce de 300 ms.
- Limpieza de tokens expirados al arrancar (best-effort).
- Endpoints `/health/live` y `/health/ready`.
- Python 3.12 en Docker/CI, `.python-version`, Docker non-root y HEALTHCHECK.
- Snapshot OpenAPI versionado y verificado en CI.
- Eliminados `axios` y el `ThemeContext` muerto; el producto queda declarado como dark-only.
- Adjuntos persistentes en PostgreSQL por defecto (`STORAGE_BACKEND=database`), con backend local para desarrollo.
- Dependencias backend fijadas en `requirements.txt`; React Router actualizado a 7.18.5 (0 vulnerabilidades de producción).
- `pyproject.toml` con configuración de pytest/ruff/mypy.
- Envelope de errores estable (`error.code/message/details/request_id`) manteniendo `detail` para clientes existentes.
- Menciones `@email` en comentarios con notificación solo a miembros del equipo.
- CSP, `Referrer-Policy` y `Permissions-Policy` en todas las respuestas.
- CORS con allowlist (`CORS_ORIGINS`), sin `*` con credenciales.
- Sentry usa la integración correcta y no bloquea el arranque si falla.
- Eliminado `create_all` del arranque; Alembic es la única fuente de esquema.
- Migración de lockout idempotente; `alembic upgrade head` funciona en DB limpia.
- `alembic/env.py` usa `DATABASE_URL` en lugar de `temp.db`.
- Uploads: nombre saneado, clave única, límite en streaming y allowlist de extensiones/MIME.
- `AttachmentOut` ya no expone `file_path`.
- Permisos de equipo: un miembro no puede expulsar a un admin y no se puede dejar el equipo sin admin.
- Tareas: cualquier miembro puede cambiar solo el estado; el creador/admin edita el resto.
- Validación de asignado al crear tarea.
- Cliente API frontend reescrito con errores tipados y `r.ok`; assign envía `user_id`.
- Invalidaciones de React Query migradas a la sintaxis v5.
- Documentación (`README`, `AGENTS`, `STACK`, `DECISIONS`) alineada con el estado real.

### Eliminado

- `schema.sql` (esquema duplicado y desactualizado).
- Dependencia de `create_all` en producción.
- Código muerto de configuración duplicada en `app/auth.py` y `app/database.py`.

### Pendiente

- P2: auto-refresh, cookies/ADR-001, rate limit Redis, limpieza de tokens.
- P3: IDs/slugs, paginación uniforme, envelope de errores, permisos por endpoint.
- P4: object storage, notificaciones SSE.
- P5: accesibilidad, tema y tests de flujos.
- P6: ruff/mypy, lockfiles, Docker non-root, CI completo.
