import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(tokenStore.get())
  const [loading, setLoading] = useState(Boolean(tokenStore.get()))

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) return setUser(null)
    try {
      setUser(await api('/api/auth/me'))
    } catch (e) {
      if (e.status === 401) {
        tokenStore.clear()
        setToken(null)
        setUser(null)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const acceptToken = useCallback(async (accessToken, me) => {
    tokenStore.set(accessToken)
    setToken(accessToken)
    if (me) setUser(me)
    else await refresh()
  }, [refresh])

  const login = useCallback(async (email, password) => {
    const res = await api('/api/auth/login', { method: 'POST', body: { email, password } })
    await acceptToken(res.access_token, res.user)
    return res.user
  }, [acceptToken])

  const signup = useCallback(async (payload) => {
    const res = await api('/api/auth/signup', { method: 'POST', body: payload })
    await acceptToken(res.access_token, res.user)
    return res.user
  }, [acceptToken])

  const demoLogin = useCallback(async (kind) => {
    const res = await api(`/api/auth/demo/${kind}`, { method: 'POST' })
    await acceptToken(res.access_token, res.user)
    return res.user
  }, [acceptToken])

  const logout = useCallback(() => {
    tokenStore.clear()
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, token, loading, isAdmin: user?.role === 'admin', login, signup, demoLogin, logout, refresh, acceptToken, setUser }),
    [user, token, loading, login, signup, demoLogin, logout, refresh, acceptToken],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
