---
id: SPEC-AUDIT-CODE
version: 1.0
status: active
owner: TaskFlow maintainers
execution: manual
auto_run: false
requires_explicit_user_request: true
default_mode: read-only
triggers:
  - "audita el código"
  - "ejecuta la auditoría de código"
  - "audit code"
  - "/audit-code"
report_format: findings + scorecard + remediation plan
---

# SPEC-AUDIT-CODE — Auditoría de código, arquitectura y escalabilidad

**Versión:** 1.0
**Norma superior:** [`constitution.md`](../taskflow/constitution.md)
**Fuente funcional:** [`spec.md`](../taskflow/spec.md)
**Arquitectura objetivo:** [`plan.md`](../taskflow/plan.md)
**Contrato:** [`contracts/api.md`](../taskflow/contracts/api.md)

---

## 0. Contrato de ejecución

Este spec se ejecuta **solo bajo demanda**:

- `auto_run: false`. No se activa al leerlo, al encontrar deuda técnica ni al
  detectar un pipeline en rojo.
- La orden debe ser explícita: `audita el código`, `audit code` o
  `/audit-code`.
- La auditoría es **read-only**: no se modifica código, configuración,
  dependencias, migraciones ni documentación.
- Si se detecta un problema crítico, se reporta y se espera autorización antes
  de tocar nada.
- El informe se entrega en la conversación; solo se escribe en disco si el
  usuario lo pide.

---

## 1. Objetivo

Evaluar si el código actual y el código nuevo cumplen estas condiciones:

1. **Corrección:** hace lo que la spec dice, sin efectos colaterales.
2. **Arquitectura:** respeta las capas y la dirección de dependencias.
3. **Escalabilidad:** puede crecer en funcionalidad, tráfico y datos sin
   reescrituras ni cuellos de botella evitables.
4. **Mantenibilidad:** es legible, tipado, testeable y sin duplicación
   innecesaria.
5. **Consistencia:** API, datos, errores y permisos siguen un único patrón.
6. **Operabilidad:** se puede observar, desplegar, migrar y revertir.

El resultado no es una opinión: es un conjunto de hallazgos con evidencia,
severidad, impacto y propuesta de remediación.

---

## 2. Alcance

### 2.1 Incluido

| Área | Rutas |
|---|---|
| Backend | `app/**/*.py` |
| Frontend | `frontend/src/**/*.{js,jsx,css}` |
| Tests | `tests/**`, `frontend/src/test/**` |
| Migraciones | `alembic/**` |
| Scripts | `scripts/**` |
| CI/CD | `.github/workflows/**`, `Dockerfile`, `docker-compose.yml`, `Procfile` |
| Contratos | `specs/taskflow/contracts/api.md`, `specs/taskflow/contracts/openapi.json` |
| Configuración | `pyproject.toml`, `requirements.txt`, `frontend/package.json`, `.env.example` |

### 2.2 Excluido

- `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`, `uploads/`.
- Datos reales, secretos y contenido de `.env`.
- Servicios externos en producción.
- Decisiones de producto que no estén en `spec.md`.

### 2.3 Modos

| Modo | Entrada | Cobertura |
|---|---|---|
| `full` | sin argumentos | Todo el repositorio |
| `path` | `audita el código de app/routers` | Rutas indicadas + dependencias directas |
| `diff` | `audita el código de este PR` | `git diff main...HEAD` + contexto |
| `release` | `audit code release` | Todo + configuración de despliegue + migraciones |

---

## 3. Rúbrica de arquitectura

La arquitectura objetivo está en [`plan.md`](../taskflow/plan.md) §2. Se evalúa
contra estas reglas:

### 3.1 Capas y dirección de dependencias

```text
Routers  →  Services  →  CRUD/Repositories  →  Models
   │            │                │
   └────────────┴────────────────┴──→ Schemas (contratos)
```

