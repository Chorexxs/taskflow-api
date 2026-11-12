# Backlog de ejecución — TaskFlow

**Versión:** 1.0
**Fuente:** [`spec.md`](./spec.md), [`plan.md`](./plan.md), [`baseline.md`](./baseline.md)
**Convención:** una tarea = un PR pequeño y revisable. Si una tarea no cabe en un PR, se divide.

**Tamaño:** XS < 2 h · S ≈ 0.5 día · M ≈ 1 día · L ≈ 2–3 días.

**Definition of Ready:** tarea con FR/BL asignado, criterio de aceptación claro, dependencias resueltas y decisión técnica tomada.

**Definition of Done:** ver `constitution.md`. Como mínimo: tests, lint, tipos, build, doc/contrato actualizado y PR con referencia `T-###`.

---

## Estado de ejecución

**Completadas (P1):** `T-011`, `T-012`, `T-013`, `T-014`, `T-015`, `T-016`, `T-017`, `T-018`, `T-019`, `T-020`, `T-021`, `T-022`, `T-023`, `T-024`.

**Completadas (P2):** `T-026` (alternativa registrada: Bearer + auto-refresh; cookies `httpOnly` a P7), `T-025` (auto-refresh proactivo con single-flight entre pestañas), `T-027` (política de contraseñas), `T-028` (cambio de contraseña con verificación y revocación global de sesiones), `T-029` (limpieza de tokens expirados al arrancar), `T-030` (limiter compartido con storage Redis y fallback en memoria), `T-031` (límites en auth/uploads/búsqueda y `429` con `Retry-After`), `T-032` (CSP, Referrer-Policy y Permissions-Policy), `T-033` (auditoría de auth con `user_id` y sin PII), `T-034` (detección de reutilización de refresh con revocación de sesiones), `T-035` (checklist ASVS L2 en `security-checklist.md`).

**Completadas (P3):** `T-036` (lookup por id/slug con nombre/título deprecados), `T-037` (slug único por equipo en proyectos y migración), `T-038` (paginación uniforme en equipos, miembros, proyectos y adjuntos), `T-039` (envelope de errores con `detail` compatible), `T-041` (edición de equipo), `T-042` (desasignación de tareas al expulsar), `T-044` (borrado de tarea con limpieza de adjuntos), `T-045` (endpoint atómico de estado Kanban), `T-046` (archivar/restaurar proyecto), `T-082` (CHECK de enums, auditoría e índices de lectura), `T-047` (actividad con actor y paginación), `T-048` (comentarios paginados y pertenencia al equipo), `T-049` (búsqueda con escape, descripciones y paginación), `T-043` (matriz de permisos cubierta con tests 401/403/404 por endpoint).

**Parcial (P4):** ninguno.

**Completadas (P4, colaboración):** `T-050` (orden asc/desc de comentarios), `T-051` (pertenencia actual al equipo al editar comentarios), `T-052` (menciones).

**Completadas (P6):** `T-072` (dependencias backend fijadas + React Router parcheado), `T-073` (Python 3.12), `T-074` (ruff y mypy fijados y ejecutados en CI), `T-075` (Docker non-root + HEALTHCHECK), `T-076` (CI frontend con lint/build y umbrales de cobertura: 80 % backend, 70 % frontend), `T-077` (tests de integración sobre PostgreSQL con esquema Alembic y truncado por test), `T-078` (snapshot OpenAPI + check en CI), `T-079` (health live/ready), `T-080` (release checklist, `smoke_release.py` 15/15, `smoke_performance.py` y verificación post-deploy).

**Completadas (P5):** `T-066` (auditoría WCAG de flujos críticos en `a11y-audit.md`, skip link y nombres accesibles), `T-063` (cliente API con refresh single-flight, retry en 401, errores tipados y AbortController), `T-064` (AuthContext endurecido: permisos visuales desde `user`, sin `user_id` en storage), `T-067` (cabeceras y buscadores responsive; tablero usable desde 360 px), `T-071` (acciones de admin ocultas en tablero y miembros), `T-069` (tests de flujos críticos con MSW: login, tablero, tarea, comentarios y notificaciones), `T-068` (estados de error consistentes con reintento en dashboard, equipo, tablero y tarea), `T-065` (decisión dark-only), `T-070` (eliminados axios y ThemeContext muerto).

**Completadas (P4):** `T-053` (backend de almacenamiento configurable), `T-054` (object storage en InsForge + backfill de adjuntos), `T-055` (MIME/tamaño, checksum SHA-256 y nombres únicos), `T-056` (limpieza de adjuntos locales y de objetos al borrar tarea).

**Completadas (P4):** `T-057` (notificaciones paginadas y contador de no leídas), `T-058` (deduplicación por evento y preferencias de tipo silenciado), `T-059` (SSE autenticado con heartbeat y `Last-Event-ID`), `T-060` (cliente SSE con fallback a polling), `T-061` (activity con actor, etiquetas legibles y paginación en UI), `T-062` (búsqueda con debounce 300 ms y paginación del tablero).

