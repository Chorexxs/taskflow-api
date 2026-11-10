# Especificación — TaskFlow

**Versión:** 1.0 — Draft para revisión
**Estado:** fuente de verdad funcional del ciclo de modernización
**Baseline:** [`baseline.md`](./baseline.md)
**Plan técnico:** [`plan.md`](./plan.md)

---

## 1. Resumen y visión

TaskFlow es una aplicación web para que equipos pequeños y medianos organicen proyectos y tareas en un tablero Kanban colaborativo. El producto debe permitir crear un equipo, invitar a sus miembros, organizar el trabajo en proyectos y tareas, discutir en comentarios, adjuntar archivos y recibir notificaciones, con permisos claros y trazabilidad de cambios.

**Visión de este ciclo:** convertir un prototipo funcional pero frágil en una base mantenible, segura y observable, sin perder las funcionalidades que ya usa la gente.

**Propuesta de valor:**

- Tablero Kanban simple, sin curva de aprendizaje.
- Colaboración por equipos con roles.
- Contexto completo de cada tarea en un solo lugar: asignado, fecha, prioridad, comentarios, adjuntos e historial.
- API REST documentada y versionada.

---

## 2. Personas y roles

| Persona | Descripción | Necesidades principales |
|---|---|---|
| **Miembro** | Persona que pertenece a un equipo y trabaja en tareas | Ver el tablero, crear tareas, moverlas, comentar, adjuntar, recibir notificaciones |
| **Admin de equipo** | Miembro con permisos de gestión | Administrar miembros, proyectos y configuración del equipo |
| **Creador** | Miembro que creó un recurso | Editar/eliminar su recurso según la matriz |
| **Asignado** | Miembro asignado a una tarea | Ver y actualizar el estado de su tarea, recibir notificaciones |
| **Visitante** | Usuario sin sesión | Registrarse e iniciar sesión; no accede a datos |

> No existe un rol global de “superadmin” en este ciclo. La administración de la plataforma es operativa (DB/ops), no una feature de producto.

---

## 3. Objetivos del ciclo

### Objetivos (Must)

1. Eliminar los hallazgos S0/S1 del baseline.
2. Hacer que la autenticación y la sesión funcionen de extremo a extremo, incluido el refresh.
3. Definir y aplicar una matriz de permisos única y testeada.
4. Asegurar integridad de datos: migraciones reproducibles, adjuntos íntegros, borrados coherentes.
5. Alinear documentación, contratos y código.
6. Dejar CI con gates reales (lint, tipos, tests, migraciones, cobertura).
7. Mejorar la experiencia en los flujos críticos: login, tablero, detalle de tarea, notificaciones.

### No objetivos

- Convertir TaskFlow en un producto SaaS multi-tenant con facturación.
- App móvil nativa.
- Chat en tiempo real completo o edición colaborativa tipo Google Docs.
- Integraciones con Slack/GitHub/Jira en este ciclo.
- Rediseño visual completo de la marca.

---

## 4. Alcance

### Dentro del alcance

- Backend: auth, usuarios, equipos, proyectos, tareas, comentarios, adjuntos, notificaciones, actividad, búsqueda.
- Frontend: todas las páginas existentes y sus estados.
- Base de datos: modelo, constraints, índices y migraciones.
- Infraestructura: Docker, CI/CD, variables de entorno, observabilidad.
- Documentación: README, AGENTS, STACK, DECISIONS y este paquete SDD.

### Fuera del alcance (este ciclo)

- Password reset por email, verificación de email y borrado de cuenta (ver §11, Could).
- Facturación, planes y límites por plan.
- Aplicaciones móviles.
- Traducción multi-idioma completa.
- WebSockets bidireccionales; como máximo SSE para notificaciones.

---

## 5. Estado actual

Ver [`baseline.md`](./baseline.md). Resumen: 38 endpoints, 10 tablas, 54 tests backend, 1 test frontend, 2 hallazgos S0, 18 S1, 19 S2 y 6 S3.

---

## 6. Journeys principales

### J-01 — Primer uso

1. El visitante se registra con email y contraseña.
2. Inicia sesión y llega al dashboard vacío.
3. Crea un equipo; el sistema genera un slug único y lo hace admin.
4. Crea un proyecto y una primera tarea.
5. Ve el tablero con la tarea en “To Do”.

