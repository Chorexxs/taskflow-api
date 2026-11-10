# Plan técnico — TaskFlow

**Versión:** 1.0
**Deriva de:** [`spec.md`](./spec.md) y [`baseline.md`](./baseline.md)
**Objetivo:** ejecutar la modernización en fases pequeñas, reversibles y verificables.

---

## 1. Principios de implementación

1. **Arreglar primero lo que rompe o expone datos.** P0/P1 antes de features.
2. **Un cambio, una razón.** No mezclar refactor estructural con cambio de comportamiento.
3. **Expand/contract.** Los cambios incompatibles de DB/API se hacen en dos despliegues.
4. **Todo con test.** El test se escribe antes o junto al cambio, nunca después “si hay tiempo”.
5. **La API es la autoridad.** La UI oculta acciones, pero nunca decide permisos.
6. **Observar antes de optimizar.** No se añade cache/realtime sin métrica.
7. **Dejar el sistema desplegable al final de cada fase.**

---

## 2. Arquitectura objetivo

```
┌────────────────────┐        HTTPS/JSON        ┌──────────────────────────┐
│  React SPA         │ ───────────────────────▶ │  FastAPI /api/v1         │
│  Vite + RQ + TW    │ ◀─────────────────────── │  Routers + Services      │
│  (Vercel)          │        SSE (notif.)      │  (Render)                │
└────────────────────┘                          └────────────┬─────────────┘
                                                             │
                        ┌────────────────────────────────────┼────────────────────────────┐
                        │                                    │                            │
                        ▼                                    ▼                            ▼
              ┌──────────────────┐                 ┌──────────────────┐        ┌──────────────────┐
              │ PostgreSQL       │                 │ Redis            │        │ Object Storage   │
              │ InsForge         │                 │ rate limit/cache │        │ S3-compatible    │
              │ Alembic          │                 │ pub/sub (SSE)    │        │ (InsForge)       │
              └──────────────────┘                 └──────────────────┘        └──────────────────┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │ Sentry + logs    │
                                                    │ JSON + requestID │
                                                    └──────────────────┘
```

### Capas

| Capa | Responsabilidad | Regla |
|---|---|---|
| **Routers** | HTTP, validación de entrada, authz de ruta | No lógica de negocio compleja |
| **Services** (nueva) | Casos de uso con múltiples pasos: auth/sesión, invitaciones, borrado con storage, notificaciones | Solo se crea cuando hay >1 paso o transacción |
| **CRUD/Repositories** | Consultas y persistencia | Sin HTTP, sin permisos |
| **Models** | Esquema ORM | Sin lógica de negocio |
| **Schemas** | Contratos Pydantic | Sin acceso a DB |
| **Jobs** (nueva) | Limpieza de tokens, reconciliación de storage, retención | Idempotentes y observables |
| **Config** (nueva) | Settings validados y fail-fast | Única fuente de configuración |

> No se introduce una capa de servicios para todo. Solo para flujos que hoy mezclan permisos, transacciones, storage y notificaciones.

---

## 3. Cambios estructurales propuestos

### 3.1 Configuración unificada

- Crear `app/config.py` con `Settings` (Pydantic Settings) que valide:
  `SECRET_KEY`, `DATABASE_URL`, `ENVIRONMENT`, `CORS_ORIGINS`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
  `REFRESH_TOKEN_EXPIRE_DAYS`, `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`,
  `REDIS_URL`, `SENTRY_DSN`, `STORAGE_*`, `MAX_UPLOAD_SIZE`, `ALLOWED_MIME_TYPES`.
- Eliminar las clases `Settings` duplicadas de `app/auth.py` y `app/database.py`.
- En `ENVIRONMENT=production`, fallar si falta un valor crítico. En `test`, permitir overrides.
- Un solo `.env.example` documentado.

### 3.2 Errores

- `DomainException` con `code`, `message`, `status_code` y `details`.
- Handler único que serializa el envelope de `contracts/api.md`.
- Reemplazar gradualmente los `HTTPException` de routers por excepciones de dominio o helper `api_error`.
- Mantener `detail` solo si se decide compatibilidad temporal; la UI migra al nuevo envelope.

