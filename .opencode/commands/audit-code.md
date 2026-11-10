---
description: Ejecuta bajo demanda la auditoría de código, arquitectura y escalabilidad
---

Ejecuta la auditoría definida en `specs/audit/code-audit.md`.

Alcance solicitado: $ARGUMENTS

Reglas obligatorias:

- La auditoría se ejecuta ahora porque el usuario la invocó explícitamente.
- Es de solo lectura: no modifiques código, tests, configuración, dependencias, migraciones ni documentación.
- Si el alcance está vacío, audita todo el repositorio (`full`).
- Sigue el procedimiento, la severidad, el formato de hallazgo y los criterios de salida del spec.
- Toda afirmación debe llevar evidencia verificable (`ruta:línea`, comando y salida).
- No escribas el informe en disco salvo que el usuario lo pida.
- No instales herramientas ni ejecutes comandos contra producción.
- Si encuentras un hallazgo `CA-0`, repórtalo de inmediato antes de continuar.
