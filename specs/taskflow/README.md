# TaskFlow — Paquete SDD (Spec-Driven Development)

**Versión:** 1.0 — Draft para revisión
**Fecha:** 2026-11-09
**Proyecto:** TaskFlow API
**Alcance del ciclo:** documentación + bugs conocidos + modernización completa
**Estado:** P0–P9 ejecutados; producción verificada con object storage activo. Solo queda reevaluar cookies `httpOnly` en P7.

---

## Qué es esto

Este paquete aplica **Spec-Driven Development**: la especificación es la fuente de verdad y el código se implementa contra ella. No se considera terminada una tarea si el comportamiento implementado no coincide con la spec o si la spec no se actualizó.

El paquete documenta dos estados:

- **As-is:** lo que existe hoy, incluyendo deuda técnica y bugs.
- **To-be:** el producto y la arquitectura objetivo, con requisitos verificables.

---

## Artefactos y orden de lectura

| # | Archivo | Qué contiene | Cuándo leerlo |
|---|---|---|---|
| 1 | [`constitution.md`](./constitution.md) | Principios no negociables, quality gates y definición de terminado | Antes de tocar código |
| 2 | [`baseline.md`](./baseline.md) | Inventario del estado actual y auditoría de hallazgos (BL-01…) | Para entender qué se hereda |
| 3 | [`spec.md`](./spec.md) | Visión, personas, requisitos funcionales (FR), no funcionales (NFR), permisos y criterios de aceptación | Para saber qué construir |
| 4 | [`plan.md`](./plan.md) | Arquitectura objetivo, ADRs, fases, testing, despliegue y riesgos | Para saber cómo construirlo |
| 5 | [`tasks.md`](./tasks.md) | Backlog accionable (T-001…) con dependencias, tamaño y trazabilidad | Para ejecutar |
| 6 | [`data-model.md`](./data-model.md) | Modelo actual y objetivo, constraints, índices y migraciones | Antes de cambiar la DB |
| 7 | [`contracts/api.md`](./contracts/api.md) | Convenciones HTTP, errores, paginación, auth y catálogo de endpoints | Antes de cambiar la API |
| 8 | [`security-checklist.md`](./security-checklist.md) | Checklist ASVS L2 y deuda de seguridad aceptada | Antes de un release |

### Auditorías bajo demanda

Fuera del ciclo funcional, pero con la misma constitución como norma superior:

| Spec | Qué revisa | Activación |
|---|---|---|
| [`../audit/code-audit.md`](../audit/code-audit.md) | Código, arquitectura, escalabilidad, tests y contratos | `audita el código` / `/audit-code` |
| [`../audit/security-audit.md`](../audit/security-audit.md) | Secretos, authn/authz, uploads, dependencias, CI/CD y privacidad | `audita la seguridad` / `/audit-security` |

> No se ejecutan de forma autónoma: solo cuando el usuario lo ordena. Son de
> solo lectura y no atacan producción.

---

## Flujo de trabajo

```
Constitución → Spec → Plan → Tasks → Implementación → Verificación → Actualización de spec
```

Reglas de uso:

1. **No hay código sin tarea.** Cada PR referencia un `T-###` y los `FR-###`/`BL-##` que cubre.
2. **No hay cambio de comportamiento sin spec.** Si la implementación revela un requisito nuevo, primero se actualiza `spec.md` y luego el código.
3. **No hay merge sin quality gates.** Ver `constitution.md`.
4. **No hay migración sin rollback.** Ver `data-model.md`.
5. **No hay release sin smoke test.** Ver `plan.md`.

---

## Convenciones de identificadores

| Prefijo | Significado | Ejemplo |
|---|---|---|
| `BL-##` | Hallazgo del baseline (as-is) | `BL-01` refresh roto |
| `FR-<ÁREA>-##` | Requisito funcional | `FR-AUTH-03` |
| `NFR-<ÁREA>-##` | Requisito no funcional | `NFR-SEC-02` |
| `ADR-###` | Decisión de arquitectura | `ADR-001` |
| `T-###` | Tarea del backlog | `T-011` |
| `P#` | Fase de entrega | `P1` |

---

## Decisiones que deben confirmarse antes de P2

Estas decisiones no bloqueaban P0/P1, pero sí el resto del plan. Estado tras
T-004: **todas aceptadas** (ver ADRs en `plan.md` y `DECISIONS.md`).

