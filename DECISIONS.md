# Decisiones técnicas — TaskFlow

> Las decisiones completas, con contexto, opciones y consecuencias, viven en [`specs/taskflow/plan.md`](./specs/taskflow/plan.md) §ADRs. Este documento es un resumen histórico y un índice.

## Índice de ADRs

| ADR | Decisión | Estado |
|---|---|---|
| ADR-001 | Transporte de tokens: Bearer + auto-refresh y single-flight; cookies `httpOnly` se reevalúan en P7 | Aceptado (alternativa) |
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

**Revisión formal (T-004, 2026-11-10):** los 11 ADRs quedan aceptados y con responsable asignado (responsable del proyecto). Los ADRs que estaban `propuesto` se aceptaron con la implementación ya realizada y las desviaciones documentadas: ADR-002 (SSE implementado, pub/sub en T-081), ADR-003 (PostgreSQL en lugar de S3 por falta de credenciales) y ADR-006/007 (dark-only y “añadir miembro existente”).

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
- **Implementado:** auto-refresh en el cliente y decisión de mantener Bearer; cookies `httpOnly` se reevalúan en P7 (ADR-001).

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
- **Pendiente P2:** storage Redis para consistencia multi-instancia y límites en más endpoints.

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

No quedan ADRs en estado `propuesto`: ADR-001…011 están aceptados (T-004). Las
siguientes decisiones son evoluciones fuera de este ciclo y no bloquean el
release:

1. **ADR-001:** reevaluar cookies `httpOnly` + CSRF en P7.
2. **ADR-003:** migrar adjuntos a object storage S3-compatible cuando haya credenciales (T-054).
3. **ADR-002:** fan-out con Redis pub/sub y prueba de carga de SSE (T-081).

Para cambiar una decisión: actualizar el ADR, la spec y el plan antes de implementar.
