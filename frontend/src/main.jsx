import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster 
            position="top-right"
            toastOptions={{
              className: 'toast-custom',
              duration: 3000,
              style: {
                background: 'var(--color-bg-secondary)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '14px',
              },
              success: {
                iconTheme: {
                  primary: 'var(--color-accent)',
                  secondary: 'var(--color-bg-primary)',
                },
              },
              error: {
                iconTheme: {
                  primary: 'var(--color-priority-high)',
                  secondary: 'var(--color-bg-primary)',
                },
              },
            }}
          />
          <div className="grain-overlay"></div>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)