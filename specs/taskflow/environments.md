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
- Antes de un release que toque DB/auth/storage → ejecutar el
  [`release-checklist.md`](./release-checklist.md) contra producción.

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
- Smoke test y checklist de release obligatorios
  ([`release-checklist.md`](./release-checklist.md)).
- Rollback según `CONTRIBUTING.md` §6.

---

## 6. Promoción de cambios

```text
local → CI → PR → merge en main → migración → deploy Render/Vercel → smoke + performance
```

Ningún cambio salta de local a producción sin CI verde. Un cambio de contrato
requiere actualizar `specs/taskflow/contracts/api.md` y el snapshot OpenAPI en el
mismo PR.

---

## 7. Retirada de InsForge y migración a Neon

**Estado (2026-11-26):** InsForge cerró la plataforma y deshabilitó los restores
(`RESTORE_DISABLED: InsForge is winding down: restores are closed`). Los datos se
recuperaron del backup diario y **Neon es la base de producción** (rama
`production` del proyecto `broad-dew-32991898`): 13 tablas, 322 filas,
`alembic_version = c1d2e3f4a5b6`. Render ya usa la URL pooled y el smoke
funcional da **15/15 en producción** (T-131 cerrada).

### Qué falló en el plan anterior (T-130)

El keep-alive se ejecutó a diario con `200` hasta el 2026-11-25 y el proyecto se
pausó igual: ni `GET /api/health` ni el `SELECT 1` de `/health/ready` (conexión
directa a Postgres) reinician el contador de 7 días. Un keep-alive basado en un
endpoint de salud **no** protege de la pausa; el workflow queda solo como
calentamiento de Render.

### Artefactos de la retirada

| Artefacto | Detalle |
|---|---|
| Backup SQL | `pg_dump` plano de `api-workflow` (2026-11-26 02:08 UTC), descargado fuera del repo en `~/Documents/insforge-backups/` |
| Contenido verificado | 13 tablas `public`, 322 filas, `alembic_version = c1d2e3f4a5b6` |
| Importador | `scripts/import_insforge_dump.py` (+ `tests/test_import_insforge_dump.py`) |
| Adjuntos | 15 objetos de 13 B en el bucket `taskflow-attachments`; se descargan desde el dashboard o se anulan sus `storage_key` |

### Migración a Neon (T-131)

1. Crear el proyecto en Neon (región Frankfurt/`eu-central` para acercarlo a Render).
2. `alembic upgrade head` contra la URL nueva: el esquema lo crea Alembic, nunca `create_all`.
3. `python scripts/import_insforge_dump.py --dump <backup.sql.gz> --target-url "$DATABASE_URL" --truncate`.
4. Configurar `DB_SSLMODE=require` y `STORAGE_BACKEND=database`; retirar las variables `INSFORGE_*`.
5. Smoke: `/health/ready`, registro/login y subida/descarga de adjunto.

Reglas:

1. Neon free **no** pausa proyectos por inactividad: apaga el compute a los 5 min
   y lo despierta en la siguiente consulta, sin cambiar la URL ni los datos.
2. El límite real de Neon free es 100 CU-horas/mes y 5 GB de egress por proyecto;
   al agotarlos se suspende el compute hasta el siguiente ciclo, sin borrar datos.
3. El dump de InsForge trae schemas internos (`auth`, `storage`, `cron`,
   `schedules`…); el importador carga solo `public` y ordena las tablas por
   dependencias de clave foránea, así que no hace falta superusuario.
4. Un cron diario ya no mantiene nada despierto en la base de datos: la única
   razón para conservar `keepalive.yml` es evitar el spin-down de Render.

---

## 8. Cuentas de prueba en producción

| Cuenta | Para qué |
|---|---|
| `webtest+1795682335815@example.com` | Admin del equipo `equipo-web-test` (proyecto 31, tarea 70): flujos de administración |
| `webtest2-20261126@example.com` | Segunda identidad: invitar, expulsar, cambiar rol y cualquier prueba que necesite dos usuarios |

- **Reutilizar** estas cuentas en las pruebas; no borrarlas ni crear una nueva
  por cada verificación.
- Las contraseñas **no** se guardan en el repo: están en el gestor de contraseñas
  del responsable.
- Los datos de prueba viven en el equipo `equipo-web-test`; se pueden limpiar
  por dentro sin tocar las cuentas.