### J-02 — Trabajo diario

1. El miembro abre el dashboard y entra a su equipo.
2. Abre el proyecto y ve el Kanban.
3. Arrastra una tarea de “To Do” a “In Progress”.
4. Abre la tarea, comenta y adjunta un archivo.
5. El asignado recibe una notificación.

### J-03 — Administración

1. El admin invita/añade a un miembro.
2. Cambia su rol o lo expulsa.
3. Archiva un proyecto terminado.
4. Revisa la actividad del proyecto.

### J-04 — Sesión

1. El usuario inicia sesión y recibe access + refresh.
2. Al expirar el access, el cliente lo renueva sin interrumpir al usuario.
3. Al cerrar sesión, ambos tokens se invalidan en el servidor.
4. Si la cuenta se bloquea por intentos fallidos, recibe un mensaje claro y un tiempo de espera.

---

## 7. Requisitos funcionales

Prioridad MoSCoW: **M** must, **S** should, **C** could.

### 7.1 Autenticación y usuarios

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-AUTH-01 | Registro con email único y contraseña | M | Email normalizado a minúsculas; contraseña 8–128 caracteres; 201 con `UserOut`; email duplicado → 409; rate limit 5/min/IP |
| FR-AUTH-02 | Login con access + refresh | M | Credenciales válidas → 200 con `access_token`, `refresh_token`, `token_type=bearer`; credenciales inválidas → 401 genérico; cuenta bloqueada → 423; rate limit 10/min/IP |
| FR-AUTH-03 | Refresh con rotación | M | `POST /auth/refresh` acepta `{"refresh_token": "..."}` en body; valida tipo `refresh`, expiración, revocación y usuario activo; revoca el anterior y emite par nuevo; reutilización → 401 y revocación de la familia (S); token en query string → 422 |
| FR-AUTH-04 | Logout real | M | `POST /auth/logout` con access en header y refresh en body; revoca ambos; 204; idempotente |
| FR-AUTH-05 | Sesión automática en el cliente | M | Si el access expira o una request devuelve 401, el cliente refresca una sola vez y reintenta; si falla, limpia sesión y redirige a login |
| FR-AUTH-06 | Bloqueo y rate limiting | M | 5 fallos consecutivos → bloqueo 15 min; contador se resetea al login exitoso; límites respaldados por Redis y consistentes entre instancias |
| FR-AUTH-07 | Cambio de contraseña seguro | M | Requiere contraseña actual; valida política; revoca todas las sesiones; responde 200/204 |
| FR-AUTH-08 | Perfil | M | `GET /users/me` devuelve id, email, is_active, created_at; actualización de email requiere contraseña actual y email único; nunca devuelve hash |
| FR-AUTH-09 | Limpieza de tokens | S | Job programado elimina tokens/sesiones expirados; métrica de filas eliminadas |
| FR-AUTH-10 | Reset de contraseña y verificación de email | C | Requiere proveedor de email; fuera de alcance si no se decide lo contrario |
| FR-AUTH-11 | Auditoría de eventos de auth | S | Login exitoso/fallido, logout, refresh, bloqueo y cambio de contraseña quedan registrados sin PII sensible |

### 7.2 Equipos

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-TEAM-01 | Crear equipo | M | Nombre obligatorio; slug generado en servidor desde el nombre, único, con sufijo si colisiona; creador queda como admin; 201 |
| FR-TEAM-02 | Listar mis equipos | M | Solo equipos donde el usuario es miembro; paginado; incluye rol del usuario y conteo de proyectos |
| FR-TEAM-03 | Ver equipo | M | Por id o slug; solo miembros; 404 si no existe; 403 si no es miembro |
| FR-TEAM-04 | Editar equipo | M | Nombre/descripción; solo admin; slug inmutable o regenerado con confirmación |
| FR-TEAM-05 | Archivar/eliminar equipo | S | Solo admin; confirmación; no se permite si es el último admin; política de datos documentada |
| FR-TEAM-06 | Listar miembros | M | Solo miembros; paginado; incluye `user_id`, email, rol, `joined_at` |
| FR-TEAM-07 | Añadir miembro existente | M | Solo admin; email debe existir; 404 si no existe; 409 si ya es miembro; rol `member` por defecto |
| FR-TEAM-08 | Invitar por email | C | Requiere tabla de invitaciones y proveedor de email; token con expiración; aceptación crea membresía |
| FR-TEAM-09 | Cambiar rol | M | Solo admin; no puede degradar al último admin; roles válidos `admin`/`member` |
| FR-TEAM-10 | Expulsar miembro | M | Admin puede expulsar a cualquiera salvo al último admin; un miembro puede salir por sí mismo salvo si es el último admin; tareas asignadas se desasignan o reasignan |
| FR-TEAM-11 | Buscar en el equipo | M | `q` mínimo 2 caracteres; busca proyectos y tareas; solo miembros; paginado; escapa `%` y `_` |

