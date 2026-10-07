import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, money, type Service } from '../api'

const empty = { name: '', duration_minutes: 30, price: '' }

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')

  const load = () => api.services().then(setServices)
  useEffect(() => { load() }, [])

  async function add(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api.createService({
        name: form.name.trim(),
        duration_minutes: Number(form.duration_minutes),
        price_cents: Math.round(Number(form.price || 0) * 100),
        active: true,
      })
      setForm(empty)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the service.')
    }
  }

  async function toggle(s: Service) {
    await api.updateService(s.id, { ...s, active: !s.active })
    load()
  }

  return (
    <>
      <header className="page-head"><h1>Services</h1></header>
      <div className="grid-2">
        <section className="card">
          <table>
            <thead><tr><th>Service</th><th>Duration</th><th>Price</th><th /></tr></thead>
            <tbody>
              {services.map(s => (
                <tr key={s.id} className={s.active ? '' : 'inactive'}>
                  <td>{s.name}</td>
                  <td>{s.duration_minutes} min</td>
                  <td>{money(s.price_cents)}</td>
                  <td className="right">
                    <button className="ghost" onClick={() => toggle(s)}>{s.active ? 'Hide' : 'Show'}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {services.length === 0 && <p className="empty">Add your first service to start taking bookings.</p>}
        </section>
        <form className="card form" onSubmit={add}>
          <h2>New service</h2>
          <label>Name<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required minLength={2} /></label>
          <label>Duration (minutes)
            <input type="number" min={5} max={480} step={5} value={form.duration_minutes}
              onChange={e => setForm({ ...form, duration_minutes: Number(e.target.value) })} required />
          </label>
          <label>Price (USD)
            <input type="number" min={0} step="0.01" value={form.price} placeholder="0.00"
              onChange={e => setForm({ ...form, price: e.target.value })} />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="primary">Add service</button>
        </form>
      </div>
    </>
  )
}
