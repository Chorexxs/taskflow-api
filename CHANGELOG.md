# Changelog

Todas las cambios relevantes del proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado semántico.

## [Unreleased]

### Añadido

- `CONTRIBUTING.md` con política de ramas, PR, release y rollback (T-010).
- `specs/taskflow/environments.md` con local, CI, preview, staging y producción (T-009).
- `specs/taskflow/release-checklist.md`, `scripts/smoke_performance.py` y `scripts/smoke_release.py` (T-080).
- ADRs 002, 003, 006 y 007 aceptados con responsable y desviaciones documentadas (T-004).
- SSE event-driven con Redis pub/sub y fallback en proceso; límites de 500 conexiones/5 por usuario con 503 + `Retry-After`; sesiones DB cortas, reconciliación cada 30 s y backoff exponencial en el cliente (T-081).
- `scripts/sse_load_test.py` para validar 500 conexiones simultáneas.
- `SSE_FALLBACK_POLL_SECONDS`, `SSE_MAX_CONNECTIONS` y `SSE_MAX_CONNECTIONS_PER_USER` configurables.
- Backend `insforge` de `StorageService` con bucket privado `taskflow-attachments`, checksum y backfill de adjuntos (T-054); verificado en producción con subida presignada, confirmación y descarga por CDN.
- `scripts/backfill_attachments_object_storage.py` con modo `--dry-run` y verificación de checksum.
- `scripts/import_github_backlog.py`; 6 labels, 10 milestones y 95 issues importados en GitHub (T-003).
- Orden estable del Kanban: columna `tasks.position`, migración `f0e1f2a3b4c5` con backfill e índice `(project_id, status, position)` (T-096).
- `app/jobs.py` y `scripts/purge_retention.py`: purga idempotente de notificaciones (90 d) y actividad (1 año) (T-098).
- `Idempotency-Key` en POST de equipos, proyectos, tareas, comentarios y adjuntos, con tabla `idempotency_keys` y migración `b2c3d4e5f6a7` (T-100).
- Bloqueo `SELECT … FOR UPDATE` sobre el equipo al expulsar miembros o cambiar roles, para que dos operaciones concurrentes no dejen el equipo sin admin (T-101).
- `scripts/backup_restore_drill.py` y `app/backup.py`: dump con `pg_dump`, restore con `pg_restore` y verificación de tablas, filas y revisión Alembic (T-102).
- Rotación de `SECRET_KEY` sin cortar sesiones: `SECRET_KEY_PREVIOUS` solo verifica durante la ventana de rotación (T-103, ADR-012).
- `specs/taskflow/threat-model.md`: modelo STRIDE con 32 amenazas, mitigaciones y riesgos residuales (T-104).
- Formularios del frontend con `label`/`htmlFor`, `id` y `name`; buscadores y filtros con `aria-label` (T-105).
- El cliente SPA envía `Idempotency-Key` en las creaciones y la reutiliza en el reintento tras un 401 (T-106).
- Build Docker verificado: usuario no-root `taskflow` y `HEALTHCHECK` sobre `/health/live` (B-04 resuelto).
- Frontend actualizado a Vite 8, Vitest 5 y `@vitest/coverage-v8` 5; CI usa Node 24 y la cobertura se restaura con tests de equipo, tablero y tarea (T-107).

- Paquete SDD completo en `specs/taskflow/`: constitución, baseline, spec, plan, tareas, modelo de datos y contrato de API.
- Configuración central en `app/config.py` con validación y fail-fast en producción.
- Tests de regresión para refresh, logout, permisos de equipo, Kanban, asignación y uploads (`tests/test_p1_hardening.py`).
- Tests frontend con Vitest + jsdom y configuración de `vite.config.js`.
- Job de frontend y verificación de migraciones en GitHub Actions.
- `LICENSE` MIT, `.env.example` actualizado y `frontend/.env.example`.
- `CHANGELOG.md`.
- Despliegue Vercel verificado: proyecto `chorexxs-projects/taskflow-api`, root `frontend`, `VITE_API_URL` de producción y repositorio de GitHub conectado.
- Headers de seguridad en `frontend/vercel.json` (CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`) y `.vercelignore` para excluir secretos del upload.

### Cambiado

- B-02 resuelto: `taskflow-api-tau.vercel.app` sirve el build actual contra la API de Render; el deploy por CLI y la integración con Git están verificados.
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
- `DB_SSLMODE` configurable (`prefer` local, `require` InsForge).
- Documentados los bloqueos de despliegue de InsForge/Vercel/Render en `specs/taskflow/blockers.md`.
- Migración offline compatible con PostgreSQL (`alembic upgrade head --sql`).
- Base de datos de InsForge enlazada, migrada a `d4e5f6a7b8c9` y verificada con smoke test real 12/12.
- Preview del frontend desplegado vía InsForge/Vercel en `https://<insforge-project-id>.insforge.site`.
- Render actualizado con la base de InsForge, `DB_SSLMODE=require`, CORS y `STORAGE_BACKEND=database`; deploy live.
- Smoke test de producción 13/13 y CORS verificado para ambos frontends.
- Mejoras de accesibilidad: focus visible, reduced motion, `aria-label` en iconos y roles de diálogo.
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
- `PATCH /tasks/{id}/status` acepta `position` y el tablero permite reordenar dentro de una columna; estado y posición se guardan en la misma transacción (T-096).
- Decisión final de ADR-001: se mantiene Bearer + auto-refresh y se documentan los disparadores para reabrirla (T-097).
- Retención de datos aplicada al arrancar y disponible como script programable (T-098).
- Contratos y checklist sin afirmaciones obsoletas sobre cookies, checksums, paginación y query string (T-099).
- Un reintento con la misma `Idempotency-Key` devuelve la respuesta original con `Idempotent-Replayed: true`; cuerpo distinto → 422 y petición en vuelo → 409 (T-100).
- La purga de retención también elimina claves de idempotencia caducadas (`IDEMPOTENCY_KEY_TTL_HOURS`, 24 h) (T-100).
- Las comprobaciones de último admin se ejecutan bajo un lock de fila del equipo; el test de concurrencia se ejecuta sobre PostgreSQL (T-101).
- `decode_token` acepta la clave anterior (`SECRET_KEY_PREVIOUS`) si la firma con la primaria no coincide, manteniendo la sesión durante la rotación (T-103).

### Corregido

- Producción desincronizada: InsForge estaba en `d4e5f6a7b8c9` y el código esperaba `c9d0e1f2a3b4`; se aplicó `alembic upgrade head` tras un backup y se verificó registro/login (T-095, B-05 resuelto).
- Rate limiting: las respuestas 2xx de endpoints limitados ya no devuelven 500; slowapi recibe `response` e inyecta `X-RateLimit-*` (T-093).
- `/health`: solo consulta Redis si `REDIS_URL` existe y con timeout de 200 ms; sin Redis responde `not_configured` sin bloquear (T-094).

### Eliminado

- `schema.sql` (esquema duplicado y desactualizado).
- Dependencia de `create_all` en producción.
- Código muerto de configuración duplicada en `app/auth.py` y `app/database.py`.

### Pendiente

- Sin tareas funcionales pendientes (P0–P10 cerrados). Queda deuda aceptada en
  `specs/taskflow/security-checklist.md` y bloqueos de entorno en
  `specs/taskflow/blockers.md` (B-04: build Docker local sin daemon).
