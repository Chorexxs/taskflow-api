---
id: SPEC-AUDIT-SEC
version: 1.0
status: active
owner: TaskFlow maintainers
execution: manual
auto_run: false
requires_explicit_user_request: true
default_mode: read-only
triggers:
  - "audita la seguridad"
  - "ejecuta la auditoría de seguridad"
  - "audit security"
  - "/audit-security"
report_format: findings + risk matrix + remediation plan
---

# SPEC-AUDIT-SEC — Auditoría de ciberseguridad

**Versión:** 1.0
**Norma superior:** [`constitution.md`](../taskflow/constitution.md)
**Requisitos:** [`spec.md`](../taskflow/spec.md) §9 (NFR-SEC-01…07)
**Contrato:** [`contracts/api.md`](../taskflow/contracts/api.md)
**Modelo de datos:** [`data-model.md`](../taskflow/data-model.md)

---

## 0. Contrato de ejecución

Este spec se ejecuta **solo bajo demanda**:

- `auto_run: false`. No se activa al leerlo, al ver una dependencia vulnerable ni
  al detectar un secreto.
- La orden debe ser explícita: `audita la seguridad`, `audit security` o
  `/audit-security`.
- La auditoría es **read-only**: no se corrige código, no se rotan credenciales y
  no se reescribe el historial sin autorización.
- No se ataca producción, no se exfiltran datos y no se ejecutan payloads
  destructivos.
- Si se encuentra un secreto real o una vulnerabilidad explotable, se detiene la
  auditoría, se reporta de inmediato y se espera instrucción.

---

## 1. Objetivo

Verificar que TaskFlow:

1. **No filtra secretos** en código, historial, logs, artefactos, CI ni
   respuestas.
2. **Autentica y autoriza correctamente** cada operación.
3. **Valida toda entrada** y trata toda salida como no confiable.
4. **No es vulnerable** a las clases de fallo de OWASP Top 10, OWASP API Top 10
   y CWE Top 25.
5. **Protege datos y privacidad** en tránsito, en reposo y en logs.
6. **Tiene una cadena de suministro** controlada (dependencias, imágenes, CI).
7. **Puede detectar, contener y recuperarse** de un incidente.

---

## 2. Normas de referencia

| Norma | Uso |
|---|---|
| OWASP ASVS 4.0.3 nivel 2 | Base de verificación de auth, sesión, acceso y validación |
| OWASP Top 10 (2021) | Clasificación de riesgos web |
| OWASP API Security Top 10 (2023) | BOLA, BFLA, mass assignment, consumo de recursos |
| CWE Top 25 | Identificación técnica de debilidades |
| NIST SSDF (SP 800-218) | Prácticas de desarrollo seguro |
| CIS Docker Benchmark | Endurecimiento de contenedores |
| CVSS 4.0 | Puntuación opcional de severidad |

La constitución exige ASVS L2 como mínimo. Este spec no rebaja esa exigencia.

---

## 3. Alcance

### 3.1 Incluido

| Superficie | Qué se revisa |
|---|---|
| Código backend | `app/**/*.py` |
| Código frontend | `frontend/src/**/*.{js,jsx}` |
| Configuración | `.env.example`, `app/config.py`, `alembic.ini`, `Dockerfile`, `docker-compose.yml` |
| Dependencias | `requirements.txt`, `frontend/package.json`, `package-lock.json` |
| CI/CD | `.github/workflows/**`, secretos, permisos, acciones |
| Git | Archivos versionados e historial completo |
| API | Auth, permisos, validación, errores, headers, CORS |
| Datos | Esquema, backups, retención, PII |
| Despliegue | Render, Vercel, InsForge (configuración, no explotación) |
| Agentes/IA | `.opencode/`, `.agents/`, `.mcp.json`, `skills-lock.json` (riesgo de secretos y prompts) |

### 3.2 Excluido

- Explotación activa contra producción.
- Denegación de servicio real.
- Ingeniería social.
- Acceso a datos de otros usuarios.
- Pentesting de infraestructura sin autorización escrita.
- Rotación de credenciales sin aprobación del responsable.

### 3.3 Modos

