---
description: Ejecuta bajo demanda la auditoría de ciberseguridad y secretos
---

Ejecuta la auditoría definida en `specs/audit/security-audit.md`.

Alcance solicitado: $ARGUMENTS

Reglas obligatorias:

- La auditoría se ejecuta ahora porque el usuario la invocó explícitamente.
- Es de solo lectura: no modifiques código, configuración, credenciales ni historial de git.
- Si el alcance está vacío, audita todo el repositorio (`full`).
- Sigue el modelo de amenazas, el procedimiento, la severidad y los criterios de salida del spec.
- Nunca muestres un secreto completo: redáctalo (`****` o últimos 4 caracteres).
- No ataques producción, no exfiltres datos y no ejecutes payloads destructivos.
- No instales herramientas ni rotes credenciales sin autorización.
- Si encuentras un secreto real o un `SEC-0`, detente, redacta y reporta de inmediato.
- No escribas el informe en disco salvo que el usuario lo pida.
