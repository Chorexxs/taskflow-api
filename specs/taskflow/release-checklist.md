# Release checklist — TaskFlow

**Tarea:** T-080
**Fecha de la última ejecución:** 2026-11-10
**Referencias:** `constitution.md` §Quality gates, `CONTRIBUTING.md` §5-6,
`environments.md`, `security-checklist.md`, `spec.md` NFR-PERF-01…05.

Una release solo se publica cuando **todos** los ítems de esta checklist están
verificados y firmados. Si algo falla, se aplica el rollback de
`CONTRIBUTING.md` §6 y se abre un incidente.

---

## 1. Firmas

| Rol | Responsable | Fecha | Resultado |
|---|---|---|---|
| Autor del cambio | responsable del proyecto | 2026-11-10 | ✅ |
| Revisión de código | pendiente (PR) | — | — |
| Revisión de seguridad | responsable del proyecto | 2026-11-10 | ✅ (`security-checklist.md`) |
| Aprobación de release | responsable del proyecto | — | — |

---

## 2. Pre-release (código y contrato)

- [x] `main` verde y sin cambios locales sin commitear.
- [x] `pytest -q` → **174 passed** sobre PostgreSQL 15.
- [x] `pytest --cov=app --cov-fail-under=80` → **86 %** de cobertura.
- [x] `mypy app` → **Success: no issues found in 23 source files**.
- [x] `ruff check app tests` y `ruff format --check app tests` → limpios.
- [ ] `npm run test:coverage`, `npm run lint` y `npm run build` → verdes (CI frontend).
- [ ] `python scripts/export_openapi.py --check` → snapshot al día.
- [x] `alembic upgrade head` → aplicado en local (PostgreSQL 15).
- [ ] `alembic downgrade -1` + `upgrade head` → reversible.
- [ ] `pip-audit -r requirements.txt` y `npm audit --omit=dev` → sin vulnerabilidades.
- [ ] `gitleaks detect` → historial limpio.
- [ ] `CHANGELOG.md` actualizado y `spec.md`/`contracts/api.md`/`data-model.md` si cambió el contrato.

---

## 3. Pre-release (datos y seguridad)

- [ ] Backup verificado de InsForge antes de una migración destructiva.
- [ ] Migración revisada: `upgrade` y `downgrade` documentados; sin `create_all`.
- [x] Sin secretos ni PII en el diff, logs o capturas.
- [x] Permisos verificados en servidor (matriz 401/403/404).
- [x] `SECRET_KEY`, `DATABASE_URL` y `CORS_ORIGINS` presentes en Render.
- [x] `/docs`, `/redoc` y `/openapi.json` deshabilitados en producción.
- [ ] Rotación de `SECRET_KEY` (solo si aplica; invalida sesiones).

---

## 4. Smoke de performance

Objetivo (NFR-PERF-01): **p95 < 300 ms** en lecturas típicas. Las escrituras
tienen un objetivo de 500 ms (NFR-PERF-02); este smoke mide lecturas.

```bash
# API local o staging (gate principal)
python scripts/smoke_performance.py --base-url http://127.0.0.1:8000 --samples 50

# Con endpoints autenticados
TOKEN="<access_token>"
python scripts/smoke_performance.py \
  --base-url https://taskflow-api-gkgl.onrender.com \
  --samples 20 --token "$TOKEN" --threshold-ms 1000 --json
```

El script calienta `/health/live` antes de medir para no confundir un arranque en
frío de Render con el p95. Devuelve código distinto de cero si hay errores o si
el p95 supera el umbral.

### Resultado local (2026-11-10, PostgreSQL 15, 50 muestras)

| Endpoint | p50 | p95 | Errores |
|---|---:|---:|---:|
| `/health` | 15,6 ms | 29,5 ms | 0 |
| `/health/live` | 2,1 ms | 23,5 ms | 0 |
| `/health/ready` | 15,7 ms | 29,3 ms | 0 |
| `/api/v1/users/me` | 27,9 ms | 32,7 ms | 0 |
| `/api/v1/notifications/unread-count` | 8,7 ms | 29,3 ms | 0 |

**Veredicto:** ✅ p95 < 300 ms en todas las lecturas.

### Resultado de producción (Render + InsForge)

Medir desde la misma región o con un umbral relajado: la latencia WAN y el
arranque en frío de Render no forman parte del objetivo de la API. Registrar aquí
la fecha, el commit desplegado y los valores obtenidos:

