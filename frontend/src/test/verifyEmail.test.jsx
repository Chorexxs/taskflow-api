import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import VerifyEmail from '../pages/VerifyEmail'

const mockApi = vi.hoisted(() => ({
  auth: { verifyEmail: vi.fn() },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderVerify(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('VerifyEmail', () => {
  it('verifies a valid token', async () => {
    mockApi.auth.verifyEmail.mockResolvedValue({ message: 'Email verified.' })

    renderVerify('/verify-email?token=abc')

    expect(await screen.findByText('Email verified.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login')
  })

  it('shows an error when the token is missing', async () => {
    renderVerify('/verify-email')

    expect(await screen.findByText(/missing its token/i)).toBeInTheDocument()
  })

  it('shows an error for an invalid token', async () => {
    mockApi.auth.verifyEmail.mockRejectedValue(new Error('Invalid or expired'))

    renderVerify('/verify-email?token=bad')

    expect(await screen.findByText('Invalid or expired')).toBeInTheDocument()
  })
})
