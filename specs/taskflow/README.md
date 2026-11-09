# TaskFlow — Paquete SDD (Spec-Driven Development)

**Versión:** 1.0 — Draft para revisión
**Fecha:** 2026-11-09
**Proyecto:** TaskFlow API
**Alcance del ciclo:** documentación + bugs conocidos + modernización completa
**Estado:** P0 parcial (specs/docs/LICENSE/baseline) y P1 (correcciones críticas) ejecutado; P2 pendiente

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

Estas decisiones no bloquean P0/P1, pero sí el resto del plan. Se proponen valores por defecto y cada una tiene un ADR asociado.

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
| P0 — Gobernanza | 🟡 Parcial | Specs en el repo, documentación alineada, LICENSE y baseline. Pendientes: labels/milestones, aceptación formal de ADRs, pre-commit y staging |
| P1 — Correcciones críticas | ✅ Ejecutado | Refresh, logout, uploads, permisos de equipo, CORS, secret fail-fast, Kanban, cliente API, Sentry, Alembic |
| P2 — Auth/sesión | 🟡 Parcial | Auto-refresh implementado; pendientes cookies/ADR-001, rate limit Redis y limpieza de tokens |
| P3 — API/datos | ⏳ Pendiente | IDs/slugs, paginación, errores, permisos, borrados |
| P4 — Colaboración/storage | ⏳ Pendiente | S3, notificaciones, SSE |
| P5 — Frontend | ⏳ Pendiente | A11y, tema, tests de flujos |
| P6 — Ops/release | ⏳ Pendiente | Ruff/mypy, CI completo, runbook |
| P7 — Realtime | ⏳ Opcional | SSE endurecido |

---

## Glosario

- **As-is:** estado actual verificado del sistema.
- **To-be:** estado objetivo definido por la spec.
- **Quality gate:** condición automática o manual que bloquea el merge.
- **Expand/contract:** patrón de migración en dos pasos para cambios incompatibles.
- **KyC:** keep your changes small; cambios pequeños y reversibles.
- **RPO/RTO:** pérdida máxima de datos aceptable / tiempo máximo de recuperación.
