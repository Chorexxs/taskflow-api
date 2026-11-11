# Checklist ASVS L2 — TaskFlow

**Fecha:** 2026-11-10
**Alcance:** API FastAPI + frontend React + despliegue Render/InsForge/Vercel.
**Referencia:** OWASP ASVS 4.0.3, nivel 2.

Leyenda: ✅ cumple · 🟡 parcial o con riesgo aceptado · ❌ no aplica / pendiente.

---

## V1 — Arquitectura, diseño y amenazas

| Control | Estado | Evidencia |
|---|---|---|
| Componentes y fronteras documentados | ✅ | `plan.md`, `data-model.md` |
| Autenticación centralizada y reutilizada | ✅ | `app/auth.py`, `get_current_user` |
| Autorización en servidor para cada endpoint | ✅ | Matriz de permisos + `tests/test_permission_matrix.py` |
| Decisiones de seguridad registradas | ✅ | `DECISIONS.md`, ADR-001…011 |
| Amenazas y riesgos identificados | ✅ | `threat-model.md` (STRIDE, TM-01…TM-32) con mitigaciones y riesgos residuales (T-104) |

## V2 — Autenticación

| Control | Estado | Evidencia |
|---|---|---|
| Contraseñas ≥ 8 y ≤ 128, sin control chars | ✅ | `schemas.py`, T-027 |
| Hash con bcrypt y salt por contraseña | ✅ | `app/auth.py` |
| Bloqueo tras intentos fallidos | ✅ | `MAX_LOGIN_ATTEMPTS`, tests de lockout |
| Sin mensajes que revelen si el email existe | ✅ | Login devuelve 401 genérico |
| Rate limiting en registro/login/refresh | ✅ | T-030/T-031, `tests/test_rate_limit_http.py` |
| Cambio de contraseña exige la actual y revoca sesiones | ✅ | T-028, `token_version` |
| MFA | ❌ | Fuera de alcance de este ciclo |

## V3 — Sesión

| Control | Estado | Evidencia |
|---|---|---|
| Access token corto (15 min) | ✅ | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh rotativo de 7 días | ✅ | `create_refresh_token`, `revoke_token` |
| Logout revoca access y refresh, idempotente | ✅ | `POST /auth/logout`, tests P1 |
| Refresh nunca en query string | ✅ | T-083: el token en query se rechaza con 422 sin rotarlo |
| Cookies `httpOnly` + CSRF | 🟡 | Riesgo aceptado tras T-097: Bearer + auto-refresh; cookies de terceros bloqueadas entre Vercel y Render (ADR-001) |
| Detección de reutilización de refresh | ✅ | T-034; reuse → 401 y revocación global de sesiones |

## V4 — Control de acceso

| Control | Estado | Evidencia |
|---|---|---|
| Denegar por defecto; permisos explícitos | ✅ | Dependencias de equipo, tests 401/403/404 |
| Sin IDOR entre equipos | ✅ | Resolución team-scoped; recurso ajeno → 404 |
| Rol admin/member verificado en servidor | ✅ | `app/dependencies.py` |
| Último admin protegido | ✅ | Tests de expulsión/degradación |
| Acciones de UI no sustituyen a la API | ✅ | `AGENTS.md`, matriz testeada |
| Asignación solo a miembros del equipo | ✅ | `POST /tasks` valida `assigned_to` |

## V5 — Validación y sanidad

| Control | Estado | Evidencia |
|---|---|---|
| Validación Pydantic v2 en todas las entradas | ✅ | `app/schemas.py` |
| Consultas parametrizadas (SQLAlchemy) | ✅ | `app/crud.py` |
| Escape de comodines en búsqueda | ✅ | T-049 |
| Sanitización de nombres de archivo | ✅ | `sanitize_filename` |
| Límite de tamaño en streaming | ✅ | T-014, `MAX_UPLOAD_SIZE` |
| Allowlist de extensión/MIME | ✅ | `validate_upload_type` |

## V6 — Criptografía

