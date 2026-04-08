import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import TeamDetail from './pages/TeamDetail'
import ProjectBoard from './pages/ProjectBoard'
import TaskDetail from './pages/TaskDetail'
import Profile from './pages/Profile'
import NotFound from './pages/NotFound'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  return children
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      <Route path="/" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/teams/:teamId" element={
        <ProtectedRoute>
          <Layout>
            <TeamDetail />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/teams/:teamId/projects/:projectId" element={
        <ProtectedRoute>
          <Layout>
            <ProjectBoard />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/teams/:teamId/projects/:projectId/tasks/:taskId" element={
        <ProtectedRoute>
          <Layout>
            <TaskDetail />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/profile" element={
        <ProtectedRoute>
          <Layout>
            <Profile />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App