### 7.3 Proyectos

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-PROJ-01 | Crear proyecto | M | Cualquier miembro; nombre obligatorio; estado `active`; `created_by`; 201 |
| FR-PROJ-02 | Listar proyectos | M | Solo miembros; activos por defecto; `include_archived=true` para incluir archivados; paginado |
| FR-PROJ-03 | Ver proyecto | M | Por id o slug único por equipo; solo miembros |
| FR-PROJ-04 | Editar proyecto | M | Solo admin; nombre/descripción; registra actividad |
| FR-PROJ-05 | Archivar proyecto | M | Solo admin; `status=archived`; las tareas se conservan; se puede restaurar |
| FR-PROJ-06 | Restaurar proyecto | S | Solo admin; `status=active`; registra actividad |
| FR-PROJ-07 | Eliminar proyecto definitivamente | C | Solo admin; confirmación; cascada controlada de tareas/comentarios/adjuntos; borra archivos |
| FR-PROJ-08 | Actividad del proyecto | M | Solo miembros; paginada; incluye actor, acción y diff legible |

### 7.4 Tareas

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-TASK-01 | Crear tarea | M | Cualquier miembro; título obligatorio; prioridad por defecto `medium`; estado `todo`; `assigned_to` debe ser miembro; 201 |
| FR-TASK-02 | Listar tareas | M | Filtros `status`, `priority`, `assigned_to`, `due_before`, `due_after`, `q`; orden configurable; paginación máx. 100; solo tareas del proyecto |
| FR-TASK-03 | Ver tarea | M | Por id (preferente) o título (legacy); solo miembros; 404 si no pertenece al proyecto |
| FR-TASK-04 | Editar tarea | M | Título, descripción, prioridad, fecha y estado; creador o admin para todos los campos; cualquier miembro puede cambiar solo el estado (Kanban); registra diff |
| FR-TASK-05 | Asignar/desasignar | M | Admin o creador; valida membresía; notifica al asignado; `assigned_to=null` desasigna |
| FR-TASK-06 | Eliminar tarea | M | Creador o admin; borra comentarios, adjuntos y archivos; registra actividad; 204 |
| FR-TASK-07 | Actividad de tarea | M | Paginada; actor, acción y diff legible |
| FR-TASK-08 | Orden en el Kanban | S | Cada tarea tiene una posición estable dentro de su columna; mover actualiza estado y posición de forma atómica |
| FR-TASK-09 | Fechas y zonas horarias | M | `due_date` en UTC; se muestra en la zona del navegador; validación de fechas inválidas |

### 7.5 Comentarios

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-COM-01 | Listar comentarios | M | Solo miembros; paginado; orden cronológico configurable |
| FR-COM-02 | Crear comentario | M | Solo miembros; contenido 1–2000 caracteres; notifica al asignado si es otro usuario |
| FR-COM-03 | Editar comentario | M | Solo el autor y solo si sigue siendo miembro; registra `updated_at` |
| FR-COM-04 | Eliminar comentario | M | Autor o admin; 204 |
| FR-COM-05 | Menciones | C | `@email` de miembros; notifica a los mencionados; no permite mencionar a no miembros |
| FR-COM-06 | Historial de edición | C | Opcional; si se implementa, visible para miembros |

