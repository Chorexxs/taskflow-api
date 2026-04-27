import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

afterEach(() => {
  cleanup()
})

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock('lucide-react', () => ({
  ArrowLeft: () => null,
  Send: () => null,
  MessageSquare: () => null,
  User: () => null,
  Calendar: () => null,
  Edit2: () => null,
  X: () => null,
  Check: () => null,
  Paperclip: () => null,
  Download: () => null,
  Trash2: () => null,
  File: () => null,
  Pencil: () => null,
  Trash: () => null,
}))