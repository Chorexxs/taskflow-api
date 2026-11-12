import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { useDialogA11y } from '../hooks/useDialogA11y'

function Dialog({ onClose }) {
  const ref = useDialogA11y(true, onClose)
  return (
    <div ref={ref} role="dialog" aria-modal="true" aria-label="Test dialog">
      <button type="button">First</button>
      <button type="button">Second</button>
    </div>
  )
}

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button type="button" onClick={() => setOpen(true)}>
        Open
      </button>
      {open && <Dialog onClose={() => setOpen(false)} />}
    </div>
  )
}

async function openDialog() {
  render(<Harness />)
  await userEvent.click(screen.getByRole('button', { name: 'Open' }))
  return screen.getByRole('dialog', { name: 'Test dialog' })
}

describe('useDialogA11y', () => {
  it('moves focus to the first control when the dialog opens', async () => {
    await openDialog()
    expect(screen.getByRole('button', { name: 'First' })).toHaveFocus()
  })

  it('keeps Tab inside the dialog and wraps around', async () => {
    await openDialog()

    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Second' })).toHaveFocus()

    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'First' })).toHaveFocus()

    await userEvent.tab({ shift: true })
    expect(screen.getByRole('button', { name: 'Second' })).toHaveFocus()
  })

  it('closes on Escape and returns focus to the trigger', async () => {
    await openDialog()

    await userEvent.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open' })).toHaveFocus()
  })
})
