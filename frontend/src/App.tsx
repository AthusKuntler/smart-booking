import { NavLink, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import AuthPage from './pages/AuthPage'
import BookingPage from './pages/BookingPage'
import Dashboard from './pages/Dashboard'
import HoursPage from './pages/HoursPage'
import ServicesPage from './pages/ServicesPage'

function OwnerLayout() {
  const { me, loading, signOut } = useAuth()
  if (loading) return <div className="center muted">Loading…</div>
  if (!me) return <Navigate to="/login" replace />
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">◷</span> Smart Booking
        </div>
        <div className="biz">{me.business.name}</div>
        <nav>
          <NavLink to="/" end>Agenda</NavLink>
          <NavLink to="/services">Services</NavLink>
          <NavLink to="/hours">Opening hours</NavLink>
        </nav>
        <a className="public-link" href={`/b/${me.business.slug}`} target="_blank" rel="noreferrer">
          Your booking page ↗
        </a>
        <button className="link" onClick={signOut}>Sign out</button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/b/:slug" element={<BookingPage />} />
      <Route element={<OwnerLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="services" element={<ServicesPage />} />
        <Route path="hours" element={<HoursPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
