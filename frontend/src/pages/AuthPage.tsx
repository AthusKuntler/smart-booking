import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { me, signIn } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', business_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const isRegister = mode === 'register'

  if (me) return <Navigate to="/" replace />

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value })

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const { access_token } = isRegister ? await api.register(form) : await api.login(form.email, form.password)
      await signIn(access_token)
      navigate(isRegister ? '/hours' : '/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth">
      <form className="card auth-card" onSubmit={submit}>
        <div className="brand big"><span className="logo">◷</span> Smart Booking</div>
        <p className="muted">{isRegister ? 'Start taking online bookings in minutes.' : 'Welcome back.'}</p>
        {isRegister && (
          <>
            <label>Your name<input value={form.name} onChange={set('name')} required minLength={2} /></label>
            <label>Business name<input value={form.business_name} onChange={set('business_name')} required minLength={2} /></label>
          </>
        )}
        <label>Email<input type="email" value={form.email} onChange={set('email')} required autoComplete="email" /></label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set('password')} required minLength={isRegister ? 8 : 1}
            autoComplete={isRegister ? 'new-password' : 'current-password'} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}</button>
        <p className="muted small">
          {isRegister ? <>Already have an account? <Link to="/login">Sign in</Link></>
            : <>New here? <Link to="/register">Create an account</Link></>}
        </p>
      </form>
    </div>
  )
}
