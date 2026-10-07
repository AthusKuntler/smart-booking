import { useEffect, useMemo, useState } from 'react'
import { api, isoDate, money, type Appointment, type AppointmentStatus, type Stats } from '../api'

const time = (iso: string) => iso.slice(11, 16)

export default function Dashboard() {
  const [day, setDay] = useState(() => new Date())
  const [stats, setStats] = useState<Stats | null>(null)
  const [items, setItems] = useState<Appointment[]>([])
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0) // bump to reload after a change

  useEffect(() => {
    let current = true
    const d = isoDate(day)
    Promise.all([api.stats(), api.appointments(d, d)])
      .then(([s, a]) => {
        if (!current) return
        setStats(s)
        setItems(a)
        setError('')
      })
      .catch(() => current && setError('Could not load your agenda.'))
    return () => { current = false }
  }, [day, version])

  const shift = (days: number) => setDay(new Date(day.getFullYear(), day.getMonth(), day.getDate() + days))

  async function change(id: number, status: AppointmentStatus) {
    await api.setStatus(id, status)
    setVersion(v => v + 1)
  }

  const dayRevenue = useMemo(
    () => items.filter(a => a.status !== 'cancelled').reduce((sum, a) => sum + a.price_cents, 0), [items])

  return (
    <>
      <header className="page-head">
        <h1>Agenda</h1>
      </header>
      {stats && (
        <section className="kpis">
          <div className="kpi"><b>{stats.today}</b><span>bookings today</span></div>
          <div className="kpi"><b>{stats.next_7_days}</b><span>next 7 days</span></div>
          <div className="kpi"><b>{money(stats.revenue_this_month_cents)}</b><span>revenue this month (completed)</span></div>
          <div className="kpi"><b>{Math.round(stats.cancellation_rate * 100)}%</b><span>cancellation rate</span></div>
        </section>
      )}
      <div className="grid-2">
        <section className="card">
          <div className="day-nav">
            <button onClick={() => shift(-1)} aria-label="Previous day">‹</button>
            <strong>{day.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</strong>
            <button onClick={() => shift(1)} aria-label="Next day">›</button>
            <button className="link" onClick={() => setDay(new Date())}>Today</button>
            <span className="muted push">{items.length} bookings · {money(dayRevenue)}</span>
          </div>
          {error && <div className="error">{error}</div>}
          {items.length === 0 ? <p className="empty">No bookings for this day.</p> : (
            <ul className="agenda">
              {items.map(a => (
                <li key={a.id} className={`appt ${a.status}`}>
                  <div className="when">{time(a.start_at)}<small>{time(a.end_at)}</small></div>
                  <div className="who">
                    <strong>{a.customer_name}</strong>
                    <span>{a.service_name} · {money(a.price_cents)}</span>
                    <small className="muted">{a.customer_phone || a.customer_email}</small>
                  </div>
                  <div className="actions">
                    {a.status === 'booked' ? (
                      <>
                        <button onClick={() => change(a.id, 'completed')}>Done</button>
                        <button className="ghost" onClick={() => change(a.id, 'cancelled')}>Cancel</button>
                      </>
                    ) : <span className={`pill ${a.status}`}>{a.status}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card">
          <h2>Top services this month</h2>
          {!stats?.top_services.length ? <p className="empty">No data yet.</p> : (
            <ul className="bars">
              {stats.top_services.map(s => (
                <li key={s.name}>
                  <span>{s.name}</span>
                  <div className="bar"><i style={{ width: `${(s.bookings / stats.top_services[0].bookings) * 100}%` }} /></div>
                  <b>{s.bookings}</b>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  )
}