**Completadas (P8, auditoría 2026-11-10):** `T-083` (refresh rechaza el token en query string), `T-084` (fail-fast de `SECRET_KEY` fuera de development/test), `T-085` (CI con permisos mínimos y acciones fijadas por SHA), `T-086` (`/docs`, `/redoc` y `/openapi.json` deshabilitados en producción), `T-087` (gitleaks en pre-commit y CI), `T-088` (pip-audit en CI), `T-089` (dependencias con CVE actualizadas: `python-multipart`, `pytest`, `pydantic-settings`), `T-090` (migración de `python-jose` a `PyJWT`), `T-091` (host de InsForge redactado en documentación), `T-092` (los 422 no reflejan el valor enviado).

**Completadas (P9, smoke de release 2026-11-10):** `T-093` (rate limit rompía las respuestas 2xx de los endpoints limitados), `T-094` (`/health` no bloquea si Redis no está configurado o no responde).

**Completada (P7):** `T-081` (SSE endurecido: Redis pub/sub con fallback en proceso, límites de conexión, sesiones DB cortas, heartbeats, reconciliación, backoff y prueba de carga 500/500).

**Completada (P9):** `T-095` (sincronizar InsForge con `alembic upgrade head` antes del deploy; causa raíz de B-05).

**Completada (P10, seguimiento 2026-11-11):** `T-096` (orden estable del Kanban con `tasks.position`, migración `f0e1f2a3b4c5`, `PATCH /status` atómico con `position` y reordenación en el tablero), `T-097` (decisión final de ADR-001: se mantiene Bearer + auto-refresh; cookies de terceros inviables sin BFF y riesgo residual registrado), `T-098` (purga idempotente de notificaciones >90 d y actividad >1 año, al arrancar y con `scripts/purge_retention.py`), `T-099` (drift documental: contratos, checklist y README sin afirmaciones obsoletas), `T-100` (idempotencia en POST críticos con `Idempotency-Key`: replay, 422/409, purga a 24 h y migración `b2c3d4e5f6a7`), `T-101` (bloqueo `FOR UPDATE` del equipo al expulsar o cambiar roles, con test de concurrencia sobre PostgreSQL), `T-102` (drill de backup/restore con `scripts/backup_restore_drill.py` y verificación de tablas, filas y revisión Alembic), `T-103` (rotación de `SECRET_KEY` con clave dual y ADR-012), `T-104` (modelo STRIDE formal en `threat-model.md` con 32 amenazas, mitigaciones y riesgos residuales), `T-105` (labels e identificadores accesibles en todos los formularios del frontend), `T-106` (el cliente SPA envía `Idempotency-Key` y la conserva en el reintento 401), `T-107` (Vite 8 + Vitest 5 con Node 24 y cobertura restaurada con tests de equipo, tablero y tarea), `T-108` (cierre de los hallazgos de la auditoría de seguridad 2026-11-11: imagen Docker sin secretos, Sentry sin PII, body limits, validación de config, health sin fugas, caché de logout y gates de CI), `T-109` (proxy de Render con IP real verificada y validación de magic bytes/ejecutables en uploads), `T-110` (escaneo ClamAV opcional con política fail-closed y rechazo antes de almacenar), `T-111` (smoke de p95 de escritura: crear tarea y cambiar estado), `T-112` (SBOM CycloneDX en CI y digest de `python:3.12-slim`), `T-113` (verificación de email con backend log/SMTP, token de un solo uso y UI).

**Completada (P10, seguimiento 2026-11-12):** `T-114` (el `sslmode` de la suite se deriva de `TEST_DATABASE_URL`/`TEST_DB_SSLMODE` y ya no hereda el del `.env`), `T-115` (eliminados `app/cache.py`, sus invalidaciones no-op y las 11 excepciones que ningún endpoint lanzaba), `T-116` (el bloqueo de cuenta incrementa `token_version` y revoca access y refresh previos), `T-117` (el listado de miembros usa `joinedload` y un test verifica que serializar una página no dispara SELECT extra), `T-118` (`crud.py` ya no importa FastAPI ni depende de auth; eliminadas cuatro funciones sin consumidores), `T-119` (la búsqueda carga el asignado con `joinedload` y la paginación se unifica en `paginate_query`), `T-120` (los siete modales comparten `useDialogA11y`: foco inicial, trampa de `Tab`, cierre con `Escape` y restauración de foco), `T-121` (`PORT`, `FORWARDED_ALLOW_IPS`, `TESTING` y `health_redis_url` viven en `settings`; tests nuevos de 404 de adjuntos y de liberación del limitador SSE), `T-122` (`tokenStorage` es la única fuente de tokens; páginas y contexto leen del cliente/contexto y no de `localStorage`).

**Completadas parcialmente (P0):** `T-001` (specs en `specs/taskflow/`), `T-002` (README/AGENTS/STACK/DECISIONS), `T-005` (LICENSE), `T-006` (71 tests backend + 6 frontend), `T-008` (inventario en la spec).

**Completada (P0):** `T-007` (pre-commit con `ruff`, `ruff format`, `gitleaks`, eslint y mypy; `pre-commit run --all-files` verde), `T-004` (ADR-001…011 aceptados con responsable y desviaciones documentadas), `T-010` (política de ramas, PR, release y rollback en `CONTRIBUTING.md`), `T-009` (entornos local/CI/preview/staging/producción en `environments.md`), `T-003` (6 labels, 10 milestones y 95 issues importados).

**Pendientes de P0:** ninguno.