### 7.6 Adjuntos

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-ATT-01 | Subir adjunto | M | Solo miembros; máx. 10 MB configurable; allowlist MIME/extensión; nombre saneado; clave única; streaming; checksum |
| FR-ATT-02 | Listar adjuntos | M | Solo miembros; metadatos sin ruta interna; paginado |
| FR-ATT-03 | Descargar adjunto | M | Solo miembros; `Content-Disposition` con nombre original saneado; no expone storage key |
| FR-ATT-04 | Eliminar adjunto | M | Uploader o admin; elimina objeto y metadatos; 204 |
| FR-ATT-05 | Almacenamiento externo | S | Objeto en storage S3-compatible; la DB guarda `storage_key`, tamaño, MIME y checksum |
| FR-ATT-06 | Limpieza de huérfanos | S | Borrar tarea/proyecto elimina objetos; job de reconciliación detecta huérfanos |

### 7.7 Notificaciones

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-NOT-01 | Crear notificaciones | M | Al asignar tarea, comentar tarea asignada y (S) mencionar; no se notifica al actor |
| FR-NOT-02 | Listar notificaciones | M | Solo el propietario; paginado; filtro `is_read`; orden descendente |
| FR-NOT-03 | Contador de no leídas | M | `GET /notifications/unread-count` devuelve `{count}`; eficiente con índice |
| FR-NOT-04 | Marcar leída / todas | M | Solo el propietario; 200/204; idempotente |
| FR-NOT-05 | Tiempo real | S | SSE para notificaciones; si no está disponible, polling cada 30–60 s; reconexión con backoff |
| FR-NOT-06 | Preferencias y deduplicación | C | Evitar duplicados por evento; permitir silenciar tipos |

### 7.8 Actividad y búsqueda

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-ACT-01 | Registrar actividad | M | Entidad, acción, actor, timestamp y diff; inmutable |
| FR-ACT-02 | Consultar actividad | M | Por tarea/proyecto; paginada; solo miembros |
| FR-ACT-03 | Diff legible | S | Nombres de campo y valores legibles; email del actor |
| FR-SRCH-01 | Búsqueda de equipo | M | Proyectos y tareas; nombre/título (S: descripción); paginada; escape de comodines |
| FR-SRCH-02 | Búsqueda en tablero | M | Filtro local por título/descripción; debounce 300 ms; no bloquea el drag & drop |

### 7.9 Frontend y UX

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-UI-01 | Rutas y guards | M | `/login`, `/register`, `/`, `/teams/:team`, `/teams/:team/projects/:project`, `/teams/:team/projects/:project/tasks/:task`, `/profile`, 404; rutas privadas redirigen a login |
| FR-UI-02 | Dashboard | M | Lista equipos con rol y conteo; crear equipo; estados carga/vacío/error |
| FR-UI-03 | Detalle de equipo | M | Proyectos, miembros, búsqueda, invitar, cambiar rol, expulsar, crear/editar proyecto según permisos |
| FR-UI-04 | Tablero Kanban | M | 3 columnas; drag & drop con actualización optimista y rollback si falla; filtros en URL; crear tarea; actividad; editar/archivar proyecto si admin |
| FR-UI-05 | Detalle de tarea | M | Ver/editar según permisos; comentarios; adjuntos; actividad; estados de carga/error |
| FR-UI-06 | Perfil | M | Ver email; cambiar contraseña con confirmación; logout |
| FR-UI-07 | Notificaciones | M | Campana con contador; panel; marcar leída/todas; enlace al recurso |
| FR-UI-08 | Tema | S | O se implementa claro/oscuro real, o se elimina el contexto y se declara solo oscuro; sin código muerto |
| FR-UI-09 | Accesibilidad | M | WCAG 2.1 AA en flujos críticos; teclado; foco; labels; contraste; `aria-label` en iconos |
| FR-UI-10 | Responsive | M | 360 px–1440 px sin overflow horizontal; tablero usable en móvil (scroll horizontal o columnas apiladas) |
| FR-UI-11 | Errores y vacíos | M | Toda query/mutación muestra error comprensible; no hay pantallas en blanco ni botones que fallan en silencio |
| FR-UI-12 | Idioma | S | UI en inglés (actual) o español; decisión única y consistente; fechas/números localizados |

