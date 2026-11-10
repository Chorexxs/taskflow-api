# Baseline as-is — Auditoría del estado actual

**Fecha de corte:** 2026-11-09
**Método:** lectura de código, configuración, tests y documentación del repositorio.
**Objetivo:** dejar constancia verificable de lo que existe y de la deuda técnica que el ciclo de modernización debe resolver.

---

## Estado de resolución (P1)

Resueltos en P1: `BL-02`, `BL-03`, `BL-04`, `BL-05`, `BL-06`, `BL-08`, `BL-09`, `BL-10`, `BL-11`, `BL-14`, `BL-17`, `BL-32`, `BL-36`, `BL-37`, `BL-38`, `BL-41`.

Parciales: `BL-01` (refresh y logout corregidos; auto-refresh del cliente pendiente P2), `BL-07` (file_path eliminado; storage externo pendiente P4), `BL-45` (cliente API con errores tipados; quedan mensajes por pulir).

Pendientes: el resto de hallazgos S1/S2/S3 según `tasks.md` (P2–P6).

Verificación actual: **101 tests backend**, **12 tests frontend**, build de producción correcto y `alembic upgrade head` + `downgrade base` correctos.

---

## 1. Snapshot

| Elemento | Estado verificado |
|---|---|
| Backend | FastAPI + Uvicorn, Python 3.11 en Docker/CI (local con trazas de 3.12) |
| ORM/DB | SQLAlchemy 2 + PostgreSQL (InsForge, `us-east`) + Alembic (2 migraciones) |
| Auth | JWT `PyJWT`, bcrypt, access 15 min, refresh 7 días, revocación en DB |
| Frontend | React 18 + Vite 5 + React Router 7 + TanStack Query 5 + Tailwind 4 |
| UI | Tema oscuro por defecto, Lucide, React Hot Toast, `@dnd-kit` |
| API | 38 endpoints bajo `/api/v1` |
| Tablas | 10: `users`, `teams`, `team_members`, `projects`, `tasks`, `comments`, `attachments`, `activity_logs`, `notifications`, `revoked_tokens` |
| Tests | 54 funciones pytest; 1 test Vitest (`taskDetailComments.test.jsx`) |
| CI | GitHub Actions: pytest con servicio PostgreSQL + Codecov |
| Deploy | Render (API), Vercel (frontend), InsForge (DB); Docker/Procfile disponibles |
| Documentación | README extenso; AGENTS/STACK/DECISIONS parcialmente desactualizados |

---

## 2. Arquitectura actual

```
React SPA (Vercel)
   │  fetch + Bearer token (localStorage)
   ▼
FastAPI /api/v1 (Render)
   │  routers → crud → SQLAlchemy
   ├── PostgreSQL (InsForge)
   ├── Redis opcional (cache no usado)
   ├── uploads/ local (adjuntos)
   └── Sentry opcional (posible bug de import)
```

### Capas reales

- `app/main.py`: app, CORS, headers, logging, rate limit, health, routers.
- `app/routers/*`: validación HTTP, autorización y orquestación básica.
- `app/crud.py`: acceso a datos y algunas reglas (44 funciones).
- `app/models.py`: 10 modelos ORM.
- `app/schemas.py`: Pydantic v2, enums, saneado de caracteres de control.
- `app/auth.py`: JWT, bcrypt, lockout, revocación.
- `app/dependencies.py`: resolución de equipo y permisos de miembro/admin.
- `app/cache.py`: servicio Redis no utilizado.
- `app/logging_config.py` + `app/middleware.py`: structlog + request ID.
- `frontend/src`: SPA con Context API, React Query y cliente `fetch` centralizado.

### Flujos verificados

- Registro → login → `users/me` → dashboard.
- Crear equipo → invitar miembro existente → crear proyecto → crear tarea.
- Kanban con drag & drop → `PATCH` de tarea.
- Comentarios, adjuntos, notificaciones y activity log.
- Refresh de token: **no se usa desde el frontend**.

---

## 3. Hallazgos

Severidad: **S0** bloqueante de seguridad/pérdida de datos; **S1** alta; **S2** media; **S3** baja.

### S0 — Bloqueantes

| ID | Área | Evidencia | Impacto |
|---|---|---|---|
| BL-01 | Auth | `app/routers/auth.py::refresh(refresh_token: str, ...)` espera query param; `frontend/src/api/index.js::auth.refresh` envía JSON body; `AuthContext` nunca llama a refresh | El refresh no funciona; la sesión muere a los 15 min o el endpoint devuelve 422. Si se usa query, el token queda en logs/historial |
| BL-02 | Adjuntos | `app/routers/attachments.py::upload_attachment` usa `os.path.join(task_dir, file.filename)` sin sanitizar; lee todo el archivo en memoria; el límite solo se comprueba si `file.size` es truthy | Path traversal (`../../`), sobrescritura de archivos, bypass de tamaño y agotamiento de memoria |

