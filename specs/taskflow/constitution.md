# Constitución del proyecto TaskFlow

**Versión:** 1.0
**Ámbito:** todo el repositorio (`app/`, `frontend/`, `tests/`, `alembic/`, infraestructura y documentación)
**Enmienda:** requiere PR explícito, justificación y aprobación del responsable del proyecto.

Esta constitución prevalece sobre preferencias personales y sobre la documentación histórica (`AGENTS.md`, `STACK.md`, `DECISIONS.md`) cuando haya conflicto. Si el código actual la incumple, el incumplimiento se registra en `baseline.md` y se corrige según el plan.

---

## Artículo 1 — La especificación es la fuente de verdad

1. Todo comportamiento observable debe estar descrito en `spec.md` o en `contracts/api.md`.
2. Si el código y la spec discrepan, la spec manda; el código se corrige o la spec se enmienda con justificación.
3. Ningún cambio de contrato (request, response, error, permiso o efecto secundario) se mergea sin actualizar la spec y el contrato.
4. Los documentos históricos no son fuente de verdad: se mantienen como punteros o se archivan.

**Consecuencia:** un PR que cambia comportamiento sin actualizar la spec se rechaza.

---

## Artículo 2 — Compatibilidad y versionado

1. La API pública vive bajo `/api/v1`. Los cambios incompatibles requieren `/api/v2` o un periodo de deprecación documentado.
2. Los cambios compatibles (añadir campos opcionales, endpoints nuevos) son preferibles a romper clientes.
3. Los `DELETE` deben tener semántica explícita: borrado físico, archivado lógico o desactivación. “DELETE que archiva” debe documentarse y nombrarse sin ambigüedad.
4. Los identificadores públicos preferentes son `id` numérico y `slug` estable. Los nombres/títulos no son identificadores fiables.
5. Las migraciones de base de datos son versionadas, reproducibles y reversibles.

---

## Artículo 3 — Seguridad por defecto

1. Ningún secreto se commitea. `.env*` está ignorado salvo `.env.example` sin valores reales.
2. La aplicación **falla al arrancar** si falta `SECRET_KEY` o `DATABASE_URL` en producción. No hay claves por defecto.
3. CORS usa una allowlist explícita por entorno. Nunca `allow_origins=["*"]` con `allow_credentials=True`.
4. Los tokens no viajan en query strings ni se escriben en logs.
5. Toda ruta que toca datos de un equipo verifica: usuario autenticado → miembro → rol/ownership.
6. Los uploads validan tamaño, tipo, nombre y ruta; nunca confían en `filename` del cliente.
7. Los errores no filtran stack traces, rutas internas ni datos de otros usuarios.
8. Se sigue OWASP ASVS nivel 2 como referencia mínima para autenticación, sesión, control de acceso y validación de entrada.

---

## Artículo 4 — Permisos y mínimo privilegio

1. Los permisos se definen en una matriz única (`spec.md` §Permisos) y se implementan de forma consistente.
2. `admin` puede administrar el equipo; `member` colabora según la matriz.
3. El creador de un recurso no obtiene permisos implícitos fuera de los definidos.
4. Los cambios de estado de una tarea (Kanban) no deben requerir ser creador/admin si el miembro participa en el tablero.
5. Nunca se puede dejar un equipo sin al menos un admin.
6. Las operaciones destructivas requieren confirmación explícita en UI y autorización en API.

---

## Artículo 5 — Calidad y tests

1. Todo bug se corrige con un test que falla antes del arreglo.
2. Toda funcionalidad nueva tiene tests de camino feliz, errores y permisos.
3. Los tests de integración usan PostgreSQL, no SQLite, para evitar divergencias de comportamiento.
4. Cobertura mínima objetivo: **80% backend** y **70% en flujos críticos frontend**. No es una meta cosmética: las líneas sin cubrir deben ser justificadas.
5. Los tests no dependen del orden de ejecución ni de estado compartido.
6. Los tests no llaman a servicios externos reales; se usan dobles o contenedores.

---

## Artículo 6 — Tipado, lint y formato

