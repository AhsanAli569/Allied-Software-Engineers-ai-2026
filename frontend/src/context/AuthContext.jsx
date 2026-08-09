import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get('/auth/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (usernameOrEmail, password) => {
    const loggedInUser = await api.post('/auth/login', { username_or_email: usernameOrEmail, password })
    setUser(loggedInUser)
    return loggedInUser
  }

  const register = async (fields) => {
    const newUser = await api.post('/auth/register', fields)
    setUser(newUser)
    return newUser
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Even if the server call fails, clear local state so the UI doesn't get stuck.
    }
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