| Regla | Qué se verifica | Violación típica |
|---|---|---|
| R1 | El router solo hace HTTP: valida entrada, resuelve dependencias, llama al servicio/CRUD y devuelve el schema | Lógica de negocio, transacciones o storage dentro del router |
| R2 | El servicio orquesta casos de uso con más de un paso | Router que crea tarea + notifica + registra actividad + sube archivo |
| R3 | El CRUD no conoce HTTP ni permisos | `HTTPException`, `Request`, códigos de estado en `crud.py` |
| R4 | Los schemas no acceden a DB | Consultas o `Session` dentro de `schemas.py` |
| R5 | Los modelos no contienen reglas de negocio | Validaciones de permisos o llamadas a servicios en `models.py` |
| R6 | La configuración es única y validada | `os.environ` disperso, settings duplicados |
| R7 | Las dependencias apuntan hacia dentro | `crud` importando routers o schemas de respuesta HTTP |

**Hallazgo automático:** `CA-1` si un router supera ~150 líneas o mezcla más de
tres responsabilidades; `CA-2` si hay `HTTPException` en CRUD o acceso a DB en
schemas.

### 3.2 Principios de diseño

| Principio | Aplicación concreta |
|---|---|
| **SRP** | Una clase/función cambia por una sola razón |
| **OCP** | Nuevas reglas se añaden sin editar cadenas de `if/elif` crecientes |
| **LSP** | Los dobles de test sustituyen a los servicios sin romper contratos |
| **ISP** | Interfaces pequeñas (`StorageService`, repositorios) |
| **DIP** | Los routers dependen de abstracciones, no de implementaciones concretas |
| **DRY** | Una sola definición de permisos, paginación, errores y slugs |
| **KISS** | La solución más simple que cumpla la spec |
| **YAGNI** | Sin capas, colas, caché o realtime sin requisito medible |

### 3.3 Módulos y tamaño

Heurísticas (no son límites duros, pero exigen justificación):

- Archivo > 600 líneas: `CA-2` (NFR-MAINT-06).
- Función > 60 líneas o > 5 parámetros: `CA-2`.
- Anidamiento > 4 niveles: `CA-2`.
- Complejidad ciclomática > 10 por función: `CA-2`.
- Duplicación de lógica de permisos, paginación o errores: `CA-1`.
- Código muerto, imports sin uso o endpoints no documentados: `CA-3`.

---

## 4. Rúbrica de escalabilidad

Una funcionalidad es escalable si cumple todos estos puntos:

### 4.1 Backend sin estado

- [ ] La API no guarda sesiones, contadores ni colas en memoria del proceso.
- [ ] El rate limiting y la caché usan un backend compartido (Redis) cuando hay
      más de una instancia.
- [ ] Los archivos no se escriben en el filesystem efímero en producción.
- [ ] Los jobs son idempotentes y pueden ejecutarse en paralelo.
- [ ] No hay locks en memoria para coordinar instancias.

### 4.2 Consultas y datos

- [ ] Toda lista está paginada con máximo 100 ítems.
- [ ] Los filtros y órdenes usados tienen índice.
- [ ] Las relaciones serializadas usan `joinedload`/`selectinload` para evitar
      N+1.
- [ ] No se cargan colecciones completas para contar; se usa `COUNT`.
- [ ] Las búsquedas escapan `%` y `_`.
- [ ] Las escrituras multi-tabla son transaccionales.
- [ ] Los borrados en cascada están definidos en DB y probados.
- [ ] Las migraciones son reversibles y usan expand/contract.

### 4.3 API y contratos

- [ ] Los endpoints nuevos tienen schema de request y response.
- [ ] Los errores usan el envelope único y códigos estables.
- [ ] Los cambios incompatibles tienen versión o deprecación.
- [ ] Los identificadores son `id`/`slug`, no nombres.
- [ ] Los `DELETE` tienen semántica explícita.
- [ ] Los endpoints son idempotentes cuando el cliente puede reintentar.
- [ ] El snapshot OpenAPI se actualiza y se revisa.

### 4.4 Rendimiento y protección