### 3.3 Identificadores

- `teams`: `id` + `slug` (slug generado en servidor).
- `projects`: `id` + `slug` único por equipo (target). Se mantiene lookup por nombre solo como legacy deprecado.
- `tasks`: `id` únicamente. El lookup por título se elimina o se marca deprecado con warning.
- Validar que el recurso pertenece al padre antes de cualquier operación.

### 3.4 Adjuntos

- `storage_service` con interfaz: `put(key, stream)`, `get(key)`, `delete(key)`, `exists(key)`.
- Implementaciones: `LocalStorage` (dev/test) y `S3Storage` (prod, InsForge).
- Metadatos en `attachments`: `storage_key`, `original_filename`, `file_size`, `mime_type`, `checksum`, `uploaded_by`, `task_id`.
- No exponer `storage_key` ni rutas internas en la API.
- Subida en streaming con límite duro y validación de MIME/extensión.
- Borrado de tarea/proyecto dispara limpieza de objetos.
- Job de reconciliación semanal.

### 3.5 Notificaciones

- `notifications` con `read_at`, `dedupe_key` y `type`.
- Endpoint `GET /notifications/unread-count`.
- SSE en `/notifications/stream` con autenticación y reconexión.
- Publicación vía Redis pub/sub para soportar múltiples instancias.
- Fallback: polling cada 30–60 s.

### 3.6 Base de datos

- Alembic como única fuente de esquema en producción.
- `Base.metadata.create_all` solo permitido en tests.
- Constraints `CHECK` para enums (`role`, `status`, `priority`, `token_type`).
- `timestamptz` en todas las fechas; UTC.
- Índices según `data-model.md`.
- Backups y restore probados.

---

## 4. Decisiones de arquitectura (ADRs)

### ADR-001 - Transporte de tokens en el navegador

**Estado:** aceptado con alternativa (2026-11-10). Sustituye la propuesta híbrida.
**Responsable:** responsable del proyecto.

**Contexto:** hoy los tokens viven en `localStorage`, accesibles a cualquier XSS. El refresh ya funciona en body y el cliente lo renueva de forma proactiva con single-flight.

**Opciones:**

| Opción | Pros | Contras |
|---|---|---|
| A. Bearer + localStorage | Simple; compatible con API clients | XSS roba ambos tokens |
| B. Access en memoria + refresh en cookie `httpOnly` | XSS no lee refresh; estándar web | Requiere CORS con credenciales, CSRF y cambios en tests |
| C. Híbrido | API acepta Bearer; navegador usa cookies | Más superficie y documentación |

**Decisión:** **A con endurecimiento**, registrada como alternativa de T-026.
- Se mantiene `Authorization: Bearer` con access de 15 min y refresh rotativo de 7 días.
- El cliente renueva 60 s antes de expirar, con single-flight entre pestañas y reintento único.
- Logout y cambio de contraseña revocan sesiones; la reutilización de refresh revoca todas las sesiones (T-034).
- CSP estricta, `Referrer-Policy`, `Permissions-Policy` y CORS por allowlist reducen el impacto de XSS.
- La migración a cookies `httpOnly` + CSRF se reevalúa en P7. Motivo: el cambio exige coordinación de CORS, CSRF, tests de navegador y logout; no aporta valor suficiente frente al riesgo actual.

**Consecuencias:** el refresh sigue accesible desde JS si hay XSS (riesgo aceptado y documentado en `security-checklist.md`, SEC-ASVS-01). Cualquier cliente programático sigue funcionando sin cookies. No se activa `allow_credentials`.

**Si se bloquea:** mantener A con auto-refresh y registrar el riesgo residual.

---

### ADR-002 — Tiempo real

**Estado:** aceptado (2026-11-10).
**Responsable:** responsable del proyecto.

**Contexto:** “notificaciones en tiempo real” hoy es polling cada 30 s.

**Opciones:** SSE, WebSockets, polling.