Verificación actual (2026-11-12, T-114): suite completa sobre PostgreSQL 16 →
**273 passed**, 0 fallos, migraciones aplicadas por Alembic y **90,95 % de
cobertura** (gate 80 %). Con el escape hatch `TEST_USE_SQLITE=1` → 267 passed,
2 fallos de SSE y 4 skips (lock y sslmode requieren PostgreSQL). `npm run test`
→ **81 passed** (74,0 % líneas / 60,93 % ramas / 62,37 % funciones; Vite 8 y
Vitest 5 con Node 24); `npm run lint` → limpio; `npm run build` → correcto;
`npm audit --omit=dev` → 0 vulnerabilidades; migraciones
`upgrade`/`downgrade -1`/`upgrade` reversibles. **Auditoría de seguridad
(2026-11-11):** full, sin SEC-0; SEC-1/SEC-2 corregidos en T-108 (imagen Docker
sin secretos, Sentry sin PII, body limits, config fail-fast, health genérico y
caché de logout). **Proxy (T-109):** verificado en producción que dos
`X-Forwarded-For` distintas tienen buckets independientes (10 peticiones → 429
para una IP; otra IP → 401). **Escritura (T-111):** smoke local contra PostgreSQL
→ p95 23,1 ms al crear tarea y 19,3 ms al cambiar estado (20 muestras, 0 errores).
**Docker (2026-11-11):** `docker build -t taskflow-api:local .`
correcto; imagen no-root (`taskflow`) con `HEALTHCHECK` sobre `/health/live`
(B-04 resuelto). **Producción (2026-11-11):** InsForge migrado a `b2c3d4e5f6a7`
(columna e índice de `position` y tabla `idempotency_keys` verificados, 0
posiciones nulas); smoke de release **15/15**; Render sirve el código del Kanban
(tarea nueva con `position` 1024) y la idempotencia responde con
`Idempotent-Replayed: true` en el reintento. Verificado también en producción:
invitar un admin (201), expulsarlo (204) y bloqueo al intentar salir el último
admin (409). **Restore (T-102):** dump de producción (228 KB) restaurado en
PostgreSQL 16 local y verificado en 22,2 s (12 tablas, 92 filas, revisión
`b2c3d4e5f6a7`). Histórico: `STORAGE_BACKEND=insforge`,
CORS verificado; p95 < 33 ms en lecturas; SSE **500/500**.

---

## P0 — Gobernanza y baseline

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-001 | Mover este paquete a `specs/` y enlazarlo desde `README.md`/`AGENTS.md` | M | — | S | — | `specs/` versionado; README apunta a constitution/spec/plan/tasks |
| T-002 | Reescribir README/AGENTS/STACK/DECISIONS para reflejar Render + InsForge + Vercel | M | T-001 | S | BL-23 | 0 referencias a Railway; comandos y env actualizados |
| T-003 | Crear labels, milestones e issues `T-###` | M | T-001 | S | — | Backlog importado; labels `s0/s1/security/db/frontend/docs` |
| T-004 | Revisar y aceptar ADR-001…011 | M | T-001 | S | — | ADRs con estado `accepted` o `proposed` y responsable |
| T-005 | Añadir `LICENSE` MIT | S | — | XS | BL-27 | Archivo presente y enlazado desde README |
| T-006 | Ejecutar baseline: tests, cobertura, build, migraciones | M | — | S | BL-16, BL-40 | Reporte con fecha y métricas en `baseline.md` |
| T-007 | Añadir pre-commit mínimo (format, eslint, secret scan) | S | — | S | BL-24 | `pre-commit run --all-files` verde; hooks completos en T-074 |
| T-008 | Inventario de endpoints y matriz de permisos verificada | M | T-001 | M | FR-API-01 | Tabla endpoint→permiso revisada contra código |
| T-009 | Definir entorno de preview/staging | S | T-002 | M | NFR-REL-01 | Preview de frontend y API documentado |
| T-010 | Política de ramas, PR, release y rollback | S | T-001 | XS | — | Documento de contribución actualizado |

**Salida P0:** documentación alineada, ADRs decididos, backlog creado y baseline reproducible.

---

