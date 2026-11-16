import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBell, faBellSlash, faClockRotateLeft, faCrown, faTrash } from '@fortawesome/free-solid-svg-icons'
import { Spinner } from '../components/Guards'
import { useRealtime } from '../context/RealtimeContext'
import { useToast } from '../context/ToastContext'
import { api } from '../lib/api'
import { CHAINS, fmtDateTime } from '../lib/format'

export default function Alerts() {
  const toast = useToast()
  const { alerts, status } = useRealtime()
  const [watches, setWatches] = useState(null)
  const [perm, setPerm] = useState(typeof Notification !== 'undefined' ? Notification.permission : 'unsupported')

  const load = useCallback(() => api('/api/watches').then(setWatches).catch((e) => toast.error(e.message)), [toast])
  useEffect(() => { load() }, [load])

  const toggle = async (w) => {
    await api(`/api/watches/${w.id}`, { method: 'PATCH', query: { active: !w.active } })
    setWatches((list) => list.map((x) => (x.id === w.id ? { ...x, active: !w.active } : x)))
  }
  const remove = async (w) => {
    await api(`/api/watches/${w.id}`, { method: 'DELETE' })
    setWatches((list) => list.filter((x) => x.id !== w.id))
    toast.success('알림 설정을 삭제했습니다.')
  }

  return (
    <div className="animate-fade-up">
      <h1 className="title-ko text-3xl">알림 설정</h1>
      <p className="mt-2 text-sm text-muted">감시 중인 상영 회차의 명당 자리가 비면 WebSocket · 웹훅으로 즉시 알려드립니다.</p>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <div className="card flex items-center justify-between p-4">
          <div><p className="text-sm font-semibold">실시간 채널</p><p className="text-xs text-muted">WebSocket {status === 'online' ? '연결됨' : '재연결 중'}</p></div>
          <span className={`size-3 rounded-full ${status === 'online' ? 'bg-mint' : 'bg-gold'}`} />
        </div>
        <div className="card flex items-center justify-between p-4">
          <div><p className="text-sm font-semibold">브라우저 알림</p><p className="text-xs text-muted">탭이 백그라운드일 때 OS 알림 표시</p></div>
          {perm === 'default' ? (
            <button className="btn-ghost py-1.5 text-xs" onClick={() => Notification.requestPermission().then(setPerm)}>허용하기</button>
          ) : <span className="text-xs text-muted">{{ granted: '허용됨', denied: '차단됨', unsupported: '미지원' }[perm]}</span>}
        </div>
      </div>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-muted"><FontAwesomeIcon icon={faBell} className="mr-2" />감시 중인 회차</h2>
        {!watches ? <Spinner /> : watches.length === 0 ? (
          <div className="card mt-3 p-10 text-center text-sm text-muted">
            아직 감시 중인 회차가 없습니다.
            <div className="mt-4"><Link to="/" className="btn-primary">상영작 둘러보기</Link></div>
          </div>
        ) : (
          <ul className="mt-3 grid gap-3 md:grid-cols-2">
            {watches.map((w) => (
              <li key={w.id} className={`card p-4 transition ${w.active ? '' : 'opacity-60'}`}>
                <div className="flex items-start justify-between gap-3">
                  <Link to={`/showtimes/${w.showtime_id}`} className="min-w-0 hover:text-accent">
                    <p className="text-[11px] font-semibold" style={{ color: CHAINS[w.showtime.chain]?.color }}>{CHAINS[w.showtime.chain]?.label}</p>
                    <p className="title-ko truncate text-lg">{w.showtime.movie_title}</p>
                    <p className="truncate text-xs text-muted">{w.showtime.theater} {w.showtime.screen} · {fmtDateTime(w.showtime.start_at)}</p>
                  </Link>
                  <div className="flex shrink-0 gap-1">
                    <button onClick={() => toggle(w)} className="btn-ghost size-9 p-0" aria-label={w.active ? '알림 끄기' : '알림 켜기'}>
                      <FontAwesomeIcon icon={w.active ? faBell : faBellSlash} className={w.active ? 'text-gold' : ''} />
                    </button>
                    <button onClick={() => remove(w)} className="btn-ghost size-9 p-0 hover:text-accent" aria-label="삭제"><FontAwesomeIcon icon={faTrash} /></button>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="chip py-1">{w.mode === 'prime' ? <><FontAwesomeIcon icon={faCrown} className="text-gold" /> 명당 전체</> : `선택 좌석 ${w.seats?.join(', ')}`}</span>
                  {(w.channels || []).map((c) => <span key={c} className="chip py-1 text-muted">{c}</span>)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-muted"><FontAwesomeIcon icon={faClockRotateLeft} className="mr-2" />이번 세션 수신 알림</h2>
        {alerts.length === 0 ? <p className="mt-3 text-sm text-muted/70">아직 수신된 알림이 없습니다.</p> : (
          <ul className="mt-3 divide-y divide-line overflow-hidden rounded-2xl border border-line">
            {alerts.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-3 bg-surface/60 px-4 py-3 text-sm">
                <Link to={`/showtimes/${a.showtime_id}`} className="min-w-0 truncate hover:text-accent">{a.movie_title} · <span className="text-gold">{a.seats.join(', ')}</span></Link>
                <span className="shrink-0 text-xs text-muted">{fmtDateTime(a.received_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
