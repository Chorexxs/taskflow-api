/**
 * TaskFlow Frontend - Theme Context
 * 
 * This module provides theme (dark/light mode) management for the application.
 * It uses React Context to provide theme state and toggle methods.
 * 
 * Features:
 * - Dark/Light mode toggle
 * - Persists user preference in localStorage
 * - Respects system preference on first visit
 * - Automatically adds/removes 'dark' class on HTML element
 * 
 * The context provides:
 * - darkMode: Boolean indicating dark mode state
 * - toggleDarkMode: Function to toggle between dark and light mode
 * 
 * Usage:
 * import { useTheme } from './context/ThemeContext';
 * 
 * function MyComponent() {
 *   const { darkMode, toggleDarkMode } = useTheme();
 *   // Use theme state
 * }
 */

import { createContext, useContext, useState, useEffect } from 'react';

/**
 * Theme context - provides theme state and toggle method
 * @type {React.Context}
 */
const ThemeContext = createContext();

/**
 * Theme provider component.
 * Manages dark/light mode state and persists preference.
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 * @returns {JSX.Element} ThemeProvider wrapper
 * 
 * @example
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 */
export function ThemeProvider({ children }) {
  /**
   * Initialize dark mode state.
   * Priority: localStorage > system preference > false
   */
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  /**
   * Effect: Apply dark mode class to HTML element and persist preference.
   * Runs whenever isDark state changes.
   */
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  /**
   * Toggle between dark and light mode.
   * 
   * @example
   * function ThemeToggle() {
   *   const { toggleDarkMode } = useTheme();
   *   return <button onClick={toggleDarkMode}>Toggle Theme</button>;
   * }
   */
  const toggleDarkMode = () => setIsDark(prev => !prev);

  return (
    <ThemeContext.Provider value={{ darkMode: isDark, toggleDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context.
 * Must be used within a ThemeProvider.
 * 
 * @returns {Object} Theme context with darkMode and toggleDarkMode
 * @throws {Error} If used outside ThemeProvider
 * 
 * @example
 * function Header() {
 *   const { darkMode, toggleDarkMode } = useTheme();
 *   
 *   return (
 *     <header>
 *       <h1>TaskFlow</h1>
 *       <button onClick={toggleDarkMode}>
 *         {darkMode ? '🌙' : '☀️'}
 *       </button>
 *     </header>
 *   );
 * }
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
