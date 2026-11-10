import { setupServer } from 'msw/node'

/** Shared MSW server for integration-style frontend tests. */
export const server = setupServer()