## P1 — Correcciones críticas

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-011 | `POST /auth/refresh` acepta JSON body `{refresh_token}` y mantiene compatibilidad temporal | S0 | T-006 | M | BL-01, FR-AUTH-03 | Test body OK; test query deprecado; token no aparece en logs |
| T-012 | Logout revoca access y refresh; frontend envía refresh | S1 | T-011 | S | BL-32, FR-AUTH-04 | Reutilizar refresh tras logout → 401 |
| T-013 | Sanitizar nombre de archivo y bloquear path traversal en upload | S0 | T-006 | M | BL-02, FR-ATT-01 | Test con `../../evil` no escribe fuera de storage |
| T-014 | Límite de tamaño en streaming y allowlist MIME/extensión | S0 | T-013 | M | BL-02, BL-37, FR-ATT-01 | Test 413 sin cargar todo en memoria; MIME no permitido → 415 |
| T-015 | Corregir autorización de `remove_member` y proteger último admin | S1 | T-006 | S | BL-03, BL-14, FR-TEAM-10 | Member no puede expulsar admin; último admin no puede salir |
| T-016 | CORS por allowlist de entorno; eliminar `*` con credenciales | S1 | T-017 | S | BL-04, NFR-SEC-03 | Origen no permitido no recibe CORS; tests de config |
| T-017 | Config fail-fast: eliminar fallback de `SECRET_KEY`; validar env | S1 | T-006 | M | BL-05, NFR-SEC-02 | Producción sin `SECRET_KEY` no arranca; test |
| T-018 | Separar permiso de cambio de estado (Kanban) del resto de campos | S1 | T-006 | M | BL-08, FR-TASK-04 | Member mueve tarea; editar título sigue restringido |
| T-019 | Validar que `assigned_to` al crear tarea sea miembro del equipo | S1 | T-006 | S | BL-09, FR-TASK-01 | Asignar no-miembro → 400 |
| T-020 | Corregir `invalidateQueries` a sintaxis React Query v5 | S1 | T-006 | S | BL-10 | 0 usos de array; mutaciones refrescan caché |
| T-021 | Cliente API: comprobar `r.ok`, error tipado y payload de assign | S1 | T-011 | M | BL-11, FR-API-01 | Errores no se tratan como datos; assign envía `user_id` |
| T-022 | Corregir import de Sentry | S1 | T-006 | XS | BL-17, NFR-OBS-02 | Arranque con `SENTRY_DSN` no falla; error de prueba llega |
| T-023 | Quitar `file_path` de `AttachmentOut` y de la API | S1 | T-013 | S | BL-41, FR-ATT-02 | Respuesta sin rutas internas; tests actualizados |
| T-024 | Eliminar `create_all` en producción y `schema.sql`; Alembic único | S1 | T-006 | M | BL-06, BL-36, ADR-004 | DB nueva se crea con `alembic upgrade head`; CI verifica |

**Salida P1:** S0 = 0; S1 críticos cerrados; deploy de smoke verde.

---

## P2 — Endurecimiento de auth y sesión

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-025 | Auto-refresh en frontend con single-flight y reintento único | M | T-011, T-021 | M | FR-AUTH-05 | Access expirado → refresh → request original reintentada una vez |
| T-026 | Implementar ADR-001: migrar a `refresh_sessions`/`revoked_access_tokens` con hash, cookie `httpOnly` + access en memoria (o registrar alternativa) | M | T-004 | L | FR-AUTH-05, NFR-SEC-07 | Flujo login/refresh/logout con cookies; CSRF/origen verificado; migración M-04 reversible |
| T-027 | Política de contraseñas (8–128, sin control chars) y mensajes claros | M | T-017 | S | FR-AUTH-01, FR-AUTH-07 | Registro/cambio rechazan débiles con 422 |
| T-028 | Cambio de contraseña requiere actual y revoca sesiones | M | T-025 | M | BL-33, FR-AUTH-07 | Token previo deja de funcionar tras cambio |
| T-029 | Job de limpieza de tokens/sesiones expirados | S | T-024 | M | BL-34, FR-AUTH-09 | Job idempotente; métrica de filas; test |
| T-030 | Rate limiter con Redis | M | T-016 | M | BL-15, ADR-010 | Dos instancias comparten límite; test |
| T-031 | Rate limit en auth y endpoints costosos + headers 429 | M | T-030 | S | FR-AUTH-06, FR-API-05 | 429 con `Retry-After`; tests |
| T-032 | CSP, HSTS, `Referrer-Policy` y revisión de headers | M | T-016 | M | NFR-SEC-05 | Escaneo sin hallazgos críticos |
| T-033 | Auditoría de eventos de auth sin PII sensible | S | T-024 | M | FR-AUTH-11 | Login/logout/refresh/bloqueo registrados con `user_id` |
| T-034 | Detección de reutilización de refresh y revocación de familia | S | T-026 | M | FR-AUTH-03 | Reutilización → 401 + familia revocada |
| T-035 | Checklist ASVS L2 y revisión de seguridad de release | M | T-025…T-034 | S | NFR-SEC-01 | Checklist firmada; issues abiertos priorizados |

**Salida P2:** AC-01, AC-02 y AC-08 verdes; checklist de seguridad aprobada.

---

