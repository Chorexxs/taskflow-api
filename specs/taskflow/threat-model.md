# Modelo de amenazas (STRIDE) — TaskFlow

**Versión:** 1.0
**Fecha:** 2026-11-11
**Autor:** responsable del proyecto (revisión asistida por agente)
**Método:** STRIDE sobre flujos, activos y fronteras de confianza.
**Tarea:** [`T-104`](./tasks.md) · **Checklist:** [`security-checklist.md`](./security-checklist.md)
**Estado:** aceptado; revisión trimestral y ante cambios en auth, uploads, SSE o infraestructura.

---

## 1. Alcance

Incluye la API (`app/`), el frontend SPA (`frontend/`), PostgreSQL gestionado
(InsForge), almacenamiento de adjuntos, Redis opcional y el pipeline de
despliegue (Render, Vercel, GitHub Actions).

Fuera de alcance: seguridad física del proveedor, detalle del aislamiento de
InsForge/Render (se asume su responsabilidad contractual), MFA y roles
personalizados (fuera del producto), y atacantes con acceso root al host.

---

## 2. Activos

| ID | Activo | Impacto si se compromete |
|---|---|---|
| A-01 | Contraseñas y hashes bcrypt | Suplantación de cuentas |
| A-02 | Access y refresh tokens | Acceso a datos del usuario y de sus equipos |
| A-03 | `SECRET_KEY` y secretos de infraestructura | Falsificación de tokens y acceso a DB/storage |
| A-04 | Datos de equipos: proyectos, tareas, comentarios | Confidencialidad e integridad del negocio |
| A-05 | Adjuntos | Exfiltración de documentos, malware |
| A-06 | Historial de actividad y notificaciones | Reputación, PII indirecta |
| A-07 | Base de datos y backups | Pérdida total o parcial de servicio |
| A-08 | Disponibilidad de API/SSE | Denegación de servicio |
| A-09 | Cadena de suministro (dependencias, CI) | Ejecución de código en build/deploy |

---

## 3. Actores

| Actor | Confianza | Capacidades |
|---|---|---|
| Anónimo | Ninguna | Registro, login, endpoints públicos y rate-limited |
| Miembro autenticado | Baja | Acceso a sus equipos; crea proyectos/tareas/comentarios |
| Admin de equipo | Media | Gestiona miembros, roles, archivado |
| Ex-miembro | Revocada | Conserva tokens hasta expirar; no debe acceder a nada del equipo |
| Atacante en red | Ninguna | Fuerza bruta, replay, enumeración, DoS |
| Cliente comprometido (XSS) | Media | Ejecuta JS en el navegador de la víctima |
| Insider operativo | Alta | Variables de entorno, consola del proveedor |
| Dependencia/acción CI comprometida | Alta en build | Ejecuta código en el pipeline |

---

## 4. Fronteras de confianza

```text
Navegador ──TLS──> Vercel (SPA, CSP)
    │                    │
    └──────TLS───────────┴──> API FastAPI (Render)
                                ├──TLS──> PostgreSQL (InsForge)
                                ├──TLS──> Object storage (InsForge)
                                └──TLS──> Redis (opcional)
GitHub ──SHA fijado──> GitHub Actions ──> Render / Vercel
```

- **F1** navegador ↔ Vercel: sirve assets estáticos con CSP y HSTS.
- **F2** navegador ↔ API: CORS por allowlist, Bearer, sin cookies de sesión.
- **F3** API ↔ PostgreSQL: `DB_SSLMODE=require` en producción.
- **F4** API ↔ storage: bucket privado; la API media todas las descargas.
- **F5** CI/CD: acciones fijadas por SHA, `permissions: contents: read`,
  gitleaks y pip-audit.

---

## 5. Flujos críticos