| ID | Decisión | Propuesta por defecto | ADR |
|---|---|---|---|
| D-01 | Transporte de tokens en el navegador | Mantener Bearer + auto-refresh en P2; evaluar cookies `httpOnly` en P3 | ADR-001 |
| D-02 | Tiempo real | SSE para notificaciones con polling de respaldo | ADR-002 |
| D-03 | Almacenamiento de adjuntos | Object storage S3-compatible (InsForge Storage) | ADR-003 |
| D-04 | Estrategia de migraciones | Alembic como única fuente; sin `create_all` en producción | ADR-004 |
| D-05 | Formato de errores | Envelope único `{error:{code,message,details,request_id}}` | ADR-005 |
| D-06 | Idioma de la UI | Mantener inglés en UI y español en documentación | ADR-006 |
| D-07 | Alcance de “tiempo real” | Solo notificaciones; el Kanban sigue siendo colaborativo por recarga | ADR-002 |
| D-08 | Invitaciones | Renombrar a “añadir miembro existente” o implementar invitación real con token/email | ADR-007 |

---

## Definición de terminado (resumen)

Una tarea está terminada cuando:

- [ ] Cumple sus criterios de aceptación de `spec.md`.
- [ ] Tiene tests automatizados (unitarios y/o integración) que fallan sin el cambio.
- [ ] Pasa lint, typecheck, tests y build.
- [ ] No introduce secretos, PII en logs ni endpoints sin autorización.
- [ ] Actualiza `spec.md`, `contracts/api.md` o `data-model.md` si cambió el contrato.
- [ ] Tiene nota de despliegue/rollback si toca DB, auth o storage.
- [ ] El PR referencia `T-###` y `FR-###`/`BL-##`.

---

## Ubicación

Este paquete vive en `specs/taskflow/` y es la fuente de verdad del ciclo. `README.md` y `AGENTS.md` enlazan aquí.

## Registro de ejecución

| Fase | Estado | Notas |
|---|---|---|
| P0 — Gobernanza | ✅ Ejecutado | Specs, documentación, LICENSE, baseline, ADRs aceptados, entornos, política de release y backlog importado en GitHub (T-003) |
| P1 — Correcciones críticas | ✅ Ejecutado | Refresh, logout, uploads, permisos de equipo, CORS, secret fail-fast, Kanban, cliente API, Sentry, Alembic |
| P2 — Auth/sesión | ✅ Ejecutado | Auto-refresh, contraseñas, cambio con revocación, limpieza de tokens, rate limit Redis, headers, auditoría y reutilización de refresh. Cookies `httpOnly` se reevalúan en P7 (ADR-001) |
| P3 — API/datos | ✅ Ejecutado | IDs/slugs, paginación, errores, permisos, borrados, archivado, actividad y búsqueda |
| P4 — Colaboración/storage | ✅ Ejecutado | Notificaciones, menciones, SSE + polling, activity y object storage con backfill (T-054); `STORAGE_BACKEND=insforge` verificado en producción |
| P5 — Frontend | ✅ Ejecutado | Cliente API, AuthContext, a11y, responsive, estados de error, MSW y dark-only |
| P6 — Ops/release | ✅ Ejecutado | Ruff/mypy, CI completo, runbook, health, gitleaks/pip-audit, checklist, smoke funcional 15/15 y smoke de performance; verificación post-deploy completada |
| P7 — Realtime | ✅ Ejecutado | SSE con Redis pub/sub, fallback en proceso, límites de conexión, backoff y prueba de 500 conexiones (T-081) |
| P8 — Auditoría de seguridad | ✅ Ejecutado | T-083…T-092 |
| P9 — Smoke de release | ✅ Ejecutado | T-093 (rate limit 500) y T-094 (health bloqueado por Redis) |

---

## Glosario

- **As-is:** estado actual verificado del sistema.
- **To-be:** estado objetivo definido por la spec.
- **Quality gate:** condición automática o manual que bloquea el merge.
- **Expand/contract:** patrón de migración en dos pasos para cambios incompatibles.
- **KyC:** keep your changes small; cambios pequeños y reversibles.
- **RPO/RTO:** pérdida máxima de datos aceptable / tiempo máximo de recuperación.
