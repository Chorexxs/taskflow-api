# Auditoría de accesibilidad — flujos críticos

**Fecha:** 2026-11-10
**Alcance:** Login, registro, dashboard, equipo, tablero, tarea, perfil y
notificaciones.
**Referencia:** WCAG 2.1 AA.

## Resumen

| Flujo | Teclado | Foco visible | Etiquetas | Roles/ARIA | Contraste | Estado |
|---|---|---|---|---|---|---|
| Login / Register | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |
| Team detail | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |
| Tablero Kanban | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado con alternativa |
| Task detail | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |
| Perfil | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |
| Notificaciones | ✅ | ✅ | ✅ | ✅ | ✅ | Aprobado |

## Correcciones aplicadas

- Enlace “Skip to main content” y `main#main-content`.
- `:focus-visible` global con anillo de acento y `prefers-reduced-motion`.
- Todos los modales tienen `role="dialog"`, `aria-modal="true"` y nombre
  accesible (`aria-label`).
- Botones solo-icono con `aria-label` (filtros, actividad, ajustes, campana,
  perfil, logout, cerrar).
- Buscadores con `aria-label` además del placeholder.
- Formularios con `<label>` visible; los errores se anuncian con `role="alert"`
  en `QueryError` y mediante toasts.
- El tablero es operable con teclado: las tarjetas son enlaces/botones y el
  movimiento de columnas tiene alternativa (abrir la tarea y cambiarla).
- Textos de estado no dependen solo del color (incluyen etiqueta textual).

## Comprobaciones manuales

1. Navegación completa con `Tab`/`Shift+Tab` sin trampas de foco.
2. `Escape` cierra los modales mediante el botón de cierre (no hay captura de
   foco automática; mejora planificada).
3. Zoom al 200 % sin pérdida de contenido en 360 px.
4. `prefers-reduced-motion` desactiva animaciones no esenciales.
5. Contraste de texto principal/secundario sobre fondo oscuro verificado con
   los tokens de `index.css`.

## Revisión en navegador (2026-11-11)

Chrome DevTools detectó en el tablero 6 campos sin `id`/`name` y 5 sin label
asociado. Se corrigieron todos los formularios de la app (login, registro,
dashboard, equipo, tablero, tarea y perfil):

- `<label htmlFor="…">` + `id`/`name` en cada control.
- `aria-label` en buscadores, filtros y controles sin label visible.
- El test del tablero valida la asociación con `getByLabelText`.

## Deuda y seguimiento

| ID | Elemento | Prioridad | Destino |
|---|---|---|---|
| A11Y-01 | Focus trap + cierre con Escape en modales | Media | P6/T-076 |
| A11Y-02 | Auditoría automatizada con axe en CI | Media | T-076 |
| A11Y-03 | Revisión con lector de pantalla (NVDA/VoiceOver) | Baja | Release T-080 |

No quedan bloqueantes de accesibilidad en los flujos críticos.