1. Registro, login, refresh rotativo, logout y cambio de contraseña.
2. Alta de equipo, invitación, cambio de rol y expulsión.
3. CRUD de proyectos, tareas, comentarios y menciones.
4. Subida, descarga y borrado de adjuntos.
5. Notificaciones: polling y SSE autenticado.
6. Búsqueda dentro del equipo.
7. Operación: migraciones, backups, rotación de claves y despliegue.

---

## 6. Catálogo STRIDE

Leyenda de riesgo residual: **B** bajo, **M** medio, **A** alto.
Cada fila referencia la mitigación principal y su evidencia.

### 6.1 Identidad y sesión

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-01 | **S**poofing | Robo de contraseña por fuerza bruta o credential stuffing | bcrypt, política 8–128, rate limit 10/min en login, bloqueo tras 5 fallos durante 15 min, auditoría sin PII | B |
| TM-02 | **S**poofing | Falsificación de JWT | HS256 con `SECRET_KEY` obligatoria fuera de dev; firma verificada en cada request; `alg` fijado en servidor | B |
| TM-03 | **S**poofing | Reutilización de refresh robado | Refresh rotativo, detección de reutilización y revocación global (`test_refresh_reuse.py`) | B |
| TM-04 | **S**poofing | Sesión válida tras logout o cambio de contraseña | Logout revoca access + refresh; cambio de contraseña exige la actual e incrementa `token_version` | B |
| TM-05 | **S**poofing | Rotación de clave que invalida sesiones o deja tokens antiguos eternos | Clave dual: `SECRET_KEY` firma, `SECRET_KEY_PREVIOUS` solo verifica durante la ventana (ADR-012, `test_secret_rotation.py`) | B |
| TM-06 | **T**ampering | Manipulación de claims del JWT | Firma criptográfica; claims `sub`, `type` y `exp` validados; la autorización no confía en claims de rol | B |
| TM-07 | **R**epudiation | Negación de acciones de auth | Eventos de registro/login/logout/refresh/bloqueo con `user_id` y `request_id` (`test_auth_audit.py`) | B |

### 6.2 Autorización y multi-tenant

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-08 | **E**levation | Member ejecuta acciones de admin (roles, archivado, expulsión) | Dependencias `get_current_team_admin`/`get_current_team_member`; matriz 401/403/404 por endpoint (`test_permission_matrix.py`) | B |
| TM-09 | **I**nformation disclosure | IDOR/BOLA: acceder a recursos de otro equipo | Toda ruta resuelve el equipo y filtra por pertenencia; recurso ajeno → 404, rol insuficiente → 403 | B |
| TM-10 | **E**levation | Ex-miembro conserva acceso o tareas asignadas | Expulsión borra membresía, desasigna tareas y registra actividad (`test_team_member_removal.py`) | B |
| TM-11 | **T**ampering | Dos admins se expulsan a la vez y dejan el equipo sin admin | `SELECT … FOR UPDATE` sobre el equipo antes de contar admins (`test_last_admin_race.py`, PostgreSQL) | B |
| TM-12 | **T**ampering | Escalada vía edición parcial de tarea (estado + otros campos) | `PATCH /status` solo acepta `status`/`position`; el resto exige creador o admin | B |

### 6.3 Datos y API

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-13 | **T**ampering | Duplicados por reintentos o doble clic | `Idempotency-Key` en POST críticos con replay, 422/409 y purga a 24 h (`test_idempotency.py`) | B |
| TM-14 | **I**nformation disclosure | Errores que filtran rutas, stack traces o datos de otros | Envelope `{error:{code,message,details,request_id}}`; 422 sin `input`; 5xx genérico | B |
| TM-15 | **D**enial of service | Listados o búsquedas sin límite | Paginación con `page_size ≤ 100`, índices, rate limits, escape de comodines SQL | B |
| TM-16 | **T**ampering | Inyección SQL | SQLAlchemy con parámetros; `LIKE` escapado en búsqueda; sin SQL dinámico con entrada | B |
| TM-17 | **I**nformation disclosure | Enumeración de usuarios o equipos | Respuestas 404 uniformes para recursos ajenos; login con mensaje genérico; sin listados públicos | B |
| TM-18 | **R**epudiation | Falta de rastro de cambios | `activity_logs` append-only con actor y diff legible | B |