### 7.10 API y contratos

| ID | Requisito | Prio | Criterio de aceptación |
|---|---|---|---|
| FR-API-01 | Error envelope único | M | Todos los errores usan `{error:{code,message,details,request_id}}`; status correcto (400/401/403/404/409/422/423/429/500); `details` de 422 omite el valor enviado (`input`) |
| FR-API-02 | Paginación uniforme | M | Listas devuelven `{items,total,page,pages,has_next}`; parámetros `page`, `page_size` |
| FR-API-03 | OpenAPI como contrato | M | `/openapi.json` generado en desarrollo/test; snapshot en CI; deshabilitado con `/docs` y `/redoc` en producción; cambios revisados |
| FR-API-04 | Semántica HTTP | M | 201 creación, 204 sin contenido, 409 conflicto, 422 validación; `DELETE` documentado |
| FR-API-05 | Rate limit headers | S | `X-RateLimit-*` y `Retry-After` en 429 |
| FR-API-06 | Idempotencia | C | `Idempotency-Key` en POST críticos (subida, creación) |
| FR-API-07 | Deprecación | S | Campos/endpoints legacy marcados y con fecha de retirada |

---

## 8. Matriz de permisos (to-be)

Leyenda: ✅ permitido; ❌ denegado; ◐ condicionado.

| Acción | Admin | Creador | Asignado | Miembro |
|---|---:|---:|---:|---:|
| Ver equipo, proyectos y tareas | ✅ | ✅ | ✅ | ✅ |
| Editar nombre/descripción del equipo | ✅ | ❌ | ❌ | ❌ |
| Archivar/eliminar equipo | ✅ | ❌ | ❌ | ❌ |
| Gestionar miembros y roles | ✅ | ❌ | ❌ | ❌ |
| Crear proyecto | ✅ | ✅ | ✅ | ✅ |
| Editar/archivar/restaurar proyecto | ✅ | ❌ | ❌ | ❌ |
| Crear tarea | ✅ | ✅ | ✅ | ✅ |
| Editar todos los campos de tarea | ✅ | ✅ | ❌ | ❌ |
| Cambiar solo el estado (Kanban) | ✅ | ✅ | ✅ | ✅ |
| Asignar/desasignar tarea | ✅ | ✅ | ❌ | ❌ |
| Eliminar tarea | ✅ | ✅ | ❌ | ❌ |
| Comentar | ✅ | ✅ | ✅ | ✅ |
| Editar comentario | ❌ | ◐ solo propio | ◐ solo propio | ◐ solo propio |
| Eliminar comentario | ✅ | ◐ solo propio | ◐ solo propio | ◐ solo propio |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Eliminar adjunto | ✅ | ◐ solo propio | ◐ solo propio | ◐ solo propio |
| Ver actividad | ✅ | ✅ | ✅ | ✅ |
| Gestionar notificaciones | ◐ propias | ◐ propias | ◐ propias | ◐ propias |
| Editar perfil/contraseña | ◐ propio | ◐ propio | ◐ propio | ◐ propio |

Reglas transversales:

1. Nadie puede dejar un equipo sin admin.
2. Un ex-miembro no conserva acceso a nada, ni siquiera a sus comentarios/adjuntos (puede editar/borrar solo mientras sea miembro).
3. El admin no puede cambiar su propio rol si es el último admin.
4. Las comprobaciones se hacen siempre en el servidor; la UI solo oculta acciones.

---

## 9. Requisitos no funcionales

### Seguridad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-SEC-01 | OWASP ASVS L2 en auth, sesión, control de acceso y validación | Checklist revisada por release |
| NFR-SEC-02 | Sin secretos en repo/logs; fallo al arrancar si faltan variables críticas | Secret scan en CI = 0 hallazgos |
| NFR-SEC-03 | CORS con allowlist por entorno; sin `*` con credenciales | Test de configuración |
| NFR-SEC-04 | Uploads seguros: tamaño, MIME, extensión, nombre, ruta y aislamiento | Tests de path traversal y tamaño |
| NFR-SEC-05 | Headers: CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | Escaneo de headers |
| NFR-SEC-06 | Rate limiting distribuido en auth y endpoints costosos | 429 consistente entre instancias |
| NFR-SEC-07 | Tokens nunca en URL; revocación en logout y cambio de contraseña | Tests de revocación |

