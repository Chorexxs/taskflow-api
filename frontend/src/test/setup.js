import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

// Node 22+ exposes an experimental `localStorage` global that is undefined
// unless `--localstorage-file` is passed, which can shadow jsdom's version.
// Provide the jsdom implementation when available and a deterministic
// in-memory fallback otherwise, so tests never depend on the Node flag.
function createMemoryStorage() {
  const store = new Map()
  return {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (key) => (store.has(String(key)) ? store.get(String(key)) : null),
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => store.delete(String(key)),
    setItem: (key, value) => store.set(String(key), String(value)),
  }
}

const storage =
  (typeof window !== 'undefined' && window.localStorage) || createMemoryStorage()

Object.defineProperty(globalThis, 'localStorage', {
  value: storage,
  configurable: true,
})
Object.defineProperty(globalThis, 'sessionStorage', {
  value:
    (typeof window !== 'undefined' && window.sessionStorage) || createMemoryStorage(),
  configurable: true,
})

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