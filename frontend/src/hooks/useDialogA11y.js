import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/**
 * Accessibility behaviour shared by every modal (FR-UI-09, constitution 8.2):
 * focus moves inside on open, `Tab`/`Shift+Tab` stay inside, `Escape` closes,
 * and focus returns to the trigger on close.
 *
 * @param {boolean} isOpen - Whether the dialog is mounted and visible.
 * @param {() => void} onClose - Called when the user presses Escape.
 * @returns {import('react').RefObject<HTMLDivElement>} Ref for the dialog container.
 */
export function useDialogA11y(isOpen, onClose) {
  const dialogRef = useRef(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!isOpen) return undefined
    const dialog = dialogRef.current
    if (!dialog) return undefined

    const previouslyFocused = document.activeElement
    const focusables = () => Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR))

    const initial = focusables()[0]
    if (initial) initial.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current?.()
        return
      }
      if (event.key !== 'Tab') return

      const items = focusables()
      if (items.length === 0) {
        event.preventDefault()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      if (previouslyFocused instanceof HTMLElement && document.contains(previouslyFocused)) {
        previouslyFocused.focus()
      }
    }
  }, [isOpen])

  return dialogRef
}
