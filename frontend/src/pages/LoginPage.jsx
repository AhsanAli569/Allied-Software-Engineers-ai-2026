import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'
import Logo from '../components/ui/Logo'
import Button from '../components/ui/Button'
import Footer from '../components/ui/Footer'
import CompanyInfo from '../components/ui/CompanyInfo'

export default function LoginPage() {
  const { user, loading, login } = useAuth()
  const navigate = useNavigate()
  const [usernameOrEmail, setUsernameOrEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) return <Navigate to="/chat" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(usernameOrEmail, password)
      navigate('/chat')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-ice px-4 dark:bg-navy">
      <div className="w-full max-w-sm animate-fade-slide-up">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="relative">
            <div className="animate-soft-glow absolute inset-0 -z-10 rounded-2xl bg-mint/40 blur-xl" />
            <Logo size={44} />
          </div>
          <div className="text-center">
            <h1 className="text-lg font-semibold text-charcoal dark:text-white">Allied Software Engineers AI</h1>
            <p className="text-sm text-muted">Intelligence Engineered for Everyone</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-white/10 dark:bg-white/5">
          <h2 className="text-base font-medium text-charcoal dark:text-white">Sign in</h2>

          {error && (
            <p role="alert" className="animate-fade-slide-up rounded-lg bg-error/10 px-3 py-2 text-sm text-error">
              {error}
            </p>
          )}

          <div>
            <label htmlFor="usernameOrEmail" className="mb-1 block text-sm font-medium text-charcoal dark:text-slate-200">
              Username or email
            </label>
            <input
              id="usernameOrEmail"
              type="text"
              required
              autoComplete="username"
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-charcoal outline-none transition-colors focus:border-mint focus:ring-2 focus:ring-mint/20 dark:border-white/15 dark:bg-white/5 dark:text-slate-100"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-charcoal dark:text-slate-200">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-charcoal outline-none transition-colors focus:border-mint focus:ring-2 focus:ring-mint/20 dark:border-white/15 dark:bg-white/5 dark:text-slate-100"
            />
          </div>

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>

          <p className="text-center text-sm text-muted">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-medium text-emerald hover:underline dark:text-mint">
              Create one
            </Link>
          </p>
        </form>

        <CompanyInfo className="mt-6" />

        <p className="mt-4 text-center text-xs text-muted">
          ASE AI can make mistakes. Verify important information.
        </p>
        <Footer className="mt-2" />
      </div>
    </div>
  )
}
