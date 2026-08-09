import { createContext, useContext, useEffect, useState } from 'react'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'ase-ai-theme' // 'light' | 'dark' | 'system' — a harmless UI preference, fine for localStorage

function applyTheme(theme) {
  const isDark =
    theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', isDark)
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem(STORAGE_KEY) || 'system')

  useEffect(() => {
    applyTheme(theme)
    if (theme !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = () => applyTheme('system')
    media.addEventListener('change', listener)
    return () => media.removeEventListener('change', listener)
  }, [theme])

  const setTheme = (next) => {
    localStorage.setItem(STORAGE_KEY, next)
    setThemeState(next)
  }

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