| Fecha | Commit | Endpoint | p95 | Umbral | Veredicto |
|---|---|---|---:|---:|---|
| 2026-11-10 | pre-T-094 | `/health` | 1541,9 ms | 1000 ms | ❌ (Redis bloqueaba 4 s) |
| 2026-11-10 | pre-T-094 | `/health/live` | 244,9 ms | 1000 ms | ✅ |
| 2026-11-10 | pre-T-094 | `/health/ready` | 867,5 ms | 1000 ms | ✅ |

> T-094 eliminó el bloqueo de Redis y T-093 corrigió el 500 de los endpoints
> limitados (`eb9815b`). El redeploy de Render sigue pendiente: ver **B-05** en
> `blockers.md`. Repetir la medición tras el redeploy y actualizar esta tabla
> antes de aprobar la release.

### Smoke de carga SSE (T-081)

```bash
# Servidor local sin rate limit por IP y con los límites elevados para la prueba
RATE_LIMIT_ENABLED=false SSE_MAX_CONNECTIONS=600 \
SSE_MAX_CONNECTIONS_PER_USER=600 \
python -m uvicorn app.main:app --port 8002

python scripts/sse_load_test.py \
  --base-url http://127.0.0.1:8002 --token "$TOKEN" \
  --connections 500 --duration 20
```

Resultado local (2026-11-10, PostgreSQL 15, 500 conexiones, 20 s):

| Métrica | Valor |
|---|---:|
| Conexiones abiertas | 500/500 |
| Fallos | 0 |
| Handshake p50 / p95 | 3758,8 ms / 4031,0 ms |
| Heartbeats recibidos | 500 |
| Errores de transporte | 0 |

El handshake p95 incluye la autenticación contra PostgreSQL de 500 clientes
simultáneos con un pool de 30 conexiones; no es la latencia de entrega de
eventos. La entrega event-driven se valida con los tests de pub/sub y de
reconciliación.

---

## 5. Deploy

1. [ ] `alembic upgrade head` contra InsForge (antes del código).
2. [ ] Deploy de la API en Render (automático desde `main`).
3. [ ] `/health/live` → 200 y `/health/ready` → `{"status":"ready"}`.
4. [ ] Deploy o verificación del frontend en Vercel.
5. [ ] `VITE_API_URL` apunta a la API correcta.
6. [ ] Verificar CORS para el dominio de producción y rechazo de un origen no permitido.

---

## 6. Post-deploy smoke (13 checks)

| # | Check | Evidencia |
|---|---|---|
| 1 | `GET /health` | 200 |
| 2 | `GET /health/live` | 200 |
| 3 | `GET /health/ready` | 200 |
| 4 | Registro | 201 + `X-RateLimit-*` |
| 5 | Login | 200 + access/refresh |
| 6 | Crear equipo | 201 |
| 7 | Crear proyecto | 201 |
| 8 | Crear tarea | 201 |
| 9 | Comentar | 201 |
| 10 | Subir y descargar adjunto | 201 / 200 |
| 11 | Búsqueda | 200 |
| 12 | Notificaciones y contador | 200 |
| 13 | Envelope de error (`404` de otro equipo) | `error.code` y `request_id` |

- [ ] 13/13 correctos.
- [ ] `/api/v1/users/me` con el token del smoke → 200.
- [ ] Logs sin secretos, tokens ni emails completos.
- [ ] Monitorización 30 min: 5xx, login/refresh y latencia.

---

## 7. Rollback

| Capa | Acción | Verificación |
|---|---|---|
| Frontend | Redeploy del deployment anterior en Vercel | `/login` carga |
| API | Redeploy del deploy anterior en Render | `/health/ready` → 200 |
| DB | `alembic downgrade -1` si es reversible; si no, restore del backup | `alembic current` |
| Feature flag | Desactivar sin redeploy | Comportamiento previo |

Criterios de aborto (iguales a `CONTRIBUTING.md` §5):

- 5xx > 5 % durante 5 minutos.
- Login o refresh fallando > 10 %.
- Migración bloqueada > 15 minutos.
- Pérdida de acceso a datos o storage.

---

## 8. Cierre

- [ ] Tag `vX.Y.Z` creado y release publicada con las notas del CHANGELOG.
- [ ] `tasks.md` actualizado con la tarea cerrada.
- [ ] Retrospectiva breve: incidencias, tiempo de deploy y acciones de seguimiento.
- [ ] Riesgos residuales registrados (staging no aprovisionado, S3 pendiente,
      SSE sin Redis pub/sub).
