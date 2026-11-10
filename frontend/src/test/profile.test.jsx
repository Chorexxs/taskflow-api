import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '../context/AuthContext'
import Profile from '../pages/Profile'

const mockApi = vi.hoisted(() => ({
  auth: { logout: vi.fn() },
  users: {
    me: vi.fn(),
    update: vi.fn(),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderProfile() {
  return render(
    <MemoryRouter initialEntries={['/profile']}>
      <AuthProvider>
        <Routes>
          <Route path="/profile" element={<Profile />} />
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Profile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('access_token', 'access-token')
    localStorage.setItem('refresh_token', 'refresh-token')
    mockApi.users.me.mockResolvedValue({ id: 1, email: 'me@example.com' })
  })

  it('shows the current email', async () => {
    renderProfile()

    expect(await screen.findByDisplayValue('me@example.com')).toBeInTheDocument()
    expect(screen.getByText(/email cannot be changed/i)).toBeInTheDocument()
  })

  it('validates that all password fields are present', async () => {
    renderProfile()
    await screen.findByDisplayValue('me@example.com')

    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    expect(screen.getByText(/fill in all password fields/i)).toBeInTheDocument()
    expect(mockApi.users.update).not.toHaveBeenCalled()
  })

  it('updates the password and closes the session', async () => {
    mockApi.users.update.mockResolvedValue({})
    mockApi.auth.logout.mockResolvedValue(undefined)

    renderProfile()
    await screen.findByDisplayValue('me@example.com')

    await userEvent.type(
      screen.getByPlaceholderText('Enter current password'),
      'current-pass',
    )
    await userEvent.type(screen.getByPlaceholderText('Enter new password'), 'new-password-123')
    await userEvent.type(
      screen.getByPlaceholderText('Confirm new password'),
      'new-password-123',
    )
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    await waitFor(() =>
      expect(mockApi.users.update).toHaveBeenCalledWith('access-token', {
        current_password: 'current-pass',
        password: 'new-password-123',
      }),
    )
    expect(await screen.findByText('login page')).toBeInTheDocument()
  })
})