| Modo | Entrada | Cobertura |
|---|---|---|
| `full` | sin argumentos | Todo el repositorio y configuración |
| `path` | `audita la seguridad de app/routers` | Rutas indicadas + flujo de datos |
| `diff` | `audita la seguridad de este PR` | `git diff main...HEAD` + contexto |
| `release` | `audit security release` | Todo + despliegue + secretos + dependencias |
| `incident` | `audit security incident` | Secretos, historial, accesos, dependencias, logs |

---

## 4. Modelo de amenazas

### 4.1 Activos

| Activo | Por qué importa |
|---|---|
| Credenciales de usuarios | Suplantación, acceso a equipos |
| Access/refresh tokens | Sesión completa |
| `SECRET_KEY` | Falsificación de tokens |
| `DATABASE_URL` y contraseña | Acceso total a datos |
| Claves de InsForge/Render/Vercel | Despliegue, DB y storage |
| Adjuntos | Malware, fuga de información |
| PII (email, nombre) | Privacidad y cumplimiento |
| Historial de actividad | Integridad y auditoría |
| Backups | Recuperación y exposición |

### 4.2 Actores

| Actor | Capacidad |
|---|---|
| Anónimo | Registro, login, endpoints públicos |
| Miembro | Acceso a su equipo y recursos |
| Admin | Gestión de miembros, proyectos y ajustes |
| Ex-miembro | Conserva token hasta expirar |
| Atacante con XSS | Robo de tokens en `localStorage` |
| Atacante con token robado | Acceso hasta revocación |
| Uploader malicioso | Archivos peligrosos o path traversal |
| Insider | Acceso legítimo mal usado |
| Dependencia comprometida | Ejecución en build o runtime |

### 4.3 Fronteras de confianza

```text
Navegador  ──HTTPS──▶  API FastAPI  ──TLS──▶  PostgreSQL (InsForge)
    │                       │
    │                       ├──▶ Storage (DB/local/S3)
    │                       ├──▶ Redis (rate limit/cache)
    │                       └──▶ Sentry
    │
    └──▶ Vercel (build estático)

GitHub Actions ──secrets──▶ Render / Vercel / InsForge
```

### 4.4 STRIDE

| Amenaza | Ejemplo en TaskFlow | Control |
|---|---|---|
| **S**poofing | Token falsificado si `SECRET_KEY` es débil | Secreto fuerte, fail-fast, expiración |
| **T**ampering | Modificar `assigned_to` o rol sin permiso | Authz en servidor, schemas |
| **R**epudiation | Borrar tarea sin actividad | Activity log inmutable |
| **I**nformation disclosure | `file_path`, stack traces, PII en logs | Schemas mínimos, errores seguros |
| **D**enial of service | Upload gigante, lista sin paginar | Límites, paginación, rate limit |
| **E**levation of privilege | Member expulsa admin o edita tarea ajena | Matriz de permisos y tests |

---

## 5. Regla de oro de secretos

> **Un secreto commiteado se considera comprometido, aunque se borre en el
> commit siguiente. Primero se rota; después se limpia el historial.**

### 5.1 Qué es un secreto

- `SECRET_KEY`, `JWT_SECRET`, claves de firma.
- `DATABASE_URL` con usuario/contraseña.
- `REDIS_URL` con contraseña.
- `SENTRY_DSN` si permite escritura/lectura.
- Tokens de Render, Vercel, GitHub, InsForge (`ik_`, `uak_`), npm, PyPI.
- Claves AWS (`AKIA…`), GCP, Azure, Stripe (`sk_live_…`), OpenAI (`sk-…`).
- Claves privadas (`-----BEGIN … PRIVATE KEY-----`).
- Cookies de sesión y tokens JWT reales (`eyJ…`).
- Credenciales de prueba que apunten a servicios reales.

### 5.2 Dónde no debe haber secretos

| Lugar | Regla |
|---|---|
| Código fuente | Nunca |
| `.env.example` | Solo placeholders |
| Tests y fixtures | Solo valores falsos evidentes |
| `Dockerfile` | Nunca en `ARG`, `ENV` ni capas |
| `docker-compose.yml` | Variables, no valores reales |
| CI | `secrets.*`, nunca `echo` |
| Frontend `VITE_*` | Son públicas: nunca un secreto |
| Logs | Nunca, ni redactados parcialmente |
| Respuestas de error | Nunca |
| Historial de git | Nunca |
| Issues/PRs/comentarios | Nunca |
| Capturas y reportes | Redactar |

### 5.3 Patrones prohibidos

```text
SECRET_KEY=<valor real>
DATABASE_URL=postgresql://user:<password>@host/db
postgres://user:<password>@host/db
redis://:<password>@host
ik_<project-key>
uak_<user-key>
ghp_<github-token>
github_pat_<token>
sk-<openai-key>
AKIA<aws-key>
-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----
Authorization: Bearer eyJ...
```

### 5.4 Procedimiento si se encuentra un secreto

1. **Detener** la auditoría y no copiar el valor completo.
2. **Redactar** en el informe: `****` o últimos 4 caracteres.
3. **Determinar** si es real, de producción, de test o un placeholder.
4. **Rotar/revocar** inmediatamente con el proveedor.
5. **Revisar accesos** y logs del servicio afectado.
6. **Limpiar el historial** con `git filter-repo` o BFG, coordinando force-push.
7. **Añadir guardrail**: gitleaks en pre-commit y CI.
8. **Documentar** el incidente y la causa raíz.

Si el secreto está en producción, la rotación tiene prioridad sobre cualquier
otro paso.

---

## 6. Checklist de seguridad

### 6.1 Secretos y configuración

- [ ] `.env` y variantes están en `.gitignore` y no están versionados.
- [ ] `.env.example` solo contiene placeholders.
- [ ] `git ls-files` no incluye `.env`, claves, certificados ni credenciales.
- [ ] El historial de git no contiene secretos.
- [ ] `SECRET_KEY` no tiene fallback en producción.
- [ ] `DATABASE_URL` es obligatoria en producción.
- [ ] `CORS_ORIGINS` es una allowlist explícita.
- [ ] No hay `allow_origins=["*"]` con credenciales.
- [ ] Los secretos de CI usan `secrets.*` y están enmascarados.
- [ ] Las variables `VITE_*` no contienen secretos.
- [ ] Los logs no imprimen configuración sensible.

### 6.2 Autenticación

- [ ] Contraseña 8–128, sin caracteres de control.
- [ ] Hash con bcrypt, nunca texto plano.
- [ ] Access 15 min; refresh 7 días.
- [ ] Refresh viaja en body, nunca en query string.
- [ ] Refresh rota en cada uso.
- [ ] Reutilización de refresh revoca la familia.
- [ ] Logout revoca access y refresh; es idempotente.
- [ ] Cambio de contraseña revoca todas las sesiones.
- [ ] Bloqueo tras 5 fallos durante 15 min.
- [ ] Contador se resetea en login exitoso.
- [ ] Rate limit en register/login/refresh.
- [ ] Errores de auth genéricos, sin enumerar usuarios.
- [ ] `WWW-Authenticate: Bearer` en 401.
- [ ] Tokens no se escriben en logs.
- [ ] Tokens no aparecen en URLs ni referrers.
- [ ] `SECRET_KEY` rotable con procedimiento documentado.

### 6.3 Autorización

- [ ] Cada ruta verifica autenticación → pertenencia → rol/ownership.
- [ ] Un recurso de otro equipo responde 404, no 403.
- [ ] Un usuario autenticado sin rol responde 403.
- [ ] BOLA/IDOR: no se confía en IDs del cliente.
- [ ] BFLA: no se confía en roles del cliente.
- [ ] Mass assignment: solo campos permitidos por schema.
- [ ] El último admin no puede salir ni degradarse.
- [ ] Un member no puede expulsar a un admin.
- [ ] Un ex-miembro no conserva acceso a comentarios/adjuntos.
- [ ] La UI oculta acciones, pero la API decide.
- [ ] Tests 401/403/404 por endpoint.

### 6.4 Entrada y salida

- [ ] Pydantic valida tipo, longitud, rango y enums.
- [ ] Se rechazan caracteres de control.
- [ ] Se escapan `%` y `_` en búsquedas.
- [ ] SQLAlchemy parametriza; no hay SQL crudo concatenado.
- [ ] React escapa por defecto; no hay `dangerouslySetInnerHTML`.
- [ ] CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
      `Referrer-Policy` y `Permissions-Policy`.
- [ ] Los errores no filtran stack traces, rutas internas ni SQL.
- [ ] Los schemas de respuesta no exponen `file_path`, `storage_key`, hashes ni
      secretos.
- [ ] No hay open redirect ni SSRF sin allowlist.

### 6.5 Uploads

- [ ] Límite de tamaño aplicado en streaming.
- [ ] Allowlist de extensión y MIME.
- [ ] Verificación de magic bytes (si aplica).
- [ ] Nombre saneado; nunca `file.filename` directo.
- [ ] Clave única; no se sobrescriben archivos.
- [ ] Ruta resuelta contenida en el directorio permitido.
- [ ] `Content-Disposition` con nombre saneado.
- [ ] Descarga solo para miembros autorizados.
- [ ] No se ejecuta ni se sirve como HTML.
- [ ] Borrado de tarea/proyecto elimina el objeto.
- [ ] Checksum y metadatos en DB.
- [ ] Antivirus/cuarentena evaluado para producción.

### 6.6 Datos y privacidad

- [ ] TLS en tránsito; `DB_SSLMODE=require` en producción.
- [ ] Backups cifrados y restore probado.
- [ ] Retención documentada (tokens 7 d, notificaciones 90 d, actividad 1 año).
- [ ] Logs sin contraseñas, tokens, emails completos ni contenido de archivos.
- [ ] Sentry con `send_default_pii=False` y scrubbing.
- [ ] Acceso a DB con mínimo privilegio.
- [ ] Adjuntos solo para miembros del equipo.
- [ ] Borrado de cuenta/datos evaluado (fuera de alcance actual).
- [ ] No se usan datos reales en tests.

### 6.7 Dependencias y cadena de suministro

- [ ] Versiones fijadas en backend y frontend.
- [ ] Lockfiles commiteados.
- [ ] `pip-audit` sin críticos/altos.
- [ ] `npm audit --omit=dev` sin críticos/altos.
- [ ] Renovate/Dependabot activo.
- [ ] Dependencias sin mantenimiento evaluadas.
- [ ] Docker base actualizada y non-root.
- [ ] Imagen sin secretos en capas.
- [ ] Acciones de GitHub fijadas por SHA o versión mayor confiable.
- [ ] Permisos de CI mínimos (`permissions: contents: read`).
- [ ] Sin `pull_request_target` con secretos.
- [ ] SBOM o inventario de dependencias (deseable).

### 6.8 Frontend

- [ ] Tokens en `localStorage` evaluados como riesgo XSS (ADR-001).
- [ ] CSP compatible con Vite/Vercel.
- [ ] Sin secretos en `VITE_*`.
- [ ] Sin `dangerouslySetInnerHTML` sin sanitizar.
- [ ] Sin `eval`, `new Function` ni scripts dinámicos.
- [ ] Errores de API no se muestran con detalles internos.
- [ ] Source maps de producción evaluados.
- [ ] Dependencias auditadas.
- [ ] Logout limpia tokens y queries.

### 6.9 Operación e incidentes

- [ ] `/health/live` y `/health/ready` no filtran detalles sensibles.
- [ ] Rate limit con Redis para multi-instancia.
- [ ] Alertas de 5xx, login fallido y readiness.
- [ ] Eventos de auth auditados sin PII.
- [ ] Runbook de incidente y rotación de secretos.
- [ ] Backups y restore documentados.
- [ ] Revisión de accesos a Render/Vercel/InsForge.

---

## 7. Severidad

| ID | Nombre | Ejemplos | SLA |
|---|---|---|---|
| `SEC-0` | Crítico | Secreto real commiteado; bypass de auth; RCE; SQLi; path traversal de escritura; acceso masivo a datos; SSRF a metadata | Inmediato |
| `SEC-1` | Alto | IDOR/BOLA explotable; XSS con robo de token; subida peligrosa; falta de authz en ruta sensible; dependencia crítica explotable | 24–72 h |
| `SEC-2` | Medio | Headers incompletos; errores verbosos; rate limit ausente en ruta no crítica; dependencia alta no explotable; CORS laxo en no producción | Sprint actual |
| `SEC-3` | Bajo | Hardening, logs mejorables, configuración defensiva ausente | Backlog |
| `SEC-4` | Info | Observación o buena práctica opcional | Cuando convenga |

Reglas:

- Un `SEC-0` detiene la auditoría y exige respuesta inmediata.
- Un `SEC-1` bloquea el release.
- La severidad se basa en impacto + explotabilidad + exposición, no solo en el
  tipo de CWE.
- Si hay duda, se sube la severidad y se justifica.

---

## 8. Procedimiento de ejecución

### Fase 0 — Autorización y preflight

1. Confirmar activación explícita y alcance.
2. Confirmar que no se atacará producción.
3. Leer `constitution.md`, `spec.md` §9, `AGENTS.md` y `contracts/api.md`.
4. Registrar commit, rama y entorno.
5. Enumerar activos y superficies incluidas.
6. Anunciar el plan y las limitaciones.

### Fase 1 — Inventario y flujo de datos

1. Listar endpoints y quién puede llamarlos.
2. Listar entradas controladas por el usuario.
3. Listar salidas que reflejan datos.
4. Listar integraciones externas y secretos que usan.
5. Dibujar el flujo token → API → DB/storage.
6. Identificar datos personales y archivos.

### Fase 2 — Escaneo de secretos

```bash
# Archivos versionados
git ls-files

# Buscar solo nombres de archivo: -l evita imprimir valores en claro
git grep -lE '(SECRET_KEY|DATABASE_URL|API_KEY|TOKEN|PASSWORD|PRIVATE KEY|ik_|uak_|ghp_|github_pat_|AKIA|sk-)'

# Herramientas dedicadas (si están instaladas)
gitleaks detect --source . --no-git --redact
gitleaks detect --source . --log-opts="--all" --redact
# Si se usa trufflehog, redirigir a un archivo temporal FUERA del repo y
# redactar antes de reportar.
trufflehog filesystem . --only-verified --json > ../trufflehog-report.json
```

> No pegar la salida cruda de ningún escáner en el informe. Revisar el archivo
> local y reportar solo la ubicación y el tipo de secreto, nunca el valor.

Revisar además:

- `.env.example`, `Dockerfile`, `docker-compose.yml`, CI.
- Configuración de Render/Vercel/InsForge (sin exponer valores).
- `.opencode/`, `.agents/`, `.mcp.json`, `skills-lock.json`.
- Historial de git completo.

### Fase 3 — Análisis estático

```bash
# Python
pip-audit -r requirements.txt
bandit -r app
semgrep --config auto app

# Frontend
cd frontend
npm audit --omit=dev --audit-level=high

# Contenedor e infraestructura
hadolint Dockerfile
trivy fs .
```

Si una herramienta no está instalada, se registra como gap de tooling y se
propone su instalación; no se instala sin autorización.

### Fase 4 — Revisión manual por dominio

| Dominio | Qué se revisa |
|---|---|
| Auth | Registro, login, refresh, logout, bloqueo, cambio de contraseña, revocación |
| Autorización | Matriz de permisos, BOLA/BFLA, pertenencia, último admin, ex-miembros |
| Uploads | Tamaño, MIME, extensión, nombre, ruta, storage, descarga, borrado |
| DB | SQLi, constraints, transacciones, migraciones, backups |
| API | Errores, headers, CORS, rate limit, paginación, mass assignment |
| Frontend | XSS, tokens, CSP, dependencias, errores |
| Config | Secretos, fail-fast, TLS, CORS, exposición de docs/health |
| CI/CD | Permisos, secretos, acciones, artefactos |

### Fase 5 — Verificación dinámica local

Solo contra `localhost`, tests o un entorno de staging autorizado:

- [ ] Sin token → 401.
- [ ] Token de otro usuario/equipo → 404.
- [ ] Member intentando acción de admin → 403.
- [ ] Último admin intentando salir → 409.
- [ ] Refresh reutilizado → 401 y familia revocada.
- [ ] Access expirado → 401.
- [ ] Upload con `../../evil` → sin escritura fuera del storage.
- [ ] Upload > límite → 413.
- [ ] MIME no permitido → 415.
- [ ] Búsqueda con `%`/`_` → literales.
- [ ] Error inesperado → envelope sin stack trace.
- [ ] CORS origen no permitido → sin cabecera.
- [ ] Rate limit → 429 con `Retry-After`.
- [ ] Headers de seguridad presentes.

No usar payloads destructivos. No atacar Render, Vercel ni InsForge reales.

### Fase 6 — Informe

Producir:

1. Resumen ejecutivo con riesgo global.
2. Tabla de hallazgos por severidad.
3. Evidencia redactada.
4. Matriz de riesgo (probabilidad × impacto).
5. Plan de remediación con orden y esfuerzo.
6. Riesgos aceptados con justificación.
7. Limitaciones de la auditoría.