- [ ] Hay timeouts en llamadas externas.
- [ ] Hay límites de tamaño de payload y de subida.
- [ ] Hay rate limit en auth y operaciones costosas.
- [ ] Las operaciones lentas se mueven a jobs, no al request.
- [ ] No hay bucles N+1 en serialización.
- [ ] No se cachea sin invalidación definida.

### 4.5 Frontend

- [ ] El cliente API es único y centraliza auth, refresh, errores y abortos.
- [ ] Las query keys son estables y versionadas por recurso.
- [ ] Las mutaciones invalidan con la sintaxis de React Query 5.
- [ ] Los estados de carga, vacío y error están cubiertos.
- [ ] El tablero no bloquea el drag & drop por búsquedas o renderizados caros.
- [ ] La UI oculta acciones, pero nunca decide permisos.
- [ ] El diseño es responsive de 360 a 1440 px.

### 4.6 Extensibilidad

- [ ] Añadir un campo, un rol o un tipo de notificación no obliga a editar
      diez archivos.
- [ ] Las reglas de permisos viven en un único lugar.
- [ ] Los tipos de notificación y actividad están centralizados.
- [ ] El storage es una abstracción sustituible.
- [ ] Las features riesgosas pueden activarse por flag.

---

## 5. Rúbrica de calidad de código

### 5.1 Backend

- [ ] Python 3.12, tipos `X | None`, `Annotated` en dependencias.
- [ ] Imports absolutos y ordenados.
- [ ] Funciones públicas con anotación de retorno.
- [ ] Pydantic v2 con `ConfigDict`, no `class Config`.
- [ ] Sin `print`; logging estructurado con `request_id`.
- [ ] Sin secretos, PII ni tokens en logs.
- [ ] `HTTPException` con status correcto y mensaje claro.
- [ ] Sin `except Exception` silencioso.
- [ ] Sin `create_all` fuera de tests.
- [ ] Sin SQL crudo sin parametrizar.
- [ ] Sin rutas internas ni stack traces en respuestas.

### 5.2 Frontend

- [ ] Sin `console.log` de datos sensibles.
- [ ] Sin `dangerouslySetInnerHTML` sin sanitización.
- [ ] Sin tokens en URLs.
- [ ] Sin lógica de permisos como única defensa.
- [ ] Sin `any` implícito ni props sin validar.
- [ ] Componentes con `aria-label` cuando el icono no tiene texto.
- [ ] Modales con foco atrapado y cierre con `Escape`.
- [ ] Sin dependencias sin uso.

### 5.3 Tests

- [ ] Camino feliz.
- [ ] 401 sin token.
- [ ] 403 sin permiso.
- [ ] 404 recurso de otro equipo.
- [ ] 422 validación.
- [ ] Casos límite: duplicados, último admin, token expirado, archivo vacío.
- [ ] Tests deterministas, sin orden ni estado compartido.
- [ ] Sin servicios externos reales.
- [ ] Cobertura backend ≥ 80%.
- [ ] Cobertura frontend crítica ≥ 70%.

### 5.4 Documentación

- [ ] `spec.md` y `contracts/api.md` reflejan el comportamiento real.
- [ ] `data-model.md` refleja el esquema real.
- [ ] `tasks.md` marca el estado real.
- [ ] No hay referencias a stacks o proveedores inexistentes.
- [ ] Los ADRs afectados están aceptados o marcados como propuestos.

---

## 6. Severidad

| ID | Nombre | Criterio | SLA |
|---|---|---|---|
| `CA-0` | Blocker | Bug de corrección, pérdida de datos, riesgo de seguridad, ruta crítica sin test o build roto | Antes del merge/release |
| `CA-1` | Crítico | Violación de arquitectura que bloquea escalar; duplicación de permisos; N+1 en ruta caliente; contrato roto | Próximo PR |
| `CA-2` | Mayor | Deuda de mantenibilidad, falta de paginación/índice, tests débiles, archivo > 600 líneas | Sprint actual |
| `CA-3` | Menor | Estilo, nombres, docs, código muerto | Backlog |
| `CA-4` | Informativo | Sugerencia o mejora opcional | Cuando convenga |

