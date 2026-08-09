import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/api'
import { calculateAge, isDateInFuture, maxDateOfBirthForMinimumAge, MINIMUM_AGE } from '../lib/validation'
import Logo from '../components/ui/Logo'
import Button from '../components/ui/Button'
import Footer from '../components/ui/Footer'

const initialForm = {
  full_name: '',
  username: '',
  email: '',
  password: '',
  confirm_password: '',
  date_of_birth: '',
}

const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]{3,50}$/
const MAX_DOB = maxDateOfBirthForMinimumAge()

// Client-side validation gives immediate, friendly feedback — the backend re-checks every
// one of these regardless (see app/schemas/auth.py), since a client-side check is never
// the real security/business-rule boundary, just a faster first pass.
function validate(form) {
  if (!USERNAME_PATTERN.test(form.username)) {
    return 'Username may only contain letters, numbers, dots, dashes and underscores (3-50 characters).'
  }
  if (!/[A-Za-z]/.test(form.password) || !/[0-9]/.test(form.password)) {
    return 'Password must contain at least one letter and one number.'
  }
  if (form.password !== form.confirm_password) {
    return 'Passwords do not match.'
  }
  if (!form.date_of_birth) {
    return 'Date of birth is required.'
  }
  if (isDateInFuture(form.date_of_birth)) {
    return 'Date of birth cannot be in the future.'
  }
  if (calculateAge(form.date_of_birth) < MINIMUM_AGE) {
    return `You must be at least ${MINIMUM_AGE} years old to create an ASE AI account.`
  }
  return null
}

export default function RegisterPage() {
  const { user, loading, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) return <Navigate to="/chat" replace />

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const validationError = validate(form)
    if (validationError) {
      setError(validationError)
      return
    }

    setSubmitting(true)
    try {
      await register(form)
      navigate('/chat')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-ice px-4 py-10 dark:bg-navy">
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
          <h2 className="text-base font-medium text-charcoal dark:text-white">Create your account</h2>

          {error && (
            <p role="alert" className="animate-fade-slide-up rounded-lg bg-error/10 px-3 py-2 text-sm text-error">
              {error}
            </p>
          )}

          <Field label="Full name" id="full_name" value={form.full_name} onChange={update('full_name')} autoComplete="name" />
          <Field
            label="Username"
            id="username"
            value={form.username}
            onChange={update('username')}
            autoComplete="username"
            hint="Letters, numbers, dots, dashes and underscores only."
          />
          <Field label="Email" id="email" type="email" value={form.email} onChange={update('email')} autoComplete="email" />
          <Field
            label="Date of birth"
            id="date_of_birth"
            type="date"
            value={form.date_of_birth}
            onChange={update('date_of_birth')}
            autoComplete="bday"
            max={MAX_DOB}
            hint={`You must be at least ${MINIMUM_AGE} to use ASE AI.`}
          />
          <Field
            label="Password"
            id="password"
            type="password"
            value={form.password}
            onChange={update('password')}
            autoComplete="new-password"
            hint="At least 8 characters, with a letter and a number."
          />
          <Field
            label="Confirm password"
            id="confirm_password"
            type="password"
            value={form.confirm_password}
            onChange={update('confirm_password')}
            autoComplete="new-password"
          />

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? 'Creating account…' : 'Create account'}
          </Button>

          <p className="text-center text-sm text-muted">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-emerald hover:underline dark:text-mint">
              Sign in
            </Link>
          </p>
        </form>
        <Footer className="mt-6" />
      </div>
    </div>
  )
}

function Field({ label, id, type = 'text', value, onChange, autoComplete, hint, max }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-charcoal dark:text-slate-200">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        minLength={type === 'password' ? 8 : undefined}
        max={max}
        autoComplete={autoComplete}
        value={value}
        onChange={onChange}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-charcoal outline-none transition-colors focus:border-mint focus:ring-2 focus:ring-mint/20 dark:border-white/15 dark:bg-white/5 dark:text-slate-100 [color-scheme:light] dark:[color-scheme:dark]"
      />
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  )
}
