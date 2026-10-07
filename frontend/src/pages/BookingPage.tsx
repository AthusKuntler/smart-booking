import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api, ApiError, isoDate, money, type Appointment, type PublicBusiness, type Service } from '../api'

function nextDays(n: number) {
  const today = new Date()
  return Array.from({ length: n }, (_, i) => new Date(today.getFullYear(), today.getMonth(), today.getDate() + i))
}

export default function BookingPage() {
  const { slug = '' } = useParams()
  const [biz, setBiz] = useState<PublicBusiness | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [service, setService] = useState<Service | null>(null)
  const [day, setDay] = useState(() => isoDate(new Date()))
  const [slots, setSlots] = useState<string[] | null>(null)
  const [slot, setSlot] = useState('')
  const [customer, setCustomer] = useState({ name: '', email: '', phone: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState<Appointment | null>(null)
  const days = useMemo(() => nextDays(14), [])

  useEffect(() => {
    api.publicBusiness(slug).then(setBiz).catch(() => setNotFound(true))
  }, [slug])

  useEffect(() => {
    if (!service) return
    let current = true
    api.slots(slug, service.id, day)
      .then(r => current && setSlots(r.slots))
      .catch(() => current && setSlots([]))
    return () => { current = false }
  }, [slug, service, day])

  // Changing service or day invalidates the previous slot list and choice.
  const chooseService = (s: Service) => { setService(s); setSlots(null); setSlot('') }
  const chooseDay = (iso: string) => { setDay(iso); setSlots(null); setSlot('') }

  async function confirm(e: FormEvent) {
    e.preventDefault()
    if (!service || !slot) return
    setError('')
    try {
      setDone(await api.book(slug, {
        service_id: service.id, start_at: `${day}T${slot}:00`,
        customer_name: customer.name, customer_email: customer.email, customer_phone: customer.phone,
      }))
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409
        ? 'Sorry, that time was just taken. Please pick another one.'
        : 'Please check your details and try again.')
      if (err instanceof ApiError && err.status === 409) {
        api.slots(slug, service.id, day).then(r => setSlots(r.slots))
      }
    }
  }

  if (notFound) return <div className="center muted">This booking page does not exist.</div>
  if (!biz) return <div className="center muted">Loading…</div>

  if (done) {
    const when = new Date(done.start_at)
    return (
      <div className="public">
        <div className="card confirm">
          <div className="check-big">✓</div>
          <h1>You're booked!</h1>
          <p><strong>{done.service_name}</strong> at <strong>{biz.name}</strong></p>
          <p className="big-date">{when.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })} · {done.start_at.slice(11, 16)}</p>
          <p className="muted">A confirmation was recorded for {done.customer_email}.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="public">
      <header className="public-head">
        <span className="logo">◷</span>
        <div><h1>{biz.name}</h1><p className="muted">Book online in under a minute</p></div>
      </header>

      <section className="card">
        <h2><span className="step">1</span> Choose a service</h2>
        <div className="service-grid">
          {biz.services.map(s => (
            <button key={s.id} className={`service ${service?.id === s.id ? 'selected' : ''}`} onClick={() => chooseService(s)}>
              <strong>{s.name}</strong>
              <span>{s.duration_minutes} min · {money(s.price_cents)}</span>
            </button>
          ))}
        </div>
      </section>

      {service && (
        <section className="card">
          <h2><span className="step">2</span> Pick a time</h2>
          <div className="days">
            {days.map(d => {
              const iso = isoDate(d)
              return (
                <button key={iso} className={`day ${iso === day ? 'selected' : ''}`} onClick={() => chooseDay(iso)}>
                  <small>{d.toLocaleDateString('en-US', { weekday: 'short' })}</small>
                  <b>{d.getDate()}</b>
                </button>
              )
            })}
          </div>
          {slots === null ? <p className="muted">Checking availability…</p>
            : slots.length === 0 ? <p className="empty">No times available on this day.</p> : (
              <div className="slots">
                {slots.map(t => (
                  <button key={t} className={`slot ${t === slot ? 'selected' : ''}`} onClick={() => setSlot(t)}>{t}</button>
                ))}
              </div>
            )}
        </section>
      )}

      {slot && (
        <form className="card form" onSubmit={confirm}>
          <h2><span className="step">3</span> Your details</h2>
          <label>Full name<input value={customer.name} onChange={e => setCustomer({ ...customer, name: e.target.value })} required minLength={2} /></label>
          <label>Email<input type="email" value={customer.email} onChange={e => setCustomer({ ...customer, email: e.target.value })} required /></label>
          <label>Phone (optional)<input value={customer.phone} onChange={e => setCustomer({ ...customer, phone: e.target.value })} /></label>
          {error && <div className="error">{error}</div>}
          <button className="primary">Confirm {service?.name} at {slot}</button>
        </form>
      )}
    </div>
  )
}