**Decisión propuesta:** **SSE** para notificaciones, con polling de respaldo.
- Unidireccional, sobre HTTP, reconexión nativa, menor complejidad que WS.
- Redis pub/sub para fan-out entre instancias.
- Si SSE falla o el proxy lo corta, el cliente vuelve a polling.

**Implementado (T-059/T-060):** endpoint SSE autenticado con heartbeat, `Last-Event-ID` y cliente con fallback a polling. El fan-out con Redis pub/sub, el backoff y las pruebas de carga de conexiones quedan como endurecimiento en T-081 (P7, opcional).

**Consecuencias:** endpoint autenticado, heartbeat, límites de conexiones, tests de reconexión.

---

### ADR-003 — Almacenamiento de adjuntos

**Estado:** aceptado con enmienda (2026-11-10).
**Responsable:** responsable del proyecto.

**Contexto:** Render tiene filesystem efímero; los archivos se pierden en redeploy. Además, `file_path` se expone y hay path traversal.

**Decisión propuesta:** **object storage S3-compatible (InsForge Storage)** en producción; local solo dev/test.
- La DB guarda metadatos y `storage_key`.
- Descarga a través de la API (autorización) o URL firmada de corta duración.
- Validación de MIME/extensión, tamaño y checksum.
- Limpieza de huérfanos.

**Enmienda (T-053/T-054):** se implementó la abstracción `StorageService` (`put`/`get`/`delete`) con dos backends: `local` (solo desarrollo) y `database` (PostgreSQL, `attachments.content`). En producción se usa `STORAGE_BACKEND=database` porque el S3-compatible no estaba disponible (credenciales). La migración a S3 queda como parcial en T-054; al activarse no requiere cambiar la API porque la interfaz ya es la misma.

**Consecuencias:** nueva dependencia/configuración; migración de archivos existentes; tests con storage fake.

---

### ADR-004 — Migraciones

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:** Alembic es la única fuente de esquema en producción.
- Eliminar `create_all` del lifespan fuera de tests.
- Crear migración baseline si la DB actual no coincide.
- CI ejecuta `upgrade head` y `downgrade -1` sobre Postgres limpio.
- Cambios incompatibles con expand/contract y backfill idempotente.
- `schema.sql` se elimina o se regenera automáticamente; no se mantiene a mano.

---

### ADR-005 — Envelope de errores

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:**

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task not found",
    "details": {"task_id": "123"},
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

- Mapeo de códigos a status: `*_NOT_FOUND` → 404, `NOT_A_MEMBER`/`PERMISSION_DENIED` → 403, `EMAIL_ALREADY_REGISTERED`/conflictos → 409, `ACCOUNT_LOCKED` → 423, validación → 422, resto → 400/500.
- El `request_id` coincide con `X-Request-ID`.
- La UI muestra `error.message` y registra `error.code`.

---

### ADR-006 — Tema e idioma

**Estado:** aceptado (2026-11-10).
**Responsable:** responsable del proyecto.

**Contexto:** `ThemeContext` no está montado; la app siempre es oscura. La UI está en inglés y la documentación en español.

**Decisión propuesta:**
- **Tema:** declarar **solo oscuro** en este ciclo y eliminar `ThemeContext`/código muerto; el tema claro se evalúa como feature posterior. Alternativa: implementar tokens claros y toggle, pero implica auditoría de contraste.
- **Idioma:** mantener UI en inglés y documentación en español; centralizar strings si se internacionaliza en el futuro.

**Implementado (T-065/T-070):** la UI es dark-only y se eliminó `ThemeContext` y el código muerto; `axios` se retiró en favor de `fetch`.

**Consecuencias:** menos código muerto; si se quiere tema claro, se añade con una spec propia.

---

### ADR-007 — Invitaciones

**Estado:** aceptado (2026-11-10).
**Responsable:** responsable del proyecto.

**Contexto:** “invitar” hoy requiere que el usuario exista; no hay email.

**Decisión propuesta:** renombrar la feature a **“añadir miembro existente”** y documentarlo. Las invitaciones reales (token + email) quedan como `Could` y requieren proveedor de email y tabla `team_invites`.

**Implementado:** la feature se documenta y nombra como “añadir miembro existente”; no hay invitaciones por email ni tabla `team_invites` en este ciclo.

**Consecuencias:** se corrige la promesa de la UI/docs; no se añade infraestructura de email en este ciclo.

---

### ADR-008 — Base de datos de tests

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:** tests de integración contra **PostgreSQL** (servicio de CI o contenedor). SQLite solo para tests unitarios puros que no dependan de SQL específico.

**Consecuencias:** tests más lentos pero representativos; fixtures con transacciones y rollback.

---

### ADR-009 — Dependencias

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:**
- Backend: versiones fijadas en `requirements.txt` (o `pyproject.toml` + lock). Renovate/Dependabot semanal.
- Frontend: `package-lock.json` commiteado; actualizaciones por PR.
- Python 3.12 en local, CI y Docker.
- Node LTS fijado con `.nvmrc`.

---

### ADR-010 — Rate limiting

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:** slowapi con storage Redis (`RATE_LIMIT_STORAGE_URI`) para consistencia multi-instancia.
- Límites en auth y endpoints costosos.
- Respuesta 429 con `Retry-After`.
- En tests, storage en memoria.

---

### ADR-011 — Lookup de recursos

**Estado:** aceptado.
**Responsable:** responsable del proyecto.

**Decisión:** `id` y `slug` son identificadores; nombres/títulos son datos, no claves.
- `teams`: id o slug.
- `projects`: id o slug único por equipo.
- `tasks`: id.
- Se mantiene compatibilidad temporal con nombre/título, marcada como deprecada y con warning en logs.

---

## 5. Fases de entrega

### P0 — Gobernanza y baseline (1–2 días)

**Objetivo:** dejar la spec como fuente de verdad y preparar el terreno.

**Incluye:**
- Mover este paquete a `specs/` y enlazarlo desde README/AGENTS.
- Crear issues/milestones con IDs `T-###`.
- Aceptar ADR-001…011.
- Añadir `LICENSE`.
- Ejecutar baseline de tests y guardar métricas.
- Configurar labels: `s0`, `s1`, `security`, `frontend`, `db`, `docs`.

**Salida:** docs alineadas; backlog creado; baseline reproducible.

**Riesgo:** burocracia sin código. Mitigación: P0 máximo 2 días.

---

### P1 — Correcciones críticas (3–5 días)

**Objetivo:** eliminar S0 y los S1 de bajo esfuerzo.

**Incluye:** BL-01, BL-02, BL-03, BL-04, BL-05, BL-06, BL-08, BL-09, BL-10, BL-11, BL-14, BL-17, BL-32, BL-36, BL-37, BL-41.

**Salida:**
- Refresh funciona con body y tiene tests.
- Upload no permite traversal ni bypass de tamaño.
- Expulsión de admin corregida.
- CORS/secret fail-fast.
- Kanban y asignación corregidos.
- Invalidaciones de React Query y cliente API corregidos.
- Sentry arranca.

**Riesgo:** tocar auth/upload sin tests. Mitigación: tests de seguridad antes del cambio.

---

### P2 — Endurecimiento de auth y sesión (5–7 días)

**Objetivo:** sesión completa y segura.

**Incluye:**
- Auto-refresh con single-flight y reintento único.
- Logout revoca access + refresh.
- Cambio de contraseña revoca sesiones.
- Política de contraseñas.
- Rate limit Redis.
- Limpieza programada de tokens.
- CSP y headers revisados.
- Auditoría de eventos de auth.
- ADR-001 implementado o decidido.

**Salida:** AC-01, AC-02 y AC-08 pasan; checklist de seguridad firmado.

---

### P3 — Consistencia de API y datos (7–10 días)

**Objetivo:** contratos, permisos y datos coherentes.

