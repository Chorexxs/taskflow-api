# Contribuir en TaskFlow

Este documento define la política de ramas, PR, release y rollback (T-010). La
constitución del proyecto ([`specs/taskflow/constitution.md`](./specs/taskflow/constitution.md))
prevalece sobre cualquier preferencia local.

---

## 1. Flujo SDD

1. Lee la constitución y la tarea `T-###` de [`specs/taskflow/tasks.md`](./specs/taskflow/tasks.md).
2. Identifica los requisitos `FR-###`/`NFR-###` y hallazgos `BL-##` que cubre.
3. Abre una rama con el ID de la tarea.
4. Implementa el cambio **con tests** (401/403/404/422 y camino feliz cuando aplique).
5. Actualiza `spec.md`, `contracts/api.md` o `data-model.md` si cambia el comportamiento o el contrato.
6. Abre el PR referenciando `T-###` y los `FR-###`/`BL-##` cubiertos.

No se acepta código sin spec ni cambios de contrato sin actualizar la documentación.

---

## 2. Ramas

| Tipo | Patrón | Origen | Destino |
|---|---|---|---|
| Feature | `feat/T-###-descripcion-corta` | `main` | `main` |
| Fix | `fix/T-###-descripcion-corta` | `main` | `main` |
| Docs / chore | `docs/T-###-descripcion` o `chore/T-###-descripcion` | `main` | `main` |
| Hotfix de producción | `hotfix/descripcion-corta` | tag de producción | `main` |

Reglas:

- `main` es la única rama de integración y siempre debe estar desplegable.
- Una rama = una tarea = un PR pequeño y revisable.
- No se hace push directo a `main`; todo entra por PR (salvo una emergencia
  documentada en el PR de hotfix).
- Rebase sobre `main` antes de pedir revisión; no se reescribe una rama ya
  revisada sin avisar.

---

## 3. Commits

- **Siempre en español**, asunto y cuerpo.
- Conventional Commits: `tipo(alcance): resumen`.
- Tipos permitidos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`,
  `style`, `build`, `ci`.
- Asunto en imperativo, minúscula tras los dos puntos, sin punto final y ≤ 72
  caracteres.
- Cuerpo opcional explicando el qué y el porqué; referencia `T-###`, `FR-###` o
  `BL-##`.

Ejemplos:

```text
feat(tareas): anadir endpoint para cambiar solo el estado
fix(adjuntos): sanear el nombre antes de construir la ruta
docs(despliegue): documentar el rollback de Render
```

---

## 4. Pull requests

Un PR solo se mergea si cumple **todos** los quality gates de la constitución:

| Gate | Comando / evidencia |
|---|---|
| Lint y formato backend | `ruff check app tests` + `ruff format --check app tests` |
| Tipos | `mypy app` |
| Tests backend | `pytest` sobre PostgreSQL (≥ 80 % de cobertura) |
| Tests frontend | `npm run test:coverage` (≥ 70 % líneas/ramas) |
| Lint y build frontend | `npm run lint` + `npm run build` |
| Migraciones | `alembic upgrade head` + `alembic downgrade -1` |
| Seguridad | `pip-audit`, `npm audit --omit=dev`, `gitleaks` |
| Contrato | `python scripts/export_openapi.py --check` |
| Documentación | spec/contrato/modelo actualizados |

Además, el PR debe incluir:

- [ ] Referencia `T-###` y `FR-###`/`BL-##`.
- [ ] Descripción del cambio y del riesgo.
- [ ] Nota de despliegue/rollback si toca DB, auth o storage.
- [ ] Evidencia de los tests ejecutados (salida o enlace al CI).
- [ ] Sin secretos, PII ni tokens en logs o capturas.

Revisión y merge:

1. Al menos una revisión aprobatoria.
2. CI verde en el último commit.
3. **Squash merge** con el asunto del PR como mensaje final.
4. Borrar la rama tras el merge.

---

## 5. Versionado y release

- Versionado semántico `MAJOR.MINOR.PATCH` y [`CHANGELOG.md`](./CHANGELOG.md)
  siguiendo Keep a Changelog.
- `main` se despliega automáticamente: Render (API) y Vercel (frontend) escuchan
  la rama. Un merge en `main` **es** un release de producción.
- Los cambios incompatibles de API requieren `/api/v2` o un periodo de
  deprecación documentado (constitución, artículo 2).

### Procedimiento de release

1. Verifica que `main` está verde y que el CHANGELOG refleja los cambios.
2. Ejecuta `alembic upgrade head` contra la base de producción (InsForge) antes
   del deploy de la API.
3. Despliega la API (Render) y espera a `/health/ready` → `200`.
4. Despliega el frontend (Vercel) o deja que el merge lo haga.
5. Ejecuta el smoke test de producción y el de performance
   ([`specs/taskflow/release-checklist.md`](./specs/taskflow/release-checklist.md)).
6. Crea el tag `vX.Y.Z` y publica la release con las notas del CHANGELOG.
7. Monitoriza 30 minutos: 5xx, login/refresh, latencia y readiness.

### Criterios de aborto

- Errores 5xx > 5 % durante 5 minutos.
- Login o refresh fallando > 10 %.
- Migración bloqueada > 15 minutos.
- Pérdida de acceso a datos o storage.

Si se cumple cualquiera, aplica el rollback y abre un incidente.

---

## 6. Rollback

| Capa | Acción | Verificación |
|---|---|---|
| Frontend | Redeploy del deployment anterior en Vercel | La URL sirve el build previo |
| API | Redeploy del deploy anterior en Render | `/health/ready` → 200 |
| DB | `alembic downgrade -1` si la migración es reversible y no hay datos nuevos dependientes; si no, restaurar el backup verificado | `alembic current` y smoke read-only |
| Feature flag | Desactivar sin redeploy | Comportamiento previo restaurado |

Reglas:

- Toda migración debe poder revertirse; si no, se documenta y se exige backup
  verificado antes del deploy.
- El rollback de la API y de la migración se coordina: primero se revierte el
  código si la migración es compatible hacia atrás.
- Después del rollback, deja constancia en `specs/taskflow/blockers.md` o en el
  issue del incidente con la causa y la acción correctiva.

---

## 7. Hotfix de producción

1. Crea `hotfix/descripcion` desde el tag desplegado.
2. Aplica el cambio mínimo con un test de regresión.
3. PR a `main` con la etiqueta de emergencia y la justificación del gate saltado,
   si lo hubiera.
4. Tras el merge, tag `vX.Y.Z+1` y smoke test.