### Fase 7 — Remediación y verificación

Si el usuario autoriza corregir:

1. Un test que reproduzca el fallo antes del cambio.
2. Corrección mínima.
3. Re-ejecutar el test y los escaneos.
4. Re-auditar el hallazgo.
5. Actualizar el estado, no borrar el hallazgo.

---

## 9. Formato de hallazgo

```markdown
### SEC-<n> — <título corto>

- **Severidad:** SEC-0 | SEC-1 | SEC-2 | SEC-3 | SEC-4
- **Categoría:** OWASP A0X / API0X / CWE-XXX
- **Ubicación:** `ruta/archivo.py:línea`
- **Activo afectado:** token | DB | PII | storage | CI | otro
- **Evidencia:** comando/salida o fragmento mínimo, con secretos redactados
- **Explotabilidad:** remota/local, autenticado/no, requisitos
- **Impacto:** confidencialidad, integridad, disponibilidad o cumplimiento
- **Reproducción:** pasos mínimos en entorno local/staging
- **Remediación:** cambio concreto
- **Test de regresión:** qué test lo demuestra
- **Referencias:** `NFR-SEC-*`, `FR-*`, `BL-##`, `CWE-*`, `OWASP-*`
- **Estado:** abierto | en progreso | corregido | aceptado como riesgo
```

Reglas:

- Nunca incluir el valor completo de un secreto.
- No incluir payloads que puedan causar daño si se copian y ejecutan.
- Un hallazgo = una debilidad.
- Sin evidencia no es un hallazgo; es una hipótesis.
- Los falsos positivos se documentan como revisados.

---

## 10. Criterios de salida

La auditoría se considera aprobada cuando:

- [ ] 0 hallazgos `SEC-0` y `SEC-1` abiertos.
- [ ] Escaneo de secretos limpio en archivos e historial.
- [ ] `pip-audit` y `npm audit` sin críticos/altos.
- [ ] 100% de endpoints con test de autorización.
- [ ] Matriz de permisos verificada.
- [ ] Uploads con tests de traversal, tamaño, MIME y borrado.
- [ ] Refresh con tests de expiración, revocación y reutilización.
- [ ] Headers de seguridad verificados.
- [ ] CORS allowlist verificado.
- [ ] Rate limit verificado en auth.
- [ ] Errores sin fuga de información.
- [ ] Logs sin PII ni secretos.
- [ ] Dependencias fijadas y lockfiles presentes.
- [ ] CI con permisos mínimos y secretos enmascarados.
- [ ] Runbook de incidente y rotación documentado.
- [ ] Riesgos aceptados con justificación y fecha.

Si no se cumple, la auditoría queda **rechazada** con el plan de remediación.

---

## 11. Reglas de engagement

### Permitido

- Revisar código, configuración e historial.
- Ejecutar escáneres locales.
- Probar en `localhost`, tests o staging autorizado.
- Crear pruebas de concepto mínimas y no destructivas.
- Reportar con evidencia redactada.

### Prohibido

- Atacar producción o servicios de terceros.
- Extraer, copiar o publicar datos reales.
- Ejecutar DoS, fuerza bruta real o fuzzing agresivo.
- Modificar código, configuración o credenciales sin autorización.
- Rotar secretos por cuenta propia.
- Reescribir el historial de git sin coordinación.
- Ocultar un hallazgo crítico.
- Compartir secretos en el chat, logs o reportes.
- Usar herramientas de terceros que envíen código a la nube sin aprobación.

Si se detecta un secreto real: **detener, redactar, reportar y esperar**.

---

## 12. Definición de Done de seguridad para código nuevo

Toda funcionalidad nueva debe cumplir:

- [ ] Sin secretos ni credenciales.
- [ ] Authn y authz en servidor.
- [ ] Validación de entrada con schema.
- [ ] Codificación/escape de salida.
- [ ] Errores seguros y envelope único.
- [ ] Rate limit si es costosa o sensible.
- [ ] Upload seguro si acepta archivos.
- [ ] Consultas parametrizadas.
- [ ] Logs sin PII.
- [ ] Dependencias auditadas.
- [ ] Tests de 401/403/404/422 y límites.
- [ ] Documentación de contrato y permisos.
- [ ] Revisión de seguridad en el PR.

---

## 13. Integración con CI

El CI puede ejecutar el subconjunto automatizado:

| Gate | Comando | Bloquea |
|---|---|---|
| Secretos | `gitleaks detect --redact` | Sí |
| Dependencias Python | `pip-audit -r requirements.txt` | Sí (crítico/alto) |
| Dependencias Node | `npm audit --omit=dev --audit-level=high` | Sí (crítico/alto) |
| SAST Python | `bandit -r app` o `semgrep` | Sí (alto/crítico) |
| Docker | `hadolint Dockerfile` | Recomendado |
| Imagen | `trivy fs .` | Recomendado |
| Tests de permisos | `pytest tests/` | Sí |
| Contrato | `python scripts/export_openapi.py --check` | Sí |

La auditoría completa sigue siendo manual y bajo demanda. El CI no sustituye la
revisión de autorización, lógica de negocio ni configuración de despliegue.

---

## 14. Trazabilidad

| Hallazgo | Requisito |
|---|---|
| Secretos | NFR-SEC-02 |
| CORS | NFR-SEC-03 |
| Uploads | NFR-SEC-04 |
| Headers | NFR-SEC-05 |
| Rate limit | NFR-SEC-06, FR-AUTH-06 |
| Tokens/revocación | NFR-SEC-07, FR-AUTH-03/04/07 |
| ASVS | NFR-SEC-01 |
| Logs sin PII | NFR-PRIV-01 |
| Adjuntos autorizados | NFR-PRIV-03 |
| Backups | NFR-REL-03 |

Cada hallazgo se enlaza además a `BL-##` de [`baseline.md`](../taskflow/baseline.md)
y a una tarea `T-###` de [`tasks.md`](../taskflow/tasks.md) o una nueva.