**Incluye:**
- Lookup por id/slug; deprecación de nombre/título.
- Paginación uniforme.
- Envelope de errores y status correctos.
- Matriz de permisos implementada y testeada.
- Ciclo de vida de equipos (editar, archivar, último admin).
- Expulsión con reasignación/desasignación.
- Archivado/restauración de proyectos.
- Borrado de tarea con limpieza de adjuntos.
- Comentarios: pertenencia y paginación.
- Actividad con actor, paginación y diff.
- Búsqueda con escape y paginación.

**Salida:** 100% endpoints con tests de autorización; OpenAPI snapshot; migraciones reversibles.

---

### P4 — Colaboración, storage y notificaciones (7–10 días)

**Objetivo:** que los datos y las colaboraciones sean fiables.

**Incluye:**
- Storage S3-compatible y migración de adjuntos.
- Validación MIME/extensión/checksum.
- Borrado y reconciliación de objetos.
- Notificaciones paginadas, contador de no leídas y dedupe.
- Menciones (si se aprueba).
- SSE (si se aprueba) o polling optimizado.
- Mejoras de activity.

**Salida:** AC-03, AC-06 y AC-07 pasan; 0 huérfanos en pruebas.

---

### P5 — Modernización frontend (5–7 días)

**Objetivo:** UX consistente, accesible y testeada.

**Incluye:**
- Cliente API central con auth, refresh, errores y `AbortController`.
- React Query v5 correcto en todas las mutaciones.
- Context de auth endurecido.
- Tema decidido (oscuro-only o ambos).
- A11y: foco, teclado, labels, contraste.
- Responsive 360–1440.
- Estados de carga/vacío/error.
- Tests de flujos críticos con MSW.
- Eliminar axios y código muerto.

**Salida:** auditoría a11y sin bloqueantes; tests frontend en CI; build sin warnings.

---

### P6 — Operación y release (5–7 días)

**Objetivo:** que el sistema sea operable y reproducible.

**Incluye:**
- Python 3.12 + pyproject + ruff + mypy + pre-commit.
- Dependencias fijadas y Renovate.
- Docker non-root + HEALTHCHECK.
- CI: lint, tipos, tests, migraciones, cobertura, frontend, seguridad, contrato.
- Runbook de deploy/rollback/migración.
- Health liveness/readiness.
- Sentry y alertas.
- Smoke test de performance.
- Release checklist.

**Salida:** todos los gates verdes; deploy y rollback probados.

---

### P7 — Tiempo real (opcional, 5 días)

**Objetivo:** notificaciones < 2 s sin polling agresivo.

**Incluye:**
- Endpoint SSE autenticado.
- Redis pub/sub.
- Heartbeat, reconexión y backoff.
- Fallback polling.
- Tests de carga de conexiones.

**Salida:** SSE estable; fallback verificado.

---

## 6. Estrategia de migración de datos

### 6.1 Principios

- **Expand/contract:** primero añadir, luego backfill, luego cambiar lectura, luego eliminar.
- Cada migración tiene `upgrade` y `downgrade`.
- Los backfills son idempotentes y por lotes.
- No se migran datos en el arranque de la app.
- Ventana de mantenimiento solo si es imprescindible.

### 6.2 Migraciones previstas

| Migración | Cambio | Estrategia |
|---|---|---|
| M-01 | Constraints de enums y `updated_at` | Añadir columnas/constraints con defaults; validar datos existentes |
| M-02 | `attachments.storage_key` + checksum | Añadir columnas; backfill desde `file_path`; migrar objetos; luego deprecar `file_path` |
| M-03 | `refresh_sessions` / tokens hasheados | Crear tabla nueva; dual-write temporal; migrar; retirar `revoked_tokens` o mantener para access |
| M-04 | `projects.slug` | Añadir nullable; backfill con slugify + sufijo; unique; hacer NOT NULL |
| M-05 | `tasks.position` | Añadir nullable; backfill por columna/created_at; default |
| M-06 | `notifications.read_at` + índices | Añadir; backfill desde `is_read`; conservar `is_read` temporalmente |
| M-07 | `team_invites` (si se aprueba) | Tabla nueva; sin impacto |
| M-08 | Índices y constraints de actividad | Crear índices; validar |