### S1 — Altas

| ID | Área | Evidencia | Impacto |
|---|---|---|---|
| BL-03 | Permisos | `app/routers/teams.py::remove_member`: `if member.user_id != current_user.id and member.role != "admin": get_current_team_admin(...)` | Un `member` puede expulsar a un `admin`; no se protege al último admin |
| BL-04 | Seguridad | `app/main.py`: `allow_origins=["*"]` + `allow_credentials=True` | Configuración inválida/insegura; cualquier origen con credenciales |
| BL-05 | Seguridad | `app/auth.py`: si falta `SECRET_KEY`, usa `temp-dev-key-do-not-use-in-production` | Tokens falsificables si producción arranca sin variable |
| BL-06 | DB | `main.py` ejecuta `Base.metadata.create_all`; `schema.sql` no coincide con los modelos (`team_members` tiene `id SERIAL` en SQL y PK compuesta en ORM) | Deriva de esquema; migraciones y `create_all` compiten |
| BL-07 | Adjuntos | Archivos en disco local (`uploads/`), `AttachmentOut` expone `file_path`, borrar tarea no borra archivos | Pérdida de archivos en Render, fuga de rutas internas, huérfanos |
| BL-08 | Tareas | `PATCH /tasks/{id}` exige creador o admin; el Kanban permite arrastrar a cualquier miembro | Miembros no creadores reciben 403 al mover tareas |
| BL-09 | Tareas | `create_task` acepta `assigned_to` sin verificar que sea miembro; `assign` sí lo verifica | Asignaciones a usuarios ajenos al equipo |
| BL-10 | Frontend | 18 llamadas `queryClient.invalidateQueries(['clave'])` con sintaxis v4; React Query 5 espera `{ queryKey: [...] }` | Caché obsoleta tras mutaciones; solo una llamada es correcta |
| BL-11 | Frontend/API | Cliente `fetch` no comprueba `r.ok` salvo excepciones; `tasks.assign` envía `{assigned_to}` pero el backend espera `{user_id}` | Errores tratados como datos; asignar desasigna silenciosamente |
| BL-12 | API | `get_project_from_id_or_name` y `get_task_from_id_or_title` buscan por nombre/título con `.first()` e `ilike` | Ambiguüedad si hay duplicados; los nombres no son identificadores |
| BL-13 | Equipos | `invite_member` exige que el usuario ya exista; no hay token/email de invitación | “Invitar” es en realidad “añadir miembro existente” |
| BL-14 | Equipos | No se impide eliminar al último admin; el admin puede abandonar el equipo | Equipo sin administrador |
| BL-15 | Rate limit | `slowapi` con almacenamiento en memoria; solo register/login | Límites inconsistentes con múltiples instancias; resto de endpoints sin protección |
| BL-16 | Tests/CI | Integración sobre PostgreSQL (T-077); lint, build y umbrales de cobertura en CI (T-076) | Regresiones de cobertura o de estilo pasan desapercibidas |
| BL-17 | Observabilidad | `main.py`: `sentry_sdk.fastapi.FastApiIntegration()` | Posible `AttributeError` al arrancar con `SENTRY_DSN` definido |
| BL-18 | Notificaciones | Polling cada 30 s; sin endpoint de no leídas; sin paginación; menciones solo en docs, no implementadas | Escalabilidad y UX limitadas; docs engañosas |
| BL-19 | API | Solo las tareas tienen paginación; equipos, proyectos, miembros, comentarios, adjuntos, notificaciones y actividad devuelven todo | Listas no escalables |
| BL-20 | API | `HTTPException` devuelve `{detail}`; `DomainException` devuelve `{error, detail}` con 400 para todo | Cliente y documentación inconsistentes; códigos de estado incorrectos |

### S2 — Medias