### Rendimiento y escalabilidad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-PERF-01 | Lecturas típicas | p95 < 300 ms |
| NFR-PERF-02 | Escrituras típicas | p95 < 500 ms (excluye upload) |
| NFR-PERF-03 | Listas paginadas | Ninguna lista devuelve más de 100 ítems |
| NFR-PERF-04 | Consultas sin N+1 | Revisión + `joinedload` en relaciones usadas |
| NFR-PERF-05 | Índices para filtros/orden | `EXPLAIN` revisado en queries críticas |

### Fiabilidad y datos

| ID | Requisito | Métrica |
|---|---|---|
| NFR-REL-01 | Disponibilidad objetivo | 99.5% mensual |
| NFR-REL-02 | Migraciones reversibles | `upgrade head` + `downgrade -1` en CI |
| NFR-REL-03 | Backup/restore probado | RPO ≤ 24 h, RTO ≤ 4 h |
| NFR-REL-04 | Borrados coherentes | 0 huérfanos en DB/storage tras tests de borrado |
| NFR-REL-05 | Degradación controlada | Sin Redis/storage, la app responde con errores claros |

### Observabilidad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-OBS-01 | Logs JSON con `request_id` | 100% de requests |
| NFR-OBS-02 | Sentry operativo | Error de prueba visible en Sentry |
| NFR-OBS-03 | Liveness/readiness | Endpoints separados y monitoreados |
| NFR-OBS-04 | Métricas básicas | Latencia, errores 5xx, tasa de login fallido |

### Mantenibilidad y calidad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-MAINT-01 | Cobertura backend | ≥ 80% |
| NFR-MAINT-02 | Cobertura frontend crítica | ≥ 70% |
| NFR-MAINT-03 | Lint/tipos/build | 0 errores |
| NFR-MAINT-04 | Dependencias fijadas | Lockfiles + actualización automatizada |
| NFR-MAINT-05 | Documentación viva | 0 referencias a stack/deploy inexistente |
| NFR-MAINT-06 | Complejidad | Sin archivos > 600 líneas sin justificación; sin duplicación de lógica de permisos |

### Accesibilidad y compatibilidad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-A11Y-01 | WCAG 2.1 AA en flujos críticos | Auditoría sin bloqueantes |
| NFR-COMPAT-01 | Navegadores modernos | Últimas 2 versiones de Chrome/Firefox/Safari/Edge |
| NFR-COMPAT-02 | Responsive | 360–1440 px |
| NFR-COMPAT-03 | API v1 compatible | Sin breaking changes sin v2/deprecación |

### Privacidad

| ID | Requisito | Métrica |
|---|---|---|
| NFR-PRIV-01 | Sin PII en logs | Revisión de muestras |
| NFR-PRIV-02 | Retención documentada | Tokens 7 días, notificaciones 90 días, actividad 1 año (propuesta) |
| NFR-PRIV-03 | Acceso mínimo a adjuntos | Solo miembros del equipo |

---

## 10. Criterios de aceptación de flujos críticos

### AC-01 — Refresh de sesión

```gherkin
Dado un usuario con access token expirado y refresh token válido
Cuando el cliente llama a una API protegida
Entonces el cliente llama una sola vez a POST /auth/refresh con el refresh en el body
Y recibe un par nuevo de tokens
Y reintenta la request original con el nuevo access
Y si el refresh falla, limpia la sesión y redirige a /login
```

### AC-02 — Rotación y reutilización

```gherkin
Dado un refresh token ya usado
Cuando se intenta usar de nuevo
Entonces la API responde 401
Y revoca toda la familia de refresh tokens de esa sesión
Y el usuario debe volver a iniciar sesión
```

### AC-03 — Subida segura de adjunto

```gherkin
Dado un miembro autenticado
Cuando sube un archivo de 5 MB con nombre "../../evil.exe" y MIME no permitido
Entonces la API rechaza la extensión/MIME con 415
Y no escribe nada fuera del directorio de storage
Y el nombre se sanea y se genera una clave única
Y si el archivo supera 10 MB, responde 413 sin cargarlo completo en memoria
```