### 6.3 Rollback

- Toda migración debe poder revertirse sin pérdida de datos nuevos.
- Si el rollback no es posible, se documenta y se requiere backup verificado antes.
- El deploy de API y migración se coordina: migración compatible primero, código después.

---

## 7. Estrategia de testing

### 7.1 Pirámide

| Nivel | Backend | Frontend |
|---|---|---|
| Unitario | Schemas, auth, helpers, crud puro | Componentes, hooks, utils |
| Integración | API + PostgreSQL + storage fake | Páginas con MSW |
| Contrato | OpenAPI snapshot + validación | Tipos/cliente |
| E2E (opcional) | Flujo completo | Playwright |
| Seguridad | Matriz de permisos + uploads + auth | — |
| Performance | k6 smoke | Lighthouse |

### 7.2 Backend

- Fixtures por test con transacción y rollback; PostgreSQL.
- Factories para usuarios, equipos, proyectos, tareas.
- Tests obligatorios por endpoint: 401 sin token, 403 sin permiso, 404 recurso ajeno, 200/201 feliz, 422 validación.
- Tests de refresh: expirado, revocado, reutilizado, tipo incorrecto, usuario bloqueado.
- Tests de upload: traversal, tamaño, MIME, duplicado, borrado.
- Tests de migración: `upgrade head`, `downgrade -1`.
- Cobertura ≥ 80%, con reporte por módulo.

### 7.3 Frontend

- Vitest + Testing Library + MSW.
- Flujos: login, refresh, dashboard, crear equipo, tablero (drag), detalle de tarea, comentarios, adjuntos, notificaciones, perfil.
- Tests de accesibilidad básicos (roles, labels, foco).
- Build de producción en CI.

### 7.4 Datos de prueba

- Sin datos reales.
- Semillas deterministas.
- Limpieza entre tests.

---

## 8. CI/CD

### Pipeline

```yaml
stages:
  - lint
  - typecheck
  - test-backend
  - test-frontend
  - migrations
  - security
  - contract
  - build
  - deploy
  - smoke
```

| Stage | Comando | Gate |
|---|---|---|
| Lint backend | `ruff check` + `ruff format --check` | 0 errores |
| Tipos | `mypy app` | 0 errores |
| Tests backend | `pytest --cov=app --cov-fail-under=80` | verde |
| Tests frontend | `npm run test` | verde |
| Build frontend | `npm run build` | sin errores |
| Migraciones | `alembic upgrade head` + `downgrade -1` | verde |
| Seguridad | `pip-audit`, `npm audit`, `gitleaks` | 0 críticos |
| Contrato | comparar `openapi.json` | diff revisado |
| Deploy | Render/Vercel | solo `main` |
| Smoke | `/health`, login, crear/borrar tarea de prueba | verde |

### Entornos

| Entorno | Backend | Frontend | DB |
|---|---|---|---|
| Local | Uvicorn + Docker | Vite | Postgres Docker |
| CI | No aplica | Build de Vite | Postgres efímero del runner |
| Preview | API de producción (compartida) | Vercel preview | InsForge de producción |
| Staging | No aprovisionado (ver `environments.md`) | — | — |
| Producción | Render | Vercel | InsForge |

> Si no hay preview de DB, los tests de integración usan Postgres efímero en CI.
> El detalle, las URLs y las reglas de uso están en
> [`environments.md`](./environments.md).

---

## 9. Observabilidad

- **Logs:** structlog JSON, `request_id`, usuario (`user_id`, nunca email completo), ruta, status, duración.
- **Sentry:** errores 5xx y excepciones de dominio inesperadas; release y entorno.
- **Health:** `/health/live` (proceso) y `/health/ready` (DB, Redis, storage).
- **Métricas:** latencia p50/p95, tasa 5xx, logins fallidos, refresh fallidos, uploads fallidos, tamaño de colas/jobs.
- **Alertas:** 5xx > 1% durante 5 min; readiness fallando; errores de migración; storage lleno.
- **SLOs:** 99.5% disponibilidad; p95 < 300 ms lecturas; p95 < 500 ms escrituras.

