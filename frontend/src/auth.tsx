import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokenStore, type Me } from './api'

interface AuthState {
  me: Me | null
  loading: boolean
  signIn: (token: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(Boolean(tokenStore.get()))

  useEffect(() => {
    if (!tokenStore.get()) return
    api.me().then(setMe).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [])

  const signIn = useCallback(async (token: string) => {
    tokenStore.set(token)
    setMe(await api.me())
  }, [])

  const signOut = useCallback(() => {
    tokenStore.clear()
    setMe(null)
  }, [])

  return <AuthContext.Provider value={{ me, loading, signIn, signOut }}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