| Control | Estado | Evidencia |
|---|---|---|
| Sin algoritmos propios | ✅ | `PyJWT`, `bcrypt` |
| Secretos fuera del código | ✅ | `.env`, fail-fast en producción |
| `SECRET_KEY` sin fallback en producción | ✅ | `app/config.py` |
| `SECRET_KEY` y algoritmo robustos | ✅ | T-108: longitud ≥32, `SECRET_KEY_PREVIOUS` ≥32 y `ALGORITHM` limitado a HS256/384/512 |
| TLS en despliegue | ✅ | Render/Vercel/InsForge; HSTS |
| TLS obligatorio a la base de datos | ✅ | T-108: `DB_SSLMODE` debe ser `require`/`verify-*` en producción |
| Rotación de claves documentada | ✅ | T-103/ADR-012: `SECRET_KEY_PREVIOUS` acepta tokens antiguos durante la ventana; procedimiento en `plan.md` §10 |

## V7 — Errores y logging

| Control | Estado | Evidencia |
|---|---|---|
| Errores sin stack trace al cliente | ✅ | Envelope + handler global |
| `request_id` en respuestas y logs | ✅ | `middleware.py`, `logging_config.py` |
| Sin contraseñas, tokens ni PII en logs | ✅ | T-033, `tests/test_auth_audit.py` |
| Sentry sin PII ni bodies | ✅ | T-108: `send_default_pii=False`, `max_request_body_size="never"` y `before_send` que redacta credenciales |
| Eventos de auth auditados | ✅ | login/logout/refresh/lockout/cambio de credenciales |
| Retención de logs | 🟡 | Depende del proveedor; no configurada explícitamente |

## V8 — Protección de datos

| Control | Estado | Evidencia |
|---|---|---|
| Datos sensibles no expuestos en schemas | ✅ | `UserOut` sin hash; `AttachmentOut` sin rutas |
| Minimización de PII | ✅ | No se registra email en auditoría |
| Cifrado en tránsito | ✅ | TLS gestionado |
| Cifrado en reposo | 🟡 | Gestionado por InsForge; no verificable desde el repo |
| Backups y restore | ✅ | T-102: drill real 2026-11-11 (12 tablas/92 filas, revisión `b2c3d4e5f6a7`) con `scripts/backup_restore_drill.py` |

## V9 — Comunicación

| Control | Estado | Evidencia |
|---|---|---|
| HTTPS obligatorio | ✅ | HSTS, Render/Vercel |
| CORS con allowlist explícita | ✅ | `CORS_ORIGINS`, tests P1 |
| Sin `*` con credenciales | ✅ | Validación en `config.py` |
| Cabeceras de seguridad | ✅ | CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy |

## V10 — Código malicioso

| Control | Estado | Evidencia |
|---|---|---|
| Sin dependencias sin pin | ✅ | `requirements.txt`, `package-lock.json` |
| Auditoría de dependencias | ✅ | `npm audit --omit=dev` → 0 y gate en CI; `pip-audit` en backend; Renovate/Dependabot |
| Imagen Docker sin secretos ni datos locales | ✅ | T-108: `.dockerignore` + copia mínima; CI verifica que no contiene `.env`, `.git`, `tests` ni `frontend` |
| Sin ejecución de archivos subidos | ✅ | Adjuntos servidos como descarga; allowlist |
| Revisión de dependencias nuevas | ✅ | PR + lockfiles |

## V11 — Lógica de negocio

| Control | Estado | Evidencia |
|---|---|---|
| Límites de recursos (paginación ≤ 100) | ✅ | T-038 |
| Límite de body JSON/form y rate limit en creaciones | ✅ | T-108: 1 MB JSON, 64 KB form y límites por endpoint |
| Idempotencia de logout | ✅ | Tests P1 |
| Coherencia de borrados | ✅ | T-044, cascada y limpieza |
| Reasignación al expulsar | ✅ | T-042 |
| Prevención de carreras en último admin | ✅ | T-101: `SELECT … FOR UPDATE` sobre la fila del equipo serializa expulsiones y cambios de rol |

## V12 — Archivos y recursos

| Control | Estado | Evidencia |
|---|---|---|
| Path traversal bloqueado | ✅ | `sanitize_filename`, `_task_upload_dir` |
| Nombres únicos | ✅ | UUID en storage |
| Descarga autenticada y team-scoped | ✅ | `attachments.py` |
| Storage persistente en producción | ✅ | `STORAGE_BACKEND=insforge` (bucket privado con `storage_key`) |
| Checksum de adjuntos | ✅ | T-055: SHA-256 calculado durante el streaming y almacenado en la DB |
| Magic bytes / antivirus | 🟡 | Allowlist de extensión/MIME y descarga forzada; falta inspección de contenido (deuda) |

## V13 — API

| Control | Estado | Evidencia |
|---|---|---|
| Contrato OpenAPI versionado y verificado en CI | ✅ | `contracts/openapi.json`, T-078 |
| Envelope de errores estable | ✅ | `{detail, error:{code,message,details,request_id}}` |
| Paginación uniforme | ✅ | T-038 |
| Rate limit con `Retry-After` | ✅ | T-031 |
| Versionado `/api/v1` | ✅ | Routers |
| Idempotencia en POST críticos | ✅ | T-100: `Idempotency-Key` con replay, 422/409 y purga a 24 h |

## V14 — Configuración

| Control | Estado | Evidencia |
|---|---|---|
| Fail-fast de configuración crítica | ✅ | `Settings.validate_runtime` |
| Contenedor non-root + HEALTHCHECK | ✅ | `Dockerfile`, T-075 |
| Health live/ready separados | ✅ | `/health/live`, `/health/ready` |
| Secretos en gestor del proveedor | ✅ | Render env vars |
| CORS/entorno por despliegue | ✅ | `blockers.md` B-02/B-03 |

---

## Hallazgos abiertos priorizados

| ID | Riesgo | Prioridad | Tarea |
|---|---|---|---|
| SEC-ASVS-01 | Sin cookies `httpOnly`; token accesible desde JS | Baja (riesgo aceptado) | T-097 / ADR-001: decisión final de mantener Bearer; reabrir si hay BFF, XSS explotable o se relaja la CSP |
| SEC-ASVS-02 | Checksum de adjuntos | ✅ Resuelto (T-055) | — |
| SEC-ASVS-03 | Carrera al degradar/expulsar al último admin | ✅ Resuelto (T-101) | Lock `FOR UPDATE` + test de concurrencia |
| SEC-ASVS-04 | Sin prueba de restore de backups | ✅ Resuelto (T-102) | — |
| SEC-ASVS-05 | Integración de tests en SQLite | ✅ Resuelto (T-077): PostgreSQL con migraciones | — |
| SEC-ASVS-06 | Imagen Docker con `.env`, `.git` y datos locales | ✅ Resuelto (T-108) | `.dockerignore` + Dockerfile mínimo + gate de CI |
| SEC-ASVS-07 | Enumeración de cuentas y oráculo de bloqueo | Baja (aceptado) | Rate limit; requiere verificación por email para cerrar del todo |
| SEC-ASVS-08 | Rate limit confía en `X-Forwarded-For` del proxy | Baja | Verificar `forwarded_allow_ips` en Render |
| SEC-ASVS-09 | Uploads sin magic bytes ni antivirus | Baja | Deuda de nuevo ciclo |
| SEC-ASVS-10 | El bloqueo de cuenta no revoca sesiones existentes | Baja (aceptado) | Comprobar `is_blocked` en auth si el producto lo exige |

## Firma

Revisión realizada por el agente el 2026-11-11 contra el código y los specs del
repositorio, con auditoría full de seguridad (SEC-1.1…SEC-4.6). Los puntos 🟡
quedan registrados como deuda aceptada; no hay hallazgos críticos abiertos
(`SEC-0`/`CA-0` = 0) y los hallazgos SEC-1/SEC-2 de la auditoría están corregidos
en T-108.