---

## 10. Seguridad operativa

- Rotación de `SECRET_KEY` documentada (invalida sesiones; coordinar).
- Gestión de secretos en Render/Vercel, nunca en repo.
- CORS por entorno (`CORS_ORIGINS`).
- CSP compatible con Vite/Vercel; revisar `connect-src` para API y SSE.
- Cookies: `Secure`, `HttpOnly`, `SameSite=Lax`, dominio correcto.
- Rate limits y bloqueo de cuenta monitoreados.
- Dependencias auditadas semanalmente.
- Uploads: allowlist, antivirus opcional, cuarentena opcional.
- Backups: prueba de restore trimestral.

---

## 11. Rollout y rollback

### Rollout

1. Migración compatible (expand) y deploy de API.
2. Deploy de frontend.
3. Activar feature flag si aplica.
4. Smoke test.
5. Monitoreo 30 min.
6. Contract (eliminar legacy) en un release posterior.

### Rollback

- Frontend: redeploy de la versión anterior en Vercel.
- Backend: redeploy de la imagen anterior en Render.
- DB: `alembic downgrade -1` solo si la migración es reversible y no hay datos nuevos dependientes; si no, restaurar backup.
- Feature flag: desactivar sin redeploy.

### Criterios de aborto

- Errores 5xx > 5% en 5 min.
- Login/refresh fallando > 10%.
- Migración bloqueada > 15 min.
- Pérdida de acceso a datos o storage.

---

## 12. Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R-01 | Migración a cookies rompe CORS/CSRF | Media | Alto | Fase separada, tests, fallback Bearer |
| R-02 | Migración de adjuntos pierde archivos | Media | Alto | Backfill verificable, checksums, rollback, mantener originales hasta validar |
| R-03 | Scope creep por “modernizar todo” | Alta | Alto | Fases con salida; fuera de alcance explícito |
| R-04 | InsForge limita storage/conexiones | Baja | Medio | Prueba de carga; plan B S3 |
| R-05 | Render cold starts afectan p95 | Media | Medio | Health, keep-alive, medición separada |
| R-06 | Sin proveedor de email, invitaciones/reset quedan a medias | Media | Medio | ADR-007; renombrar y documentar |
| R-07 | Tests lentos desincentivan ejecución | Media | Medio | Paralelización, fixtures, suite rápida + completa |
| R-08 | Deriva de esquema por `create_all` | Alta | Alto | ADR-004; CI de migraciones |
| R-09 | Regresiones de permisos | Media | Alto | Matriz + tests por endpoint |
| R-10 | Dependencias mayores rompen build | Media | Medio | Actualización incremental, lockfiles, CI |

---

## 13. Trazabilidad spec → plan → tasks

| Área | FR | Fase | Tareas |
|---|---|---|---|
| Auth | FR-AUTH-01…11 | P1, P2 | T-011, T-012, T-015, T-017, T-022, T-025…T-035 |
| Equipos | FR-TEAM-01…11 | P3 | T-036, T-041, T-042, T-043 |
| Proyectos | FR-PROJ-01…08 | P3 | T-037, T-043, T-046 |
| Tareas | FR-TASK-01…09 | P1, P3 | T-018, T-019, T-043, T-044, T-045 |
| Comentarios | FR-COM-01…06 | P3, P4 | T-048, T-050, T-051, T-052 |
| Adjuntos | FR-ATT-01…06 | P1, P4 | T-013, T-014, T-023, T-053…T-056 |
| Notificaciones | FR-NOT-01…06 | P4, P7 | T-057…T-060, T-081 |
| Actividad | FR-ACT-01…03 | P3, P4 | T-047, T-061 |
| Búsqueda | FR-SRCH-01…02 | P3, P4 | T-049, T-062 |
| Frontend | FR-UI-01…12 | P5 | T-063…T-071 |
| API | FR-API-01…07 | P3 | T-036, T-038, T-039, T-040 |
| NFR | NFR-* | P2, P6 | T-025…T-035, T-072…T-080 |