## P3 — Consistencia de API, datos y permisos

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-036 | Lookup por `id`/`slug`; deprecar nombre/título con warning | M | T-024 | M | BL-12, FR-API-04 | Tests de ambigüedad; nombres duplicados no rompen |
| T-037 | Añadir `slug` único por equipo a proyectos + migración/backfill | M | T-036 | M | FR-PROJ-03 | Migración reversible; lookup por slug |
| T-038 | Paginación uniforme en todas las listas | M | T-036 | L | BL-19, FR-API-02 | `{items,total,page,pages,has_next}`; máx. 100 |
| T-039 | Envelope de errores único y mapeo de status | M | T-036 | M | BL-20, ADR-005 | Todos los errores con `code/message/details/request_id` |
| T-040 | Snapshot OpenAPI y check de contrato en CI | M | T-039 | M | FR-API-03 | `openapi.json` versionado; CI falla en diff no revisado |
| T-041 | Editar/archivar equipo + guards de último admin | M | T-015 | M | FR-TEAM-04, FR-TEAM-05 | Admin edita; no puede dejar equipo sin admin |
| T-042 | Expulsión con reasignación/desasignación de tareas | M | T-015 | M | FR-TEAM-10 | Tareas del expulsado quedan sin asignar o reasignadas |
| T-082 | Endurecer esquema: `CHECK` de enums, columnas de auditoría e índices (M-01/M-08) | M | T-024 | M | NFR-REL-04 | Migración reversible; constraints validados con datos existentes |
| T-043 | Matriz de permisos implementada y testeada en todos los endpoints | M | T-036…T-049, T-082 | L | FR-API-04 | Test 401/403/404 por endpoint; 100% cubierto |
| T-044 | Borrado de tarea con cascada de comentarios/adjuntos y limpieza local | M | T-013, T-023 | M | BL-07, FR-TASK-06 | DB sin huérfanos; archivos locales limpiados; storage en T-056 |
| T-045 | Endpoint de cambio de estado (Kanban) separado y atómico | M | T-018 | M | FR-TASK-04, FR-TASK-08 | `PATCH /status`; posición si aplica; tests |
| T-046 | Archivar/restaurar proyecto y semántica explícita de `DELETE` | M | T-036 | M | FR-PROJ-05, FR-PROJ-06 | `DELETE` archiva documentado; `POST /restore` admin |
| T-047 | Actividad: actor, diff legible y paginación | M | T-038 | M | BL-30, FR-ACT-01…03 | Respuesta con email/nombre de campo; paginada |
| T-048 | Comentarios: paginación y pertenencia al equipo en edición | M | T-038 | S | BL-35, FR-COM-01…04 | Ex-miembro no edita; lista paginada |
| T-049 | Búsqueda: escape de comodines, paginación y descripción | M | T-038 | M | BL-29, FR-SRCH-01 | `%`/`_` literales; resultados paginados |

**Salida P3:** contratos y permisos consistentes; 100% endpoints con authz test; migraciones reversibles.

---

## P4 — Colaboración, storage y notificaciones

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-050 | Comentarios: paginación y orden configurable | M | T-048 | S | FR-COM-01 | Lista paginada; orden asc/desc |
| T-051 | Comentarios: validar pertenencia actual al equipo | M | T-048 | S | BL-35, FR-COM-03 | Ex-miembro → 403 |
| T-052 | Menciones `@email` con notificación | C | T-050 | M | FR-COM-05 | Solo miembros mencionables; no auto-notificación |
| T-053 | Abstracción `StorageService` (local/S3) | M | T-024 | M | FR-ATT-05, ADR-003 | Interfaz put/get/delete; fake para tests |
| T-054 | Migrar adjuntos a storage S3-compatible + backfill | M | T-053 | L | BL-07, FR-ATT-05 | Archivos migrados con checksum; rollback documentado |
| T-055 | Validación MIME/extensión, checksum y nombres únicos | M | T-053 | M | BL-37, BL-38, FR-ATT-01 | Duplicados no se sobrescriben; checksum en DB |
| T-056 | Limpieza de huérfanos y borrado en cascada de objetos | M | T-054 | M | FR-ATT-06 | Job de reconciliación; test de borrado |
| T-057 | Notificaciones: paginación, filtro y contador de no leídas | M | T-038 | M | BL-18, FR-NOT-02, FR-NOT-03 | `GET /unread-count`; índice; tests |
| T-058 | Deduplicación y preferencias básicas de notificación | C | T-057 | M | FR-NOT-06 | Sin duplicados por evento; silenciar tipo |
| T-059 | SSE backend para notificaciones | S | T-057 | L | FR-NOT-05, ADR-002 | Endpoint autenticado; heartbeat; reconexión |
| T-060 | Cliente SSE con fallback a polling | S | T-059 | M | FR-NOT-05 | Notificación en < 2 s; fallback funciona |
| T-061 | Mejoras de activity en UI (actor, diff, paginación) | S | T-047 | M | FR-ACT-03 | Panel legible; sin IDs crudos |
| T-062 | Búsqueda en UI con debounce y paginación | S | T-049 | M | FR-SRCH-02 | Debounce 300 ms; no bloquea el tablero |

**Salida P4:** AC-03, AC-06 y AC-07 verdes; storage y notificaciones operativas.

---

## P5 — Modernización frontend

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-063 | Cliente API central con auth, refresh, errores y `AbortController` | M | T-025 | L | FR-UI-11 | Un solo wrapper; 401 reintenta; errores tipados |
| T-064 | Endurecer `AuthContext`: estado derivado, logout limpio, sin confiar en `user_id` | M | T-063 | M | BL-44, FR-UI-01 | Permisos visuales desde API; sesión limpia |
| T-065 | Decidir e implementar tema (oscuro-only o claro/oscuro real) | S | T-004 | M | BL-21, FR-UI-08 | Sin código muerto; contraste AA |
| T-066 | Auditoría y corrección de accesibilidad en flujos críticos | M | T-063 | L | BL-28, FR-UI-09 | Teclado, foco, labels, `aria-label`, modales |
| T-067 | Responsive 360–1440 y tablero usable en móvil | M | T-063 | M | FR-UI-10 | Sin overflow; drag usable o alternativa |
| T-068 | Estados de carga/vacío/error consistentes | M | T-063 | M | FR-UI-11 | Ninguna pantalla en blanco; toasts claros |
| T-069 | Tests frontend de flujos críticos con MSW | M | T-063 | L | NFR-MAINT-02 | Login, refresh, tablero, tarea, comentarios, notificaciones |
| T-070 | Eliminar `axios`, `ThemeContext` muerto y código sin uso | S | T-065 | S | BL-22, BL-21 | Dependencias y archivos limpios |
| T-071 | Pulir dashboard/tablero/notificaciones (UX y permisos visuales) | S | T-063 | M | FR-UI-02, FR-UI-04, FR-UI-07 | Acciones visibles según matriz; sin 403 inesperados |

