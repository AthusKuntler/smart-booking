export type AppointmentStatus = 'booked' | 'completed' | 'cancelled'

export interface Business { id: number; name: string; slug: string }
export interface Me { id: number; name: string; email: string; business: Business }
export interface Service { id: number; name: string; duration_minutes: number; price_cents: number; active: boolean }
export interface WorkingHours { weekday: number; opens_at: string; closes_at: string }
export interface Appointment {
  id: number
  service_id: number
  service_name: string
  customer_name: string
  customer_email: string
  customer_phone: string
  start_at: string
  end_at: string
  status: AppointmentStatus
  price_cents: number
}
export interface Stats {
  today: number
  next_7_days: number
  revenue_this_month_cents: number
  cancellation_rate: number
  top_services: { name: string; bookings: number; revenue_cents: number }[]
}
export interface PublicBusiness { name: string; slug: string; services: Service[]; hours: WorkingHours[] }

const TOKEN_KEY = 'sb_token'
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = tokenStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof URLSearchParams)) headers.set('Content-Type', 'application/json')
  const res = await fetch(path, { ...init, headers })
  if (res.status === 401 && token) {
    tokenStore.clear()
    window.location.assign('/login')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : 'Please check the form and try again.'
    throw new ApiError(res.status, detail)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })

export const api = {
  register: (data: { name: string; email: string; password: string; business_name: string }) =>
    request<{ access_token: string }>('/api/auth/register', json('POST', data)),
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: new URLSearchParams({ username: email, password }),
    }),
  me: () => request<Me>('/api/auth/me'),
  stats: () => request<Stats>('/api/stats'),
  services: () => request<Service[]>('/api/services'),
  createService: (s: Omit<Service, 'id'>) => request<Service>('/api/services', json('POST', s)),
  updateService: (id: number, s: Omit<Service, 'id'>) => request<Service>(`/api/services/${id}`, json('PUT', s)),
  hours: () => request<WorkingHours[]>('/api/hours'),
  setHours: (h: WorkingHours[]) => request<WorkingHours[]>('/api/hours', json('PUT', h)),
  appointments: (start: string, end: string) =>
    request<Appointment[]>(`/api/appointments?start=${start}&end=${end}`),
  setStatus: (id: number, status: AppointmentStatus) =>
    request<Appointment>(`/api/appointments/${id}`, json('PATCH', { status })),
  publicBusiness: (slug: string) => request<PublicBusiness>(`/api/public/${slug}`),
  slots: (slug: string, serviceId: number, date: string) =>
    request<{ slots: string[] }>(`/api/public/${slug}/slots?service_id=${serviceId}&date=${date}`),
  book: (slug: string, data: Record<string, unknown>) =>
    request<Appointment>(`/api/public/${slug}/appointments`, json('POST', data)),
}

export const money = (cents: number) =>
  (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })

/** yyyy-mm-dd in local time (toISOString would shift the day in some time zones). */
export const isoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
