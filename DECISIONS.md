# Decisiones técnicas — TaskFlow

> Las decisiones completas, con contexto, opciones y consecuencias, viven en [`specs/taskflow/plan.md`](./specs/taskflow/plan.md) §ADRs. Este documento es un resumen histórico y un índice.

## Índice de ADRs

| ADR | Decisión | Estado |
|---|---|---|
| ADR-001 | Transporte de tokens: Bearer + auto-refresh y single-flight; cookies `httpOnly` reevaluadas y descartadas en T-097 | Aceptado (T-097) |
| ADR-002 | Tiempo real con SSE para notificaciones (fallback polling); Redis pub/sub, límites y carga implementados en T-081 | Aceptado |
| ADR-003 | Adjuntos en object storage: `StorageService` con backends PostgreSQL (default), local e InsForge Storage | Aceptado |
| ADR-004 | Alembic como única fuente de esquema; sin `create_all` en producción | Aceptado |
| ADR-005 | Envelope de errores `{error:{code,message,details,request_id}}` | Aceptado |
| ADR-006 | Solo tema oscuro + UI en inglés en este ciclo | Aceptado |
| ADR-007 | “Invitar” se renombra a “añadir miembro existente” | Aceptado |
| ADR-008 | Tests de integración contra PostgreSQL | Aceptado |
| ADR-009 | Dependencias fijadas + Renovate/Dependabot; Python 3.12 | Aceptado |
| ADR-010 | Rate limiting con Redis para múltiples instancias | Aceptado |
| ADR-011 | Identificadores `id`/`slug`; nombres/títulos deprecados | Aceptado |
| ADR-012 | Rotación de `SECRET_KEY` con clave dual (`SECRET_KEY_PREVIOUS` solo verifica) | Aceptado (T-103) |

**Revisión formal (T-004, 2026-11-10):** los 11 ADRs quedan aceptados y con responsable asignado (responsable del proyecto). Los ADRs que estaban `propuesto` se aceptaron con la implementación ya realizada y las desviaciones documentadas: ADR-002 (SSE implementado, pub/sub en T-081), ADR-003 (object storage InsForge implementado en T-054, verificado en producción) y ADR-006/007 (dark-only y “añadir miembro existente”).

---

## ¿Por qué PostgreSQL?

- Integridad relacional, transacciones ACID e índices compuestos.
- InsForge ofrece PostgreSQL gestionado con backups.
- SQLAlchemy 2 + Alembic dan portabilidad y migraciones versionadas.

**Corrección histórica:** la documentación anterior mencionaba Railway. El despliegue actual es **Render (API) + InsForge (DB) + Vercel (frontend)**.

---

## ¿Por qué JWT con refresh y rotación?

- Access token corto (15 min) reduce la ventana de exposición.
- Refresh token (7 días) mantiene la sesión sin pedir credenciales.
- Rotación: cada refresh invalida el anterior.
- Revocación en DB para logout y refresh reutilizado.
- **Implementado:** auto-refresh en el cliente y decisión de mantener Bearer; T-097 cerró la reevaluación de cookies `httpOnly` (ADR-001).

---

## ¿Por qué paginación por página y no cursor?

- El estado actual usa `page`/`page_size` en tareas.
- La paginación por cursor queda como evolución para listas grandes (notificaciones/actividad).
- Decisión documentada en `specs/taskflow/contracts/api.md`.
- **Corrección:** la documentación anterior afirmaba que había paginación por cursor; no era cierto. `CursorPaginatedResponse` existe pero no se usa.

---

## ¿Por qué structlog?

- Logs JSON con `request_id`, método, ruta, status y duración.
- Facilita trazabilidad y correlación con Sentry.
- No se registran secretos ni PII sensible.

---

## ¿Por qué slowapi?

- Integración sencilla con FastAPI.
- Límites por IP en auth (5/min registro, 10/min login).
- **Implementado en P2:** storage Redis compartido con fallback en memoria y límites en auth, uploads y búsqueda (T-030/T-031).

---

## ¿Por qué Render + InsForge + Vercel?

- Render: despliegue del backend desde el repositorio.
- InsForge: PostgreSQL gestionado.
- Vercel: frontend estático/SPA con previews.
- Docker Compose replica el entorno local con PostgreSQL + Redis.

**Corrección histórica:** Railway ya no es el proveedor de despliegue.

---

## ¿Por qué separar CRUD y routers?

- Los routers validan HTTP, autorización y orquestación.
- `crud.py` concentra acceso a datos.
- La capa de servicios se introduce solo para flujos con múltiples pasos (auth/sesión, borrados con storage, notificaciones), según `plan.md` §2.

---

## ¿Por qué versionar `/api/v1`?

- Permite evolucionar sin romper clientes.
- Los cambios incompatibles requieren `/api/v2` o deprecación documentada.
- El contrato vive en `specs/taskflow/contracts/api.md` y OpenAPI.

---

## Decisiones pendientes

No quedan ADRs en estado `propuesto`: ADR-001…011 están aceptados. Las
siguientes son evoluciones fuera de este ciclo y no bloquean el release:

1. **ADR-001:** reevaluación cerrada en T-097 (2026-11-11). Se mantiene Bearer +
   auto-refresh porque el frontend y la API son sitios distintos y una cookie de
   refresh requeriría cookies de terceros (`SameSite=None`), bloqueadas por
   Safari/Firefox. La alternativa real es un BFF en el mismo origen; se reabre
   si se adopta esa arquitectura, si aparece un XSS explotable o si se relaja la
   CSP. Riesgo residual en `specs/taskflow/security-checklist.md` (SEC-ASVS-01).
2. **ADR-007:** invitaciones reales por email; hoy el flujo es "añadir miembro
   existente".
3. **Cursor pagination:** paginación por cursor para listas grandes
   (notificaciones/actividad) cuando el volumen lo justifique.

Para cambiar una decisión: actualizar el ADR, la spec y el plan antes de implementar.