**Salida P5:** build limpio, tests frontend en CI, auditoría a11y sin bloqueantes.

---

## P6 — Operación y release

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-072 | Fijar dependencias backend/frontend y activar Renovate/Dependabot | M | T-006 | M | NFR-MAINT-04 | Lockfiles; PRs automáticos; build reproducible |
| T-073 | Estandarizar Python 3.12 + `pyproject.toml` + `.python-version` | M | T-072 | M | BL-25 | Docker/CI/local usan 3.12 |
| T-074 | Ruff + mypy + pre-commit | M | T-073 | M | BL-24, NFR-MAINT-03 | `ruff`/`mypy` verdes; hooks instalados |
| T-075 | Docker non-root + HEALTHCHECK + build reproducible | M | T-073 | M | BL-26 | Contenedor no root; healthcheck; smoke |
| T-076 | CI frontend + umbral de cobertura + gates completos | M | T-069 | M | BL-16, NFR-MAINT-01 | Pipeline con lint/tests/build/coverage |
| T-077 | Tests de integración contra PostgreSQL | M | T-024 | L | BL-16, ADR-008 | Suite verde en Postgres; sin SQLite para integración |
| T-078 | Contrato OpenAPI en CI + validación de schemas | M | T-040 | S | FR-API-03 | Diff revisado; schemas válidos |
| T-079 | Runbook de deploy/rollback/migración + health liveness/readiness | M | T-024 | M | NFR-REL-01, NFR-OBS-03 | Runbook probado; endpoints separados |
| T-080 | Release checklist + smoke de performance | M | T-075…T-079 | M | NFR-PERF-01 | Release candidate con checklist firmada |

**Salida P6:** todos los gates verdes; deploy/rollback probados; release listo.

---

## P7 — Tiempo real (opcional)

| ID | Tarea | Prio | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-081 | Endurecer SSE: Redis pub/sub, backoff, límites y carga | C | T-059, T-060 | L | FR-NOT-05, ADR-002 | 500 conexiones simuladas estables; reconexión < 5 s |

---

## P8 — Hallazgos de la auditoría de seguridad (2026-11-10)

Origen: [`specs/audit/security-audit.md`](../audit/security-audit.md), modo `incident`.

| ID | Tarea | Prioridad | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-083 | Refresh: rechazar el token en query string | SEC-3 | T-011 | XS | FR-AUTH-03 | Token en query → 422 y sin rotarlo; body → 200 |
| T-084 | Fail-fast de `SECRET_KEY` fuera de development/test | SEC-3 | T-017 | XS | NFR-SEC-02 | `ENVIRONMENT=staging` sin clave → `RuntimeError`; dev/test conservan fallback |
| T-085 | CI con permisos mínimos y acciones fijadas por SHA | SEC-3 | T-074 | XS | NFR-MAINT-03 | `permissions: contents: read`; 0 acciones sin SHA |
| T-086 | Deshabilitar `/docs`, `/redoc` y `/openapi.json` en producción | SEC-3 | T-032 | XS | NFR-SEC-05, FR-API-03 | 404 en producción; habilitados en dev/test; snapshot intacto |
| T-087 | gitleaks en pre-commit y CI con allowlist documentada | SEC-3 | T-074 | S | SPEC-AUDIT-SEC §13 | Historial limpio; un token real sigue fallando el escaneo |
| T-088 | pip-audit como gate de dependencias | SEC-3 | T-072 | S | NFR-MAINT-04 | `pip-audit -r requirements.txt` sin vulnerabilidades |
| T-089 | Actualizar dependencias con CVE (`python-multipart`, `pytest`, `pydantic-settings`) | SEC-2 | T-072 | XS | NFR-MAINT-04 | Versiones corregidas fijadas; suite verde |
| T-090 | Migrar `python-jose` → `PyJWT` (CVE sin parche y `ecdsa` transitiva) | SEC-1 | T-089 | S | NFR-SEC-07 | 0 CVEs en JWT; refresh, revocación y reutilización verdes |
| T-091 | Redactar el host real de InsForge en documentación | SEC-4 | — | XS | SEC-4.1 | `git grep` del host → 0 ocurrencias |
| T-092 | Los errores 422 no reflejan el valor enviado | SEC-4 | T-039 | XS | FR-API-01, SEC-4.2 | `details` sin `input`; la contraseña no aparece en la respuesta |

---

## P9 — Hallazgos del smoke de release (2026-11-10)

Origen: smoke de performance y verificación de release (T-080). El rate limiting
con `headers_enabled` rompía cualquier respuesta 2xx de un endpoint limitado, y
`/health` bloqueaba hasta 4 s cuando Redis no estaba disponible.