### 6.4 Archivos

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-19 | **T**ampering | Path traversal o nombre malicioso | `sanitize_filename` + claves generadas por el servidor; nunca se usa `file.filename` en rutas | B |
| TM-20 | **T**ampering | Ejecución de archivos peligrosos | Allowlist de extensión + MIME; límite de 10 MB aplicado en streaming; checksum SHA-256 | B |
| TM-21 | **I**nformation disclosure | Descarga de adjuntos ajenos o URL pública permanente | Bucket privado; descarga a través de la API con pertenencia al equipo; no se expone `storage_key` ni `file_path` | B |
| TM-22 | **D**enial of service | Subidas masivas o gigantes | Límite en streaming, `413`, rate limit 20/min y cuotas de proveedor | M (cuota) |

### 6.5 Tiempo real y notificaciones

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-23 | **S**poofing | Suscripción SSE sin autenticar o a notificaciones ajenas | Endpoint con Bearer validado; eventos filtrados por `user_id` | B |
| TM-24 | **D**enial of service | Agotar conexiones o el pool de base de datos | Límite 500 conexiones/5 por usuario con `503` + `Retry-After`; sesiones DB cortas; heartbeat; prueba 500/500 | B |
| TM-25 | **I**nformation disclosure | Notificaciones duplicadas o con datos de otro equipo | `dedupe_key`, preferencias de silenciado, contenido mínimo sin PII | B |
| TM-26 | **R**epudiation | Menciones sin rastro | Notificación + actividad al crear el comentario | B |

### 6.6 Operación y cadena de suministro

| ID | Categoría | Amenaza | Mitigación | Residual |
|---|---|---|---|---|
| TM-27 | **S**poofing | Deploy con clave de desarrollo o `SECRET_KEY` débil/filtrada | Fail-fast fuera de dev/test; secretos solo en Render; gitleaks en pre-commit y CI | B |
| TM-28 | **T**ampering | Acción de CI comprometida o permisos excesivos | Acciones fijadas por SHA y `permissions: contents: read` | B |
| TM-29 | **I**nformation disclosure | Dependencia vulnerable | Dependencias fijadas + `pip-audit` en CI | M (transitiva) |
| TM-30 | **D**enial of service | Migración o deploy deja la API inservible | `alembic upgrade head` en el runbook, health live/ready, backup y restore drill verificado (`T-102`) | B |
| TM-31 | **T**ampering | Deriva de esquema o datos | Alembic como única fuente; constraints CHECK; snapshot OpenAPI en CI | B |
| TM-32 | **I**nformation disclosure | Documentación interactiva expuesta en producción | `/docs`, `/redoc` y `/openapi.json` deshabilitados en producción | B |

---

## 7. Casos de abuso priorizados

1. **XSS que roba tokens de `localStorage`.** Riesgo aceptado en ADR-001; se
   mitiga con CSP `script-src 'self'` en Vercel, access de 15 min, rotación y
   revocación. Reabrir la decisión si aparece un XSS explotable o se adopta un
   BFF en el mismo origen.
2. **BOLA/IDOR sobre IDs incrementales.** La autorización se resuelve siempre
   contra la pertenencia al equipo; los recursos ajenos responden 404.
3. **Replay de refresh o de POST.** Refresh rotativo con detección de reuso;
   POST críticos con `Idempotency-Key`.
4. **Expulsión cruzada de admins.** Serializada con lock de fila y probada en
   PostgreSQL.
5. **Subida de archivo malicioso o traversal.** Allowlist, streaming, nombre
   saneado, checksum y bucket privado.
