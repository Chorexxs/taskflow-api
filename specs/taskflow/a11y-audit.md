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
- Los modales comparten `useDialogA11y`: el foco entra en el primer control,
  `Tab`/`Shift+Tab` quedan atrapados, `Escape` cierra y el foco vuelve al
  disparador (T-120).
- Botones solo-icono con `aria-label`: filtros, actividad, ajustes, campana,
  perfil, logout, volver, "New Task" (también por debajo de `sm`, donde el texto
  se oculta), enviar comentario, editar/eliminar comentario, editar/restaurar
  proyecto, quitar miembro y cierre de cada modal (T-133).
- Buscadores con `aria-label` además del placeholder.
- Formularios con `<label>` visible; los errores se anuncian con `role="alert"`
  en `QueryError` y mediante toasts.
- El tablero es operable con teclado: las tarjetas son enlaces/botones y el
  movimiento de columnas tiene alternativa (abrir la tarea y cambiarla).
- Textos de estado no dependen solo del color (incluyen etiqueta textual).

## Comprobaciones manuales

1. Navegación completa con `Tab`/`Shift+Tab`; en modales el foco queda atrapado.
2. `Escape` cierra los modales y devuelve el foco al disparador (T-120).
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

## Revisión con navegador real (2026-11-26)

Prueba end-to-end contra producción con Chrome (registro, equipo, proyecto,
tablero, tarea, comentario, adjunto, búsqueda y notificaciones). La auditoría de
2026-11-11 daba los iconos por cubiertos, pero el árbol de accesibilidad del
navegador mostró botones sin nombre y una tarjeta sin acción:

| ID | Hallazgo | Corrección |
|---|---|---|
| A11Y-04 | "New Task" pierde el texto por debajo de `sm` y quedaba sin nombre accesible; el botón de volver del tablero y del detalle de tarea tampoco tenían nombre | T-133: `aria-label` explícito, independiente del ancho |
| A11Y-05 | Cierres de modal (X), enviar comentario, editar/eliminar comentario, quitar miembro y editar/restaurar proyecto dependían de `title` o no tenían nombre | T-133 |
| A11Y-06 | La tarjeta del tablero era un `div[role=button]` sin `onClick` y con un `button` anidado: no abría la tarea y duplicaba controles | T-134: un único control que abre el detalle con clic y `Enter` |
| A11Y-07 | El detalle de equipo mostraba "No members yet" mientras la query estaba pendiente | T-135: skeleton hasta que la carga termina |
| A11Y-08 | Los inputs de email y contraseña no declaraban `autoComplete`; Chrome lo reporta como issue y los gestores de contraseñas no se activan | T-136: `email`, `current-password` y `new-password` en login, registro, perfil e invitación |

## Deuda y seguimiento

| ID | Elemento | Prioridad | Destino |
|---|---|---|---|
| A11Y-01 | Focus trap + cierre con Escape en modales | Media | ✅ Resuelto en T-120 (`useDialogA11y` + tests) |
| A11Y-02 | Auditoría automatizada con axe en CI | Media | Backlog |
| A11Y-03 | Revisión con lector de pantalla (NVDA/VoiceOver) | Baja | Backlog |
| A11Y-04 | Botones sin nombre accesible según ancho de viewport | Alta | ✅ Resuelto en T-133 |
| A11Y-05 | Controles solo-icono sin `aria-label` | Alta | ✅ Resuelto en T-133 |
| A11Y-06 | Tarjeta de tarea sin acción y con controles anidados | Alta | ✅ Resuelto en T-134 |
| A11Y-07 | Estado vacío falso durante la carga de miembros | Baja | ✅ Resuelto en T-135 |
| A11Y-08 | Inputs sin `autoComplete` | Baja | ✅ Resuelto en T-136 |

No quedan bloqueantes de accesibilidad en los flujos críticos.