| ID | Tarea | Prioridad | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-093 | Corregir 500 en respuestas 2xx de endpoints con rate limit | S0 | T-031 | XS | FR-AUTH-06, NFR-SEC-04 | Registro/login 2xx con cabeceras `X-RateLimit-*`; test de regresión |
| T-094 | `/health` no debe bloquear si Redis no está configurado o no responde | S1 | T-079 | XS | NFR-PERF-01, NFR-OBS-03 | `/health` < 300 ms sin `REDIS_URL`; timeouts cortos si existe |
| T-095 | Sincronizar migraciones de producción antes del deploy | S0 | T-024 | XS | NFR-REL-04 | `alembic current` = head; registro/login 2xx |

---

## P10 — Seguimiento post-release (2026-11-11)

Origen: revisión de la documentación contra el código tras cerrar P9. Detecta
un requisito funcional sin implementar (FR-TASK-08/M-05), la decisión de
ADR-001 aplazada a un P7 ya cerrado, la retención de datos de Q-08 y drift
documental.

| ID | Tarea | Prioridad | Dep. | Tamaño | Refs | Aceptación |
|---|---|---|---|---|---|---|
| T-096 | Orden estable del Kanban: `tasks.position`, migración M-05, `PATCH /status` con `position` y reordenación en el tablero | S1 | T-045 | M | FR-TASK-08, M-05 | Migración reversible; estado+posición atómicos; lista ordenada por `position`; tests backend y frontend |
| T-097 | Cerrar ADR-001: decisión formal sobre cookies `httpOnly` + CSRF | S1 | T-026 | S | FR-AUTH-05, NFR-SEC-07 | Decisión registrada en ADR/checklist; riesgo residual o migración documentada |
| T-098 | Job de retención de notificaciones (90 d) y actividad (1 año) | S2 | T-029 | S | Q-08, NFR-REL-04 | Purga idempotente y observable; tests; runbook |
| T-099 | Corregir drift documental de contratos y checklist | S3 | — | XS | NFR-MAINT-02 | 0 afirmaciones obsoletas verificables |
| T-100 | Idempotencia en POST críticos con `Idempotency-Key` | S1 | T-039 | M | FR-API-06 | Reintento devuelve la respuesta original; 422/409; purga a 24 h; tests |
| T-101 | Serializar cambios de membresía para proteger al último admin | S2 | T-041, T-042 | S | FR-TEAM-04, FR-TEAM-05 | `FOR UPDATE` sobre el equipo; test en PostgreSQL de bloqueo concurrente |
| T-102 | Drill de backup/restore automatizado y verificado | S2 | T-080 | M | NFR-REL-04 | Dump, restore y comparación de tablas/filas/revisión; evidencia y runbook |
| T-103 | Rotación de `SECRET_KEY` con clave dual | S2 | T-017 | S | NFR-SEC-02, ADR-012 | `SECRET_KEY_PREVIOUS` solo verifica; tokens antiguos válidos durante la ventana; tests y procedimiento |
| T-104 | Modelo STRIDE formal | S2 | T-035 | M | NFR-SEC-01 | Activos, fronteras, amenazas TM-01…TM-32, mitigaciones y riesgos residuales; revisión trimestral |
| T-105 | Asociar labels e identificadores en formularios del frontend | S3 | T-066 | S | FR-UI-09 | 0 avisos de label/id en Chrome; tests con `getByLabelText`; lint/build verdes |
| T-106 | Enviar `Idempotency-Key` desde el cliente SPA | S2 | T-100 | XS | FR-API-06 | Clave por creación, reutilizada en el reintento 401; tests del cliente |
| T-107 | Actualizar Vite 8 + Vitest 5 y restaurar la cobertura | S2 | T-072 | M | NFR-MAINT-01, NFR-MAINT-04 | `npm ci`, tests, lint y build verdes con Node 24; cobertura ≥70 % líneas/sentencias |
| T-108 | Cerrar los hallazgos de la auditoría de seguridad 2026-11-11 | S1 | T-104 | M | NFR-SEC-01…07 | SEC-1/SEC-2 corregidos; `.dockerignore`, Sentry, body limits, config, health, caché y gates de CI |
| T-109 | Verificar el proxy de Render y validar magic bytes en uploads | S2 | T-108 | S | NFR-SEC-05, FR-ATT-01 | Rate limit por IP real verificado; contenido de adjuntos coincide con su extensión y se rechazan ejecutables |
| T-110 | Escaneo antimalware de adjuntos con ClamAV | S2 | T-109 | S | NFR-SEC-05, FR-ATT-01 | ClamAV INSTREAM opcional, fail-closed configurable y archivo infectado rechazado antes de almacenar |
| T-111 | Smoke de performance de escritura | S3 | T-080 | XS | NFR-PERF-01 | Script con p95 de crear/cambiar estado; umbral configurable y ejecución local documentada |
| T-112 | SBOM CycloneDX y digest de la imagen base | S3 | T-108 | XS | NFR-MAINT-04 | SBOM generado y subido en CI; `python:3.12-slim` fijado por digest |
| T-113 | Verificación de email con backend log/SMTP | S2 | T-027 | M | FR-AUTH-10, SEC-ASVS-07 | Token de un solo uso, registro genérico, endpoints verify/resend, migración y UI |
| T-114 | Aislar la configuración TLS de la suite del `.env` de producción | S3 | T-113 | XS | ADR-008, NFR-MAINT-01 | `pytest` verde sin exportar variables aunque `.env` tenga `DB_SSLMODE=require`; el `sslmode` de `TEST_DATABASE_URL` o `TEST_DB_SSLMODE` se respeta |
| T-115 | Eliminar el caché no-op y las excepciones de dominio sin uso | S3 | — | XS | BL-31, constitución art. 9.5 | 0 referencias a `app.cache`/`cache_service`; `app/exceptions.py` solo expone `DomainException`; suite verde y docs sin afirmaciones obsoletas |
| T-116 | Revocar sesiones al bloquear la cuenta | S2 | T-028 | S | FR-AUTH-06, SEC-ASVS-10 | Access y refresh previos al bloqueo → 401; login correcto → 423 durante el bloqueo; al expirar, tokens nuevos válidos; tests de regresión |
| T-117 | Evitar el N+1 del listado de miembros | S1 | — | XS | FR-TEAM-06, NFR-PERF-01, CA-1-01 | `joinedload` en la query paginada; test que exige 0 SELECT extra al serializar una página |
| T-118 | Desacoplar `crud` de FastAPI/auth y borrar código muerto | S3 | — | XS | R3, R7, NFR-MAINT-06, CA-2-01, CA-3-01 | `crud.py` sin `Depends` ni `get_current_user`; 0 funciones sin consumidores; suite verde |
| T-119 | Evitar el N+1 de la búsqueda y unificar la paginación | S2 | — | XS | FR-SRCH-01, NFR-PERF-01, CA-2-05, CA-3-02 | `joinedload` del asignado; 0 SELECT extra al serializar; un solo helper de paginación |
| T-120 | Focus trap y cierre con Escape en los modales | S2 | — | S | FR-UI-09, NFR-A11Y-01, CA-2-08, CA-3-05 | Hook compartido con foco inicial, trampa de Tab, Escape y restauración de foco; tests del hook y de Dashboard |
| T-121 | Centralizar la configuración de runtime y cubrir huecos de test | S2 | — | S | R6, NFR-MAINT-06, CA-2-04, CA-3-03 | `PORT`, `FORWARDED_ALLOW_IPS`, `TESTING` y `health_redis_url` en `settings`; 0 `os.environ` en `main`; tests de 404 de adjuntos y liberación del limitador SSE |
| T-122 | Fuente única de tokens en el frontend | S2 | — | S | NFR-MAINT-01, CA-3-04 | `tokenStorage` centraliza claves, lecturas y escrituras; 0 accesos directos en páginas, contexto o cliente; tests de almacenamiento |