1. Backend: `ruff` para lint/format y `mypy` para tipado estático en `app/`.
2. Frontend: ESLint y build de producción obligatorios en CI.
3. No se mergea código con errores de lint, tipos o build.
4. Las dependencias se fijan con lockfile. Las actualizaciones se hacen por PR automatizado y con tests.
5. La versión de Python y Node está fijada y es la misma en local, CI y Docker.

---

## Artículo 7 — Observabilidad y operabilidad

1. Cada request tiene `request_id` y lo devuelve en `X-Request-ID`.
2. Los logs son estructurados (JSON), sin secretos ni PII sensible.
3. Los errores 5xx se reportan a Sentry con contexto suficiente para reproducirlos.
4. Existen endpoints de **liveness** y **readiness** separados del health informativo.
5. Las migraciones se ejecutan antes del despliegue y el rollback está documentado.
6. Toda feature que dependa de Redis, storage o email degrada de forma controlada y visible.

---

## Artículo 8 — Accesibilidad y experiencia

1. La UI cumple WCAG 2.1 AA en flujos críticos: login, dashboard, tablero, detalle de tarea.
2. Todo control es accesible por teclado; los modales atrapan el foco y se cierran con `Escape`.
3. Los estados de carga, vacío y error son explícitos; nunca se muestra una pantalla en blanco.
4. Los formularios tienen labels asociados, mensajes de error y foco en el primer error.
5. El tema claro/oscuro debe ser real o eliminarse; no se mantiene código muerto.

---

## Artículo 9 — Simplicidad y cambios reversibles

1. Se prefiere el cambio más pequeño que cumpla la spec.
2. No se añade una capa de servicios, cola, cache o realtime sin un requisito medible.
3. Las features riesgosas se despliegan tras un flag o en fases expand/contract.
4. Cada fase deja el sistema desplegable y con tests verdes.
5. Se elimina código muerto en lugar de mantenerlo “por si acaso”.

---

## Artículo 10 — Datos y privacidad

1. Fechas en UTC (`timestamptz`), serializadas en ISO 8601.
2. Borrados y retenciones tienen política documentada.
3. Los adjuntos se sirven solo a miembros autorizados; las rutas internas no se exponen.
4. No se registran contraseñas, tokens, emails completos ni contenido de archivos en logs.
5. Las copias de seguridad y restauración se prueban, no solo se contratan.

---

## Quality gates

Un PR solo puede mergearse si cumple **todos** estos gates:

| Gate | Backend | Frontend | Infra |
|---|---|---|---|
| Formato/lint | `ruff check` + `ruff format --check` | `eslint` | `hadolint` (opcional) |
| Tipos | `mypy app` | — | — |
| Tests | `pytest` con PostgreSQL | `vitest run` | smoke test |
| Cobertura | ≥ 80% | ≥ 70% flujos críticos | — |
| Migraciones | `alembic upgrade head` + `downgrade -1` | — | — |
| Seguridad | `pip-audit` + secret scan | `npm audit --omit=dev` | — |
| Contrato | OpenAPI snapshot sin cambios inesperados | — | — |
| Documentación | spec/contrato actualizados | — | runbook actualizado |

---

## No negociables (violaciones bloqueantes)

- [ ] Secretos en el repositorio o en logs.
- [ ] `SECRET_KEY` con fallback silencioso.
- [ ] CORS `*` con credenciales.
- [ ] Tokens en query string.
- [ ] `create_all` en producción.
- [ ] Upload sin sanitización de nombre/ruta.
- [ ] Endpoint sin verificación de pertenencia al equipo.
- [ ] `DELETE` con semántica ambigua.
- [ ] Merge con tests rojos o migración no reversible.
- [ ] Cambio de contrato sin actualizar la spec.

---

## Enforcement

1. **Local:** pre-commit ejecuta lint, format y tests rápidos.
2. **CI:** ejecuta todos los gates en cada push/PR a `main`.
3. **Review:** el revisor verifica trazabilidad `T-### → FR-###` y calidad de tests.
4. **Excepción:** solo el responsable del proyecto puede saltarse un gate, dejando constancia en el PR y un issue de seguimiento con fecha.