---

## Anexo A — Comandos de referencia

```bash
# Secretos (no imprimir valores: -l lista archivos y --redact oculta coincidencias)
git ls-files
git grep -lE '(SECRET_KEY|DATABASE_URL|API_KEY|TOKEN|PASSWORD|PRIVATE KEY)'
gitleaks detect --source . --no-git --redact
gitleaks detect --source . --log-opts="--all" --redact

# Dependencias y SAST
pip-audit -r requirements.txt
bandit -r app
semgrep --config auto app
npm audit --omit=dev --audit-level=high

# Contenedor e infraestructura
hadolint Dockerfile
trivy fs .
docker scout cves taskflow-api:local

# Verificación funcional local
python -m pytest -q
python -m pytest tests/test_p1_hardening.py -q
python scripts/export_openapi.py --check
```

Los comandos que no estén disponibles se registran como gap de tooling.

---

## Anexo B — Matriz de permisos como checklist de authz

| Acción | Admin | Creador | Asignado | Member |
|---|---:|---:|---:|---:|
| Ver equipo/proyectos/tareas | ✅ | ✅ | ✅ | ✅ |
| Editar/archivar equipo | ✅ | ❌ | ❌ | ❌ |
| Gestionar miembros | ✅ | ❌ | ❌ | ❌ |
| Crear proyecto/tarea | ✅ | ✅ | ✅ | ✅ |
| Editar todos los campos de tarea | ✅ | ✅ | ❌ | ❌ |
| Cambiar solo estado | ✅ | ✅ | ✅ | ✅ |
| Asignar tarea | ✅ | ✅ | ❌ | ❌ |
| Eliminar tarea | ✅ | ✅ | ❌ | ❌ |
| Comentar | ✅ | ✅ | ✅ | ✅ |
| Editar comentario | ❌ | solo propio | solo propio | solo propio |
| Eliminar comentario | ✅ | solo propio | solo propio | solo propio |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Eliminar adjunto | ✅ | solo propio | solo propio | solo propio |

Cada fila debe tener al menos un test que demuestre permitido y denegado.

---

## Anexo C — Incidente de secreto: respuesta rápida

```text
1. Detectar y confirmar (sin copiar el valor).
2. Redactar y clasificar (real, test, placeholder).
3. Revocar/rotar con el proveedor.
4. Revisar accesos y logs.
5. Limpiar historial (filter-repo/BFG) con coordinación.
6. Añadir gitleaks a pre-commit y CI.
7. Documentar causa raíz y acciones.
8. Verificar que el secreto viejo ya no funciona.
```