Un hallazgo `CA-0` o `CA-1` impide declarar la auditoría como aprobada.

---

## 7. Procedimiento de ejecución

### Fase 0 — Preflight

1. Confirmar que la activación fue explícita.
2. Confirmar alcance (`full`, `path`, `diff`, `release`).
3. Leer `constitution.md`, `AGENTS.md`, `spec.md` y `plan.md`.
4. Identificar la rama, el commit y si hay cambios sin commitear.
5. Registrar el entorno: Python, Node, versiones de herramientas.
6. Anunciar el plan de auditoría en 5 líneas.

**Salida:** alcance, commit auditado y limitaciones.

### Fase 1 — Inventario

```bash
git rev-parse --short HEAD
git status --short
git ls-files
```

Recoger:

- Número de archivos y líneas por módulo.
- Endpoints y routers.
- Modelos, tablas y migraciones.
- Dependencias backend/frontend.
- Tests y cobertura.
- Jobs, middlewares y servicios externos.

### Fase 2 — Evidencia automatizada

Ejecutar lo disponible. Si una herramienta no está instalada, registrar el gap;
no instalarla sin autorización.

```bash
# Backend
python -m pytest -q --cov=app --cov-report=term-missing
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app

# Contrato y migraciones
python scripts/export_openapi.py --check
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Frontend
cd frontend
npm run lint
npm run test
npm run build
npm audit --omit=dev
```

Opcionales de complejidad y duplicación:

```bash
radon cc app -s -a
vulture app
jscpd app frontend/src
```

**Salida:** tabla de comandos, resultado y evidencia.

### Fase 3 — Arquitectura

1. Mapear routers → servicios → CRUD → modelos.
2. Buscar violaciones de capas (R1–R7).
3. Revisar tamaño, complejidad y duplicación.
4. Revisar dirección de imports.
5. Revisar configuración y settings duplicados.
6. Revisar manejo de errores y envelope.
7. Revisar permisos: una sola fuente de verdad.

### Fase 4 — Revisión por dominio

| Dominio | Preguntas clave |
|---|---|
| Auth | ¿Rotación, revocación, bloqueo, expiración y logout son coherentes? |
| Equipos | ¿Último admin, expulsión, roles y pertenencia? |
| Proyectos | ¿Slug, archivo/restauración, borrado y actividad? |
| Tareas | ¿Permisos por campo, Kanban, asignación y borrado en cascada? |
| Comentarios | ¿Pertenencia actual, paginación, menciones y notificaciones? |
| Adjuntos | ¿Streaming, MIME, nombre, storage, checksum y borrado? |
| Notificaciones | ¿Dedupe, contador, paginación y propiedad? |
| Actividad | ¿Actor, diff legible, paginación e inmutabilidad? |
| Búsqueda | ¿Escape de comodines, paginación y descripción? |
| Frontend | ¿Cliente único, refresh, query keys, estados y a11y? |

### Fase 5 — Escalabilidad

1. Revisar listas sin paginación.
2. Revisar consultas N+1 y falta de índices.
3. Revisar estado en memoria y uso de Redis.
4. Revisar escrituras no transaccionales.
5. Revisar jobs y borrados en cascada.
6. Revisar límites de payload, upload y rate limit.
7. Revisar timeouts y degradación controlada.

### Fase 6 — Tests

1. Mapear cada `FR-*` tocado a un test.
2. Buscar rutas sin test de 401/403/404/422.
3. Revisar calidad de asserts y aislamiento.
4. Revisar cobertura real, no solo el número global.
5. Revisar tests de migración y contrato.

### Fase 7 — Documentación y trazabilidad

1. Contrastar `spec.md` contra el código.
2. Contrastar `contracts/api.md` y `openapi.json`.
3. Contrastar `data-model.md` contra modelos y migraciones.
4. Revisar `tasks.md` contra el estado real.
5. Detectar ADRs sin aceptar.