| ID | Área | Evidencia | Impacto |
|---|---|---|---|
| BL-21 | Frontend | `ThemeProvider` no está montado en `main.jsx`; `:root` define tokens oscuros y `.dark` no se usa | Tema claro/oscuro inexistente; código muerto |
| BL-22 | Frontend | `axios` en `package.json` pero no se importa | Dependencia innecesaria |
| BL-23 | Docs | STACK/DECISIONS hablan de Railway; README de Render/InsForge; TTL 30 vs 15; “realtime” es polling; “delete project” archiva | Onboarding confuso y decisiones desactualizadas |
| BL-24 | Tooling | `requirements.txt` sin versiones; sin `pyproject.toml`; sin lint/typecheck backend | Builds no reproducibles; deuda silenciosa |
| BL-25 | Tooling | Docker/CI Python 3.11; bytecode local 3.12; sin `.python-version` | Divergencia de entorno |
| BL-26 | Docker | Contenedor corre como root; sin `HEALTHCHECK`; una sola etapa | Superficie de ataque y operación pobre |
| BL-27 | Legal | README declara MIT pero no existe `LICENSE` | Ambigüedad legal |
| BL-28 | A11y | Modales son `div` fijos sin focus trap/Escape consistente; botones de icono sin `aria-label` | Accesibilidad incompleta |
| BL-29 | Búsqueda | `ilike` sin escapar `%`/`_`; sin paginación; solo nombre/título | Resultados incorrectos y no escalables |
| BL-30 | Activity | Sin paginación, sin email del actor, diffs con IDs crudos | Auditoría poco útil |
| BL-31 | Cache | `CacheService` no se usa en endpoints; health consulta Redis igualmente | Complejidad sin beneficio |
| BL-32 | Auth | Logout revoca solo el access token; el refresh sigue válido en servidor | Sesión no cerrada de verdad |
| BL-33 | Auth | Cambiar contraseña no revoca tokens/sesiones | Token robado sigue válido |
| BL-34 | Auth | `clean_expired_tokens` existe pero nunca se programa | Tabla `revoked_tokens` crece indefinidamente |
| BL-35 | Permisos | Editar comentario valida autoría pero no pertenencia actual al equipo | Ex-miembro puede editar comentarios |
| BL-36 | DB | `schema.sql` está desactualizado respecto a los modelos | Fuente de esquema duplicada y divergente |
| BL-37 | Adjuntos | Sin allowlist MIME/extensión; `content_type` viene del cliente; sin antivirus | Upload de contenido peligroso |
| BL-38 | Adjuntos | Nombres duplicados sobrescriben el archivo y crean otra fila | Corrupción de adjuntos |
| BL-39 | Auth | Sin verificación de email, reset de contraseña ni borrado de cuenta | Postura de seguridad/UX incompleta |

### S3 — Bajas / informativas

| ID | Área | Evidencia | Impacto |
|---|---|---|---|
| BL-40 | Tests | 54 tests backend, 1 frontend, sin E2E | Cobertura insuficiente en flujos críticos |
| BL-41 | API | `AttachmentOut` incluye `file_path` | Fuga innecesaria de implementación |
| BL-42 | API | `CursorPaginatedResponse` y `NotificationUpdate` existen sin uso | Código muerto |
| BL-43 | Infra | `health` informa Redis/disco pero no distingue liveness/readiness | Operación en orquestadores |
| BL-44 | Frontend | `AuthContext` guarda `user_id` en localStorage y confía en él para permisos visuales | Manipulable; la API debe ser la autoridad |
| BL-45 | Frontend | `api.tasks.create` lanza error, el resto no; manejo inconsistente | UX de errores desigual |

---

## 4. Deriva documental

| Documento | Afirma | Realidad |
|---|---|---|
| `STACK.md` / `DECISIONS.md` | Railway + PostgreSQL gestionado | Render + InsForge |
| `README.md` | Access token 30 min en deploy | Código y `.env.example` usan 15 |
| `README.md` | Notificaciones en tiempo real | Polling cada 30 s |
| `README.md` | `DELETE` proyecto = eliminar | El endpoint archiva (`status=archived`) |
| `README.md` | Invitar miembros por email | Solo añade usuarios ya registrados |
| `AGENTS.md` | Árbol de archivos y stack | Parcialmente actualizado; omite rutas y cambios recientes |
| `schema.sql` | Esquema de la DB | No coincide con `models.py` |

---

## 5. Lo que está bien y debe preservarse

- Versionado `/api/v1` y prefijos anidados claros.
- Soporte de `id` o `slug` para equipos y de `id` para proyectos/tareas (aunque haya que corregir nombres).
- Activity log como base de auditoría.
- Índices compuestos en tareas/proyectos y `joinedload` para evitar N+1.
- Logging estructurado con `request_id` y middleware propio.
- Headers de seguridad, lockout de cuenta y rate limiting básico.
- Tests de backend por dominio y CI con PostgreSQL disponible.
- Docker Compose con Postgres + Redis + app.
- Diseño visual consistente con tokens CSS y componentes reutilizables.
- Optimistic UI en el Kanban.

---

## 6. Métricas de partida

| Métrica | Valor |
|---|---|
| Endpoints | 38 |
| Tablas | 10 |
| Tests backend | 54 |
| Tests frontend | 1 |
| Cobertura backend | No medida con umbral |
| Cobertura frontend | No medida |
| Migraciones Alembic | 2 |
| Hallazgos S0 | 2 |
| Hallazgos S1 | 18 |
| Hallazgos S2 | 19 |
| Hallazgos S3 | 6 |

> Estas métricas son la línea base para medir el éxito del ciclo en `spec.md` §Métricas.
