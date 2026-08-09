import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-400">Loading…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}
