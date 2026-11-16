import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { WS_URL } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import { useAuth } from './AuthContext'
import { useToast } from './ToastContext'

const RealtimeContext = createContext(null)

/** WebSocket 실시간 채널: 잔여석 알림(seat_alert) · 좌석 변동(seat_update) · 크롤링 상태 · 권한 변경 */
export function RealtimeProvider({ children }) {
  const { token, refresh } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [status, setStatus] = useState('connecting')
  const [alerts, setAlerts] = useState([])
  const [popup, setPopup] = useState(null)
  const listeners = useRef(new Set())

  const subscribe = useCallback((fn) => {
    listeners.current.add(fn)
    return () => listeners.current.delete(fn)
  }, [])

  const handle = useCallback((msg) => {
    listeners.current.forEach((fn) => fn(msg))
    if (msg.type === 'seat_alert') {
      const item = { ...msg, received_at: new Date().toISOString() }
      setAlerts((a) => [item, ...a].slice(0, 50))
      setPopup(item)
      toast.alert(`명당 자리 잔여석 발생! ${msg.seats.slice(0, 4).join(', ')}`, {
        description: `${msg.movie_title}\n${msg.theater} ${msg.screen} · ${fmtDateTime(msg.start_at)}`,
        action: { label: '좌석 보러가기', onClick: () => navigate(`/showtimes/${msg.showtime_id}`) },
      })
      if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
        new Notification('movpick 명당 자리 알림', { body: `${msg.movie_title} · ${msg.seats.join(', ')}`, icon: '/favicon.svg' })
      }
    } else if (msg.type === 'role_changed') {
      refresh()
      toast.info(`회원 권한이 '${msg.role === 'admin' ? '관리자' : '일반 사용자'}'(으)로 변경되었습니다.`)
    }
  }, [navigate, refresh, toast])

  const handleRef = useRef(handle)
  handleRef.current = handle

  useEffect(() => {
    let ws, retry = 0, pingTimer, retryTimer, closed = false
    const connect = () => {
      setStatus('connecting')
      ws = new WebSocket(token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL)
      ws.onopen = () => {
        retry = 0
        setStatus('online')
        pingTimer = setInterval(() => ws.readyState === 1 && ws.send(JSON.stringify({ type: 'ping' })), 25000)
      }
      ws.onmessage = (e) => {
        try { handleRef.current(JSON.parse(e.data)) } catch { /* ignore malformed */ }
      }
      ws.onclose = () => {
        clearInterval(pingTimer)
        if (closed) return
        setStatus('offline')
        retryTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++))
      }
    }
    connect()
    return () => {
      closed = true
      clearInterval(pingTimer)
      clearTimeout(retryTimer)
      ws?.close()
    }
  }, [token])

  const value = useMemo(
    () => ({ status, alerts, popup, closePopup: () => setPopup(null), subscribe }),
    [status, alerts, popup, subscribe],
  )
  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>
}

export const useRealtime = () => useContext(RealtimeContext)

export function useRealtimeEvent(type, handler) {
  const { subscribe } = useRealtime()
  const ref = useRef(handler)
  ref.current = handler
  useEffect(() => subscribe((msg) => msg.type === type && ref.current(msg)), [subscribe, type])
}