### Fase 8 — Informe

Producir:

1. Resumen ejecutivo (3–5 líneas).
2. Tabla de comandos y resultados.
3. Hallazgos ordenados por severidad.
4. Scorecard.
5. Plan de remediación priorizado.
6. Riesgos residuales y limitaciones.

### Fase 9 — Verificación

Si el usuario pide corregir:

1. Cada hallazgo debe tener un test que falle antes.
2. Ejecutar de nuevo los comandos de la fase 2.
3. Re-auditar solo los hallazgos corregidos.
4. Actualizar el estado del hallazgo, no borrarlo.

---

## 8. Formato de hallazgo

```markdown
### CA-<n> — <título corto>

- **Severidad:** CA-0 | CA-1 | CA-2 | CA-3 | CA-4
- **Ubicación:** `ruta/archivo.py:línea`
- **Dimensión:** arquitectura | escalabilidad | corrección | tests | datos | API | frontend | docs
- **Evidencia:** comando + salida o fragmento mínimo
- **Impacto:** qué se rompe, qué se degrada o qué se vuelve difícil de escalar
- **Remediación:** cambio concreto y mínimo
- **Test requerido:** qué test demuestra la corrección
- **Referencias:** `FR-*`, `NFR-*`, `BL-##`, `T-###`, ADR
- **Esfuerzo:** XS | S | M | L
- **Estado:** abierto | en progreso | corregido | aceptado como riesgo
```

Reglas:

- Un hallazgo = un problema. No agrupar cosas distintas.
- Sin evidencia no es un hallazgo; es una hipótesis y se marca como tal.
- No se acepta “está mal” sin explicar el impacto.
- Los riesgos aceptados requieren justificación y fecha.

---

## 9. Scorecard

Puntuar de 0 a 5 cada dimensión. El promedio no sustituye a los hallazgos: un
solo `CA-0` bloquea aunque el promedio sea alto.

| Dimensión | 0–5 | Criterio |
|---|---:|---|
| Arquitectura y capas | | Respeta R1–R7 y la dirección de dependencias |
| Escalabilidad | | Sin estado en memoria, paginación, índices, jobs |
| Corrección | | Cumple la spec y los casos límite |
| Manejo de errores | | Envelope, status y mensajes consistentes |
| Datos y migraciones | | Reversibles, constraints, transacciones |
| Tests | | Cobertura y casos de permiso/validación |
| Contratos/API | | OpenAPI, versionado, semántica HTTP |
| Frontend | | Cliente único, estados, a11y, responsive |
| Observabilidad | | Logs, request_id, health, Sentry |
| Documentación | | Sin drift spec/código |

**Umbrales:**

- PR normal: promedio ≥ 3.5 y ningún `CA-0`.
- Release: promedio ≥ 4.0, ningún `CA-0`/`CA-1` abierto.
- Un `CA-0` o `CA-1` debe tener tarea y fecha antes de aprobar.

---

## 10. Criterios de salida

La auditoría se considera aprobada cuando:

- [ ] No hay `CA-0` ni `CA-1` abiertos.
- [ ] `pytest` verde y cobertura ≥ 80%.
- [ ] `ruff check` y `ruff format --check` verdes.
- [ ] `mypy app` verde.
- [ ] `npm run lint`, `npm run test` y `npm run build` verdes.
- [ ] `alembic upgrade head` + `downgrade -1` verdes.
- [ ] OpenAPI snapshot al día.
- [ ] No hay listas sin paginación en rutas públicas.
- [ ] No hay N+1 en rutas calientes.
- [ ] Cada `FR-*` tocado tiene test.
- [ ] No hay drift entre spec, contrato y código.
- [ ] Scorecard ≥ 4.0 en modo release.

Si no se cumple, la auditoría queda **rechazada** con el plan de remediación.

---

## 11. Prohibiciones durante la auditoría

- No modificar código, tests, configuración ni migraciones.
- No instalar dependencias sin autorización.
- No ejecutar migraciones contra producción.
- No hacer `git push`, `commit` ni abrir PRs.
- No inventar evidencia ni afirmar que un comando pasó sin ejecutarlo.
- No ocultar hallazgos por no bloquear el release.
- No mezclar una auditoría con una remediación: son fases separadas.

---

## 12. Integración con CI

El CI puede ejecutar el subconjunto automatizado de este spec:

| Gate | Comando | Bloquea |
|---|---|---|
| Tests backend | `pytest --cov=app --cov-fail-under=80` | Sí |
| Lint backend | `ruff check` + `ruff format --check` | Sí |
| Tipos | `mypy app` | Sí |
| Tests frontend | `npm run test` | Sí |
| Build frontend | `npm run build` | Sí |
| Migraciones | `alembic upgrade head` + `downgrade -1` | Sí |
| Contrato | `python scripts/export_openapi.py --check` | Sí |
| Seguridad de deps | `pip-audit` + `npm audit --omit=dev` | Sí |

La auditoría completa (`full`/`release`) sigue siendo manual y bajo demanda.

---

## 13. Trazabilidad

Cada hallazgo debe mapearse a:

- Un requisito `FR-*` o `NFR-*` de [`spec.md`](../taskflow/spec.md).
- Un hallazgo histórico `BL-##` de [`baseline.md`](../taskflow/baseline.md) si
  aplica.
