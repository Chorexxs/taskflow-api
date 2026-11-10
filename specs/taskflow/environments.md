# Entornos — TaskFlow

**Fecha:** 2026-11-10
**Tarea:** T-009 (preview/staging documentado)
**Referencias:** `plan.md` §8, `blockers.md` B-02/B-03, `CONTRIBUTING.md` §5.

---

## Resumen

| Entorno | API | Frontend | Base de datos | Uso |
|---|---|---|---|---|
| Local | Uvicorn `http://localhost:8000` | Vite `http://localhost:5173` | PostgreSQL + Redis en Docker | Desarrollo y pruebas manuales |
| CI | No aplica | Build de Vite | PostgreSQL efímero del runner | Gates automáticos |
| Preview | API de producción (compartida) | Vercel Preview por PR | InsForge de producción | Revisión visual de UI |
| Staging | **No aprovisionado** | — | — | — |
| Producción | Render | Vercel | InsForge | Usuarios reales |

---

## 1. Local

```bash
docker compose up -d          # PostgreSQL + Redis + API
cd frontend && npm run dev    # http://localhost:5173
```

- `ENVIRONMENT=development`, `STORAGE_BACKEND=local` o `database`.
- Datos desechables; nunca se copian datos de producción.
- `DATABASE_URL` y `SECRET_KEY` salen de `.env` (ignorado por git).

Criterio de salida: `pytest` verde y `npm run test` verde antes de abrir PR.

---

## 2. CI

Cada push/PR a `main` ejecuta los gates de la constitución sobre un PostgreSQL
efímero del runner (`TEST_DATABASE_URL`). El esquema se crea con `alembic upgrade
head`, por lo que CI valida también las migraciones.

- No usa InsForge ni Render.
- El snapshot OpenAPI (`python scripts/export_openapi.py --check`) bloquea
  cambios de contrato no revisados.

---

## 3. Preview (frontend)

- **URL:** el deployment de Vercel asociado al PR (`*.vercel.app`) o el alias
  `https://taskflow-api-tau.vercel.app` para `main`.
- **API:** `VITE_API_URL=https://taskflow-api-gkgl.onrender.com` (producción).
- **DB:** InsForge de producción.

Limitaciones y reglas de uso:

1. El preview **comparte la API y la base de producción**: solo se usa con
   cuentas de prueba y datos desechables.
2. Para cambios de UI es suficiente. Para cambios de contrato o migraciones se
   valida en local/CI, nunca desde el preview.
3. `frontend/vercel.json` aplica rewrite SPA y headers de seguridad también en
   previews.

---

## 4. Staging

**Estado: no aprovisionado (decisión registrada en T-009).**

Motivos:

- Render no tiene un entorno de preview/branch habilitado para el servicio
  actual.
- InsForge no ofrece una branch de base de datos separada en el plan actual.
- Un staging con la misma base que producción no aporta aislamiento y sí riesgo
  de datos.

Sustituto acordado:

- Cambios de API/DB → local con Docker + CI sobre PostgreSQL efímero.
- Cambios de UI → Vercel Preview con cuentas de prueba.
- Antes de un release que toque DB/auth/storage → ejecutar la checklist de
  release (T-080) contra producción.

### Cómo habilitar staging en el futuro

1. Crear un servicio de Render independiente con `ENVIRONMENT=staging`.
2. Crear una base PostgreSQL separada (branch de InsForge o instancia propia) y
   migrarla con `alembic upgrade head`.
3. Configurar `CORS_ORIGINS` con la URL del frontend de staging y
   `STORAGE_BACKEND=database`.
4. Añadir el smoke test de staging al pipeline y documentar la URL aquí.

---

## 5. Producción

| Servicio | URL | Verificación |
|---|---|---|
| API | `https://taskflow-api-gkgl.onrender.com` | `/health/ready` → 200 |
| Frontend | `https://taskflow-api-tau.vercel.app` | `/login` carga |
| DB | InsForge (`eu-central`) | `alembic current` = head |
| Preview alternativo | `https://<insforge-project-id>.insforge.site` | Mismo build |

Reglas:

- `ENVIRONMENT=production`, `SECRET_KEY` y `CORS_ORIGINS` obligatorios (fail-fast).
- Deploy automático desde `main`; migración antes del código.
- Smoke test y checklist de release obligatorios (T-080).
- Rollback según `CONTRIBUTING.md` §6.

---

## 6. Promoción de cambios

```text
local → CI → PR → merge en main → migración → deploy Render/Vercel → smoke + performance
```

Ningún cambio salta de local a producción sin CI verde. Un cambio de contrato
requiere actualizar `specs/taskflow/contracts/api.md` y el snapshot OpenAPI en el
mismo PR.