### AC-04 — Permisos de equipo

```gherkin
Dado un equipo con un admin y un member
Cuando el member intenta expulsar al admin
Entonces la API responde 403
Y el admin sigue siendo miembro
Cuando el admin intenta degradarse siendo el último admin
Entonces la API responde 409
```

### AC-05 — Kanban

```gherkin
Dado un member que no creó una tarea
Cuando la arrastra de "To Do" a "In Progress"
Entonces la API acepta el cambio solo de estado
Y la UI actualiza de forma optimista
Y si la API falla, la tarjeta vuelve a su columna original
Y se muestra un toast de error
```

### AC-06 — Notificaciones

```gherkin
Dado un miembro asignado a una tarea
Cuando otro miembro comenta en esa tarea
Entonces se crea una notificación para el asignado
Y el contador de no leídas aumenta
Y al abrir/marcar la notificación, el contador disminuye
Y el autor del comentario no recibe notificación de su propio comentario
```

### AC-07 — Borrado coherente

```gherkin
Dada una tarea con comentarios y adjuntos
Cuando su creador la elimina
Entonces se borran comentarios, metadatos de adjuntos y objetos de storage
Y no quedan filas huérfanas ni archivos huérfanos
Y la actividad registra la eliminación
```

### AC-08 — Migraciones

```gherkin
Dada una base de datos en la última migración
Cuando se ejecuta alembic downgrade -1 y luego upgrade head
Entonces el esquema vuelve al estado esperado
Y los tests de integración pasan
```

---

## 11. Preguntas abiertas y decisiones

| ID | Pregunta | Propuesta | Bloquea |
|---|---|---|---|
| Q-01 | ¿Tokens en localStorage o cookies `httpOnly`? | Mantener Bearer + auto-refresh en P2; evaluar cookies en P3 (ADR-001) | P2 |
| Q-02 | ¿SSE o WebSockets? | SSE solo para notificaciones; resto polling (ADR-002) | P4 |
| Q-03 | ¿Invitaciones reales por email? | Depende de proveedor; si no, renombrar a “añadir miembro” (ADR-007) | P3 |
| Q-04 | ¿Tema claro/oscuro o solo oscuro? | Implementar ambos o eliminar ThemeContext (ADR-006) | P5 |
| Q-05 | ¿Proyectos se archivan o se borran? | Archivar por defecto; borrado definitivo solo admin con confirmación | P3 |
| Q-06 | ¿Proyectos con slug? | Sí, único por equipo; migrar búsquedas por nombre | P3 |
| Q-07 | ¿Orden manual de tareas? | Añadir `position` por columna (FR-TASK-08) | P4 |
| Q-08 | ¿Retención de datos? | Tokens 7 d, notificaciones 90 d, actividad 1 año | P6 |
| Q-09 | ¿Transferencia de propiedad del equipo? | Fuera de alcance; el último admin no puede salir | P3 |
| Q-10 | ¿Reset de contraseña? | Could; requiere email | P6 |

---

## 12. Métricas de éxito

| Métrica | Baseline | Objetivo |
|---|---|---|
| Hallazgos S0 abiertos | 2 | 0 |
| Hallazgos S1 abiertos | 18 | 0 |
| Endpoints con test de autorización | Parcial | 100% |
| Cobertura backend | No medida | ≥ 80% |
| Cobertura frontend crítica | 1 test | ≥ 70% |
| Drift documental | 7 puntos | 0 |
| p95 lecturas | No medida | < 300 ms |
| p95 escrituras | No medida | < 500 ms |
| Gates CI | Parciales | Todos verdes |
| WCAG AA flujos críticos | Sin auditar | 0 bloqueantes |

---

## 13. Fuera de alcance explícito

- Multi-tenant con aislamiento por organización.
- Roles personalizados más allá de admin/member.
- Facturación, límites por plan y onboarding comercial.
- Aplicación móvil.
- Edición colaborativa en tiempo real de documentos.
- Integraciones externas (Slack, GitHub, Jira).
- Analítica de producto avanzada.
- IA generativa dentro del producto.

Cualquier propuesta fuera de alcance se registra como idea y requiere una nueva spec.