- Una tarea `T-###` de [`tasks.md`](../taskflow/tasks.md) o una tarea nueva.
- Un ADR de [`plan.md`](../taskflow/plan.md) si la remediación cambia una
  decisión de arquitectura.

---

## Anexo A — Checklist de funcionalidad nueva

Antes de considerar terminada una feature:

- [ ] Tiene `FR-*`, `T-###` y criterio de aceptación.
- [ ] Tiene contrato de request/response/error.
- [ ] Tiene permiso definido en la matriz.
- [ ] Tiene validación Pydantic.
- [ ] Tiene servicio si hay más de un paso.
- [ ] Tiene consulta paginada e indexada si lista.
- [ ] Tiene transacción si escribe en varias tablas.
- [ ] Tiene migración reversible si toca DB.
- [ ] Tiene tests de camino feliz, 401, 403, 404, 422 y límites.
- [ ] Tiene logs sin PII y con `request_id`.
- [ ] Tiene manejo de errores del cliente.
- [ ] Tiene estados de carga, vacío y error en UI.
- [ ] Tiene a11y y responsive si toca UI.
- [ ] Actualiza `spec.md`, `contracts/api.md` o `data-model.md`.
- [ ] Pasa lint, tipos, tests, build y snapshot OpenAPI.

---

## Anexo B — Anti-patrones específicos de TaskFlow

| Anti-patrón | Por qué es un problema | Corrección |
|---|---|---|
| `HTTPException` dentro de `crud.py` | Mezcla persistencia con HTTP | Excepción de dominio o retorno `None` |
| `os.environ` disperso | Configuración no validada | Usar `settings` |
| `create_all` en producción | Deriva de esquema | Alembic |
| Listas sin `page`/`page_size` | No escala | Paginación uniforme |
| `ilike(f"%{q}%")` sin escape | Comodines inesperados | Escapar `%` y `_` |
| `file.filename` en rutas | Path traversal | Sanitizar + clave única |
| Confiar en `file.size` | Bypass de límite | Contar en streaming |
| Permisos duplicados en routers | Inconsistencia | Dependencia única |
| `invalidateQueries([...])` | No invalida en React Query 5 | `{ queryKey: [...] }` |
| `localStorage` para permisos | Manipulable | La API decide |
| Estado en memoria para rate limit | No sirve multi-instancia | Redis |
| `except Exception: pass` | Oculta fallos | Loggear y propagar |
| Retornar `file_path`/`storage_key` | Fuga de implementación | Schema público mínimo |
| `DELETE` que archiva sin documentar | Contrato ambiguo | Nombrar `/archive` o documentar |
