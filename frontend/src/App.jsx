/**
 * TaskFlow Frontend - Application Entry Point
 * 
 * This is the main application component that sets up routing and providers.
 * It configures:
 * - React Router for navigation
 * - Query Client for React Query
 * - Auth Context for authentication
 * - Theme Context for dark/light mode
 * 
 * Routes:
 * - /login - Login page (public)
 * - /register - Registration page (public)
 * - / - Dashboard (protected)
 * - /teams/:teamId - Team detail (protected)
 * - /teams/:teamId/projects/:projectId - Project board (protected)
 * - /teams/:teamId/projects/:projectId/tasks/:taskId - Task detail (protected)
 * - /profile - User profile (protected)
 * - /* - 404 Not Found
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import TeamDetail from './pages/TeamDetail';
import ProjectBoard from './pages/ProjectBoard';
import TaskDetail from './pages/TaskDetail';
import Profile from './pages/Profile';
import NotFound from './pages/NotFound';

/**
 * Protected route wrapper component.
 * Redirects unauthenticated users to login page.
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components to render if authenticated
 * @returns {JSX.Element} Children or redirect to login
 * 
 * @example
 * <ProtectedRoute>
 *   <Dashboard />
 * </ProtectedRoute>
 */
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  
  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

/**
 * Main application component.
 * Sets up all routes with appropriate protection levels.
 * 
 * @returns {JSX.Element} Application router
 * 
 * @example
 * // No props needed - component is self-contained
 * <App />
 */
function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* Protected routes with Layout */}
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
      
      {/* 404 catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
