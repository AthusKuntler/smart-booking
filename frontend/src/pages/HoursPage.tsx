import { useEffect, useState } from 'react'
import { api, ApiError, WEEKDAYS } from '../api'

interface Row { open: boolean; opens_at: string; closes_at: string }

const defaults = (): Row[] => WEEKDAYS.map((_, i) => ({ open: i < 5, opens_at: '09:00', closes_at: '18:00' }))

export default function HoursPage() {
  const [rows, setRows] = useState<Row[]>(defaults)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.hours().then(hours => {
      if (!hours.length) return
      const next = defaults().map(r => ({ ...r, open: false }))
      for (const h of hours) next[h.weekday] = { open: true, opens_at: h.opens_at.slice(0, 5), closes_at: h.closes_at.slice(0, 5) }
      setRows(next)
    })
  }, [])

  const update = (i: number, patch: Partial<Row>) => setRows(rows.map((r, j) => (i === j ? { ...r, ...patch } : r)))

  async function save() {
    setMessage('')
    setError('')
    try {
      await api.setHours(rows.flatMap((r, weekday) => (r.open ? [{ weekday, opens_at: r.opens_at, closes_at: r.closes_at }] : [])))
      setMessage('Opening hours saved.')
    } catch (err) {
      setError(err instanceof ApiError ? 'Each open day needs a closing time after the opening time.' : 'Could not save.')
    }
  }

  return (
    <>
      <header className="page-head"><h1>Opening hours</h1></header>
      <section className="card narrow">
        <p className="muted">Customers can only book times that fit entirely inside these hours.</p>
        {rows.map((r, i) => (
          <div className="hours-row" key={WEEKDAYS[i]}>
            <label className="check">
              <input type="checkbox" checked={r.open} onChange={e => update(i, { open: e.target.checked })} />
              {WEEKDAYS[i]}
            </label>
            {r.open ? (
              <>
                <input type="time" value={r.opens_at} onChange={e => update(i, { opens_at: e.target.value })} />
                <span className="muted">to</span>
                <input type="time" value={r.closes_at} onChange={e => update(i, { closes_at: e.target.value })} />
              </>
            ) : <span className="muted closed">Closed</span>}
          </div>
        ))}
        {error && <div className="error">{error}</div>}
        {message && <div className="success">{message}</div>}
        <button className="primary" onClick={save}>Save hours</button>
      </section>
    </>
  )
}
