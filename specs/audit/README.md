# Auditorías bajo demanda — TaskFlow

**Versión:** 1.0
**Estado:** activo
**Ámbito:** todo el repositorio (`app/`, `frontend/`, `tests/`, `alembic/`, `scripts/`, `.github/`, Docker y documentación)

Este directorio contiene dos specs de auditoría reutilizables. No son
funcionalidades del producto ni tareas del backlog: son **procedimientos de
revisión** que se ejecutan únicamente cuando el usuario lo ordena.

---

## 1. Los dos specs

| Spec | Qué audita | Cuándo usarlo |
|---|---|---|
| [`code-audit.md`](./code-audit.md) | Calidad del código, arquitectura, acoplamiento, escalabilidad, tests, contratos, datos, frontend y documentación | Antes de un release, al cerrar una fase, al revisar un PR grande o al incorporar una funcionalidad nueva |
| [`security-audit.md`](./security-audit.md) | Ciberseguridad: secretos, authn/authz, validación, uploads, dependencias, CI/CD, infraestructura y privacidad | Antes de un release, al tocar auth/upload/permisos, al rotar credenciales o ante una sospecha de incidente |

Ambos specs comparten:

- La [constitución](../taskflow/constitution.md) como norma superior.
- El flujo SDD de [`AGENTS.md`](../../AGENTS.md).
- El modelo de severidad y el requisito de evidencia verificable.
- La prohibición de modificar código durante la auditoría.

---

## 2. Contrato de autonomía (no negociable)

```yaml
execution: manual
auto_run: false
requires_explicit_user_request: true
default_mode: read-only
```

Reglas:

1. **Ningún agente ejecuta estos specs por iniciativa propia.** Encontrar este
   archivo, leer un `TODO`, ver un pipeline en rojo o detectar un hallazgo no es
   una orden de auditoría.
2. La auditoría solo comienza cuando el usuario usa una frase de activación o
   invoca el comando correspondiente.
3. La auditoría es **de solo lectura**. No se corrige código, no se actualizan
   dependencias, no se reescriben migraciones y no se hacen commits salvo que el
   usuario lo pida explícitamente en un mensaje posterior.
4. El informe se entrega en la conversación. Solo se escribe en disco si el
   usuario lo solicita.
5. Un hallazgo crítico se reporta de inmediato y detiene la auditoría si implica
   un secreto real expuesto o una vulnerabilidad explotable en producción.

### Frases de activación

| Spec | Frases válidas |
|---|---|
| Código | `audita el código`, `ejecuta la auditoría de código`, `audit code`, `/audit-code` |
| Seguridad | `audita la seguridad`, `ejecuta la auditoría de seguridad`, `audit security`, `/audit-security` |

También se aceptan variantes con alcance:

```text
audita el código de app/routers
audita la seguridad del diff de este PR
audit security full
/audit-code frontend/src
/audit-security --scope=auth,uploads
```

---

## 3. Modos de alcance

| Modo | Cuándo | Qué se revisa |
|---|---|---|
| `full` | Release o cierre de fase | Todo el repositorio |
| `path` | Módulo o feature concreta | Solo las rutas indicadas y sus dependencias directas |
| `diff` | PR o cambio local | Solo el diff contra `main`, más el contexto necesario |
| `release` | Antes de desplegar | Todo el repositorio + configuración de despliegue + migraciones |
| `incident` | Sospecha de brecha | Secretos, historial de git, accesos, dependencias y configuración |

Si el usuario no indica alcance, el valor por defecto es `full`.

---

## 4. Comandos de OpenCode

Los comandos viven en `.opencode/commands/` y solo expanden el prompt; no
ejecutan nada por sí solos:

| Comando | Efecto |
|---|---|
| `/audit-code [alcance]` | Inicia la auditoría de código según `code-audit.md` |
| `/audit-security [alcance]` | Inicia la auditoría de seguridad según `security-audit.md` |

Los comandos recuerdan al agente que la auditoría es bajo demanda y de solo
lectura.

---

## 5. Evidencia y reportes

Toda afirmación debe tener evidencia:

- Ruta y línea: `app/routers/tasks.py:235`.
- Comando ejecutado y salida relevante.
- Si es una revisión manual, el fragmento mínimo que demuestra el hallazgo.

Los informes pueden contener detalles de explotación. Por eso:

- El informe de seguridad se entrega **redactado** en la conversación.
- Los secretos se muestran solo como `****` o con los últimos 4 caracteres.
- No se commitean reportes crudos con payloads, tokens o rutas internas.
- Si el usuario pide guardar el informe, se guarda una versión saneada.

---

## 6. Relación con el SDD

| Documento | Relación |
|---|---|
| [`constitution.md`](../taskflow/constitution.md) | Norma superior; los specs de auditoría no pueden contradecirla |
| [`spec.md`](../taskflow/spec.md) | Fuente de verdad funcional; los hallazgos se mapean a `FR-*`/`NFR-*` |
| [`plan.md`](../taskflow/plan.md) | Arquitectura objetivo y ADRs; se usa como rúbrica |
| [`tasks.md`](../taskflow/tasks.md) | Los hallazgos se convierten en tareas `T-###` o se vinculan a una existente |
| [`baseline.md`](../taskflow/baseline.md) | Hallazgos históricos `BL-##`; se verifica si siguen abiertos |
| [`contracts/api.md`](../taskflow/contracts/api.md) | Contrato HTTP que la auditoría de código valida |

Un hallazgo de auditoría **no** sustituye a una tarea del backlog: si requiere
código, se registra como tarea con severidad, referencia y criterio de
aceptación.

---

## 7. Mantenimiento

- Los specs se versionan con el repositorio.
- Un cambio de stack, de arquitectura o de normativa de seguridad obliga a
  revisar el spec correspondiente.
- Las excepciones a una regla deben quedar documentadas con justificación y
  fecha, igual que en la constitución.