6. **Agotar SSE o el pool de conexiones.** Límites por usuario y globales,
   heartbeats y sesiones DB cortas.
7. **Enumeración de equipos/usuarios.** Sin endpoints públicos de búsqueda de
   usuarios; 404 uniforme.

---

## 8. Riesgos residuales aceptados

| ID | Riesgo | Justificación | Revisión |
|---|---|---|---|
| RR-01 | Tokens accesibles desde JS (sin cookies `httpOnly`) | Frontend y API en dominios distintos; cookies de terceros bloqueadas. CSP y rotación reducen el impacto (ADR-001, T-097) | Si hay XSS, BFF o cambia la política de cookies |
| RR-02 | Dependencias transitivas vulnerables | Fijadas y auditadas en CI; parchear depende del mantenedor | Semanal en CI |
| RR-03 | Sin MFA | Fuera de alcance del ciclo | Nuevo ciclo |
| RR-04 | Una sola región/proveedor | Simplicidad operativa; backups y restore verificados | Trimestral |
| RR-05 | Cifrado en reposo y retención de logs dependen del proveedor | No verificable desde el repo | Revisión contractual |
| RR-06 | Sin prueba de carga de escritura sostenida | Solo se midió lectura (p95 < 33 ms) y SSE 500/500 | Próximo ciclo |

---

## 9. Supuestos

- TLS extremo a extremo en producción (Vercel, Render e InsForge).
- El proveedor aísla la base de datos y el bucket; no son públicos.
- Los secretos viven en el gestor del proveedor, nunca en el repositorio.
- El cliente HTTP del frontend valida `r.ok` y trata errores como errores.
- Los operadores aplican el runbook (migración, backup, rotación) antes de un
  release.

---

## 10. Revisión y evidencia

- **Cadencia:** trimestral y obligatoria ante cambios en auth, uploads, SSE,
  permisos o infraestructura.
- **Responsable:** responsable del proyecto.
- **Evidencia automatizada:** `tests/test_permission_matrix.py`,
  `test_refresh_reuse.py`, `test_auth_audit.py`, `test_attachments.py`,
  `test_idempotency.py`, `test_last_admin_race.py`, `test_secret_rotation.py`,
  `test_sse.py`, `test_backup_restore.py`.
- **Evidencia documental:** [`security-checklist.md`](./security-checklist.md),
  [`plan.md`](./plan.md) (ADR-001…012), [`data-model.md`](./data-model.md) y
  [`contracts/api.md`](./contracts/api.md).

Cualquier amenaza nueva se registra con ID `TM-##` y se enlaza a un `T-###`
antes de implementar la mitigación.

## 11. Revisión 2026-11-11 (auditoría full)

Auditoría de seguridad completa sobre `307d345`; sin SEC-0. Corregidos en T-108:

- **SEC-1.1:** imagen Docker con `.env`/`.git` → `.dockerignore`, Dockerfile
  mínimo y gate de CI que verifica el contenido de la imagen (TM-27/TM-31).
- **SEC-2.1:** Sentry sin PII/bodies → configuración explícita y scrubbing
  (TM-07/TM-14).
- **SEC-2.2:** bodies JSON/form sin límite y creaciones sin rate limit →
  middleware de tamaño y límites por endpoint (TM-15/TM-22).
- **SEC-2.3:** clave/algoritmo/TLS sin validar → fail-fast de configuración
  (TM-02/TM-27).
- **SEC-2.4:** `/health` filtraba errores de DB → mensaje genérico (TM-14).
- **SEC-2.5:** logout no limpiaba React Query → caché limpiada (TM-09).

Residuales aceptados: enumeración de cuentas (SEC-ASVS-07) y bloqueo sin
revocación de sesiones (SEC-ASVS-10). El rate limit detrás del proxy se corrigió
y verificó en T-109 (SEC-ASVS-08); magic bytes y escaneo ClamAV opcional en
T-109/T-110 (SEC-ASVS-09).