---

## Orden recomendado de ejecución

```text
P0: T-001 → T-002 → T-004 → T-003 → T-005/T-006 → T-007/T-008 → T-009/T-010
P1: T-011 → T-012 → T-013 → T-014 → T-015 → T-016 → T-017 → T-018 → T-019
    → T-020 → T-021 → T-022 → T-023 → T-024
P2: T-025 → T-027 → T-028 → T-029 → T-030 → T-031 → T-032 → T-033 → T-034
    → T-026 → T-035
P3: T-036 → T-037 → T-038 → T-039 → T-040 → T-041 → T-042 → T-082
    → T-044 → T-045 → T-046 → T-047 → T-048 → T-049 → T-043
P4: T-053 → T-054 → T-055 → T-056 → T-057 → T-058 → T-059 → T-060
    → T-050 → T-051 → T-052 → T-061 → T-062
P5: T-063 → T-064 → T-068 → T-066 → T-067 → T-065 → T-069 → T-070 → T-071
P6: T-072 → T-073 → T-074 → T-075 → T-077 → T-076 → T-078 → T-079 → T-080
P7: T-081
```

> Si hay que paralelizar: P1 (seguridad) y P5 (frontend) pueden avanzar en paralelo tras P0, siempre que no toquen los mismos archivos. P3 y P4 comparten DB/storage: coordinarlos.

---

## Riesgos de ejecución por tarea

| Tarea | Riesgo | Mitigación |
|---|---|---|
| T-026 | Cookies rompen CORS/CSRF | Feature flag; mantener Bearer; tests de navegador |
| T-037 | Backfill de slugs duplica | Slugify + sufijo determinista; unique; dry-run |
| T-038 | Cambiar respuesta rompe frontend | Versionar o adaptar cliente en el mismo release |
| T-039 | Envelope rompe clientes | Periodo de transición con `detail` además de `error` |
| T-043 | Tests de permisos incompletos | Matriz como checklist; coverage por endpoint |
| T-054 | Pérdida de archivos | Checksums, copia, verificación, rollback |
| T-059 | SSE bloqueado por proxy | Fallback polling; timeout/heartbeat |
| T-073 | Python 3.12 rompe dependencias | Actualizar en rama; CI matrix 3.11/3.12 temporal |

---

## Métricas de avance

| Fase | Criterio de salida medible |
|---|---|
| P0 | 100% docs alineadas; 0 referencias a Railway; ADRs decididos |
| P1 | 0 S0; S1 críticos cerrados; smoke verde |
| P2 | AC-01/AC-02/AC-08 verdes; checklist ASVS |
| P3 | 100% endpoints con authz test; OpenAPI snapshot; migraciones reversibles |
| P4 | AC-03/AC-06/AC-07 verdes; 0 huérfanos |
| P5 | Tests frontend en CI; a11y sin bloqueantes |
| P6 | Todos los gates verdes; release checklist |
| P7 | SSE estable con 500 conexiones; fallback verificado |
