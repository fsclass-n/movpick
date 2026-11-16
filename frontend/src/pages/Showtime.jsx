import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowLeft, faArrowUpRightFromSquare, faBell, faCircleInfo, faCrown, faEnvelope, faFire, faGlobe, faLocationDot, faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons'
import { faDiscord, faTelegram } from '@fortawesome/free-brands-svg-icons'
import SeatMap from '../components/SeatMap'
import { Spinner } from '../components/Guards'
import { useAuth } from '../context/AuthContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { useToast } from '../context/ToastContext'
import { api } from '../lib/api'
import { CHAINS, fmtDateTime, fmtTime } from '../lib/format'
import { Poster } from './Home'

const CHANNELS = [
  { id: 'web', label: '웹 푸시', icon: faGlobe },
  { id: 'telegram', label: '텔레그램', icon: faTelegram },
  { id: 'discord', label: '디스코드', icon: faDiscord },
  { id: 'email', label: '이메일', icon: faEnvelope },
]

export default function Showtime() {
  const { id } = useParams()
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState([])
  const [heatmap, setHeatmap] = useState(false)
  const [flash, setFlash] = useState([])
  const [channels, setChannels] = useState(['web'])
  const [available, setAvailable] = useState({ web: true })
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => api(`/api/showtimes/${id}/seats`).then(setData).catch((e) => setError(e.message)), [id])
  useEffect(() => { load() }, [load])
  useEffect(() => { api('/api/watches/channels').then(setAvailable).catch(() => {}) }, [])

  useRealtimeEvent('seat_update', (m) => {
    if (String(m.showtime_id) !== String(id)) return
    setData((d) => {
      if (!d) return d
      const free = new Set(Object.keys(d.scores).filter((s) => !m.taken.includes(s)))
      const primeFree = d.prime.filter((s) => free.has(s)).sort((a, b) => d.scores[b] - d.scores[a])
      return { ...d, taken: m.taken, prime_free: primeFree, recommended: primeFree.slice(0, 4), showtime: { ...d.showtime, available_seats: m.available_seats } }
    })
    setSelected((sel) => sel.filter((s) => !m.taken.includes(s)))
    if (m.freed.length) {
      setFlash(m.freed)
      setTimeout(() => setFlash([]), 4000)
    }
  })

  if (error) return <div className="card p-10 text-center text-sm text-muted">{error}<div className="mt-4"><Link to="/" className="btn-ghost">상영작 목록</Link></div></div>
  if (!data) return <Spinner label="좌석 배치도를 불러오는 중" />

  const st = data.showtime
  const toggle = (seat, { isTaken }) => {
    if (isTaken && !user) return toast.info('예매된 좌석입니다. 로그인하면 취소표 알림을 받을 수 있어요.')
    setSelected((s) => (s.includes(seat) ? s.filter((x) => x !== seat) : s.length >= 20 ? s : [...s, seat]))
  }

  const watch = async (mode) => {
    if (!user) return navigate('/login', { state: { from: `/showtimes/${id}` } })
    setSaving(true)
    try {
      if (channels.includes('web') && 'Notification' in window && Notification.permission === 'default') Notification.requestPermission()
      const res = await api('/api/watches', { method: 'POST', body: { showtime_id: st.id, mode, seats: mode === 'custom' ? selected : [], channels } })
      toast.success(mode === 'prime' ? '명당 자리 잔여석 감시를 시작했습니다.' : `선택한 ${selected.length}개 좌석 감시를 시작했습니다.`, {
        description: res.available_now.length ? `현재 비어있는 대상 좌석: ${res.available_now.slice(0, 8).join(', ')}` : '좌석이 비는 즉시 실시간으로 알려드려요.',
      })
    } catch (e) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="animate-fade-up">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg"><FontAwesomeIcon icon={faArrowLeft} /> 상영작 목록</Link>

      <header className="mt-4 flex gap-4">
        <Poster url={st.poster_url} title={st.movie_title} className="hidden aspect-[2/3] w-24 shrink-0 rounded-xl sm:block" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: `${CHAINS[st.chain]?.color}26`, color: CHAINS[st.chain]?.color }}>{CHAINS[st.chain]?.label}</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${st.source === 'real' ? 'bg-mint/15 text-mint' : 'bg-surface-2 text-muted'}`}>{st.source === 'real' ? 'RPA LIVE' : 'MOCK'}</span>
          </div>
          <h1 className="title-ko mt-2 text-2xl sm:text-3xl">{st.movie_title}</h1>
          <p className="mt-1 text-sm text-muted"><FontAwesomeIcon icon={faLocationDot} className="mr-1.5 text-accent" />{st.theater} · {st.screen}</p>
          <p className="mt-1 text-sm"><span className="title-cine text-xl">{fmtTime(st.start_at)}</span>{st.end_at && <span className="text-muted"> ~ {fmtTime(st.end_at)}</span>} <span className="text-muted">· {fmtDateTime(st.start_at).split(' ')[0]}</span></p>
        </div>
      </header>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <section className="card p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm"><span className="title-cine text-2xl text-mint">{st.available_seats}</span><span className="text-muted"> / {st.total_seats}석 잔여</span></p>
            <button onClick={() => setHeatmap((v) => !v)} className={`chip ${heatmap ? 'border-gold text-gold' : 'text-muted'}`}>
              <FontAwesomeIcon icon={faFire} /> 명당 히트맵
            </button>
          </div>
          <SeatMap data={data} selected={selected} onToggle={toggle} heatmap={heatmap} flash={flash} />
          {data.estimated && (
            <p className="mt-5 text-center text-[11px] text-muted/80">
              <FontAwesomeIcon icon={faCircleInfo} className="mr-1" />잔여석 수는 영화관에서 실시간 수집된 값이며, 좌석 단위 배치는 잔여석 수를 기반으로 추정한 값입니다.
            </p>
          )}
        </section>

        <aside className="space-y-4">
          <div className="card p-5">
            <p className="flex items-center gap-2 text-sm font-semibold"><FontAwesomeIcon icon={faWandMagicSparkles} className="text-gold" /> 명당 자리 추천</p>
            <p className="mt-1 text-xs text-muted">스크린 기준 약 2/3 지점 · 중앙 열 좌석일수록 높은 점수</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.recommended.length ? data.recommended.map((s) => (
                <button key={s} onClick={() => toggle(s, {})} className={`rounded-lg border px-2.5 py-1 font-mono text-sm ${selected.includes(s) ? 'border-accent bg-accent text-white' : 'border-gold/50 bg-gold-soft text-gold'}`}>{s}</button>
              )) : <span className="text-xs text-muted">현재 비어있는 좌석이 없습니다.</span>}
            </div>
            <p className="mt-3 text-xs text-muted"><FontAwesomeIcon icon={faCrown} className="mr-1 text-gold" />명당 잔여 {data.prime_free.length} / {data.prime.length}석</p>
          </div>

          <div className="card p-5">
            <p className="flex items-center gap-2 text-sm font-semibold"><FontAwesomeIcon icon={faBell} className="text-accent" /> 잔여석 실시간 알림</p>
            <p className="mt-1 text-xs text-muted">취소표가 발생하면 RPA 모니터가 감지해 즉시 알려드립니다.</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {CHANNELS.map((c) => {
                const on = channels.includes(c.id)
                const disabled = !available[c.id]
                return (
                  <label key={c.id} className={`chip cursor-pointer justify-center py-2 ${on ? 'border-accent bg-accent-soft text-fg' : 'text-muted'} ${disabled ? 'cursor-not-allowed opacity-40' : ''}`} title={disabled ? '서버에 웹훅이 설정되지 않았습니다' : ''}>
                    <input type="checkbox" className="sr-only" disabled={disabled} checked={on}
                      onChange={() => setChannels((ch) => (on ? ch.filter((x) => x !== c.id) : [...ch, c.id]))} />
                    <FontAwesomeIcon icon={c.icon} /> {c.label}
                  </label>
                )
              })}
            </div>
            <div className="mt-4 grid gap-2">
              <button onClick={() => watch('prime')} disabled={saving} className="btn-primary"><FontAwesomeIcon icon={faCrown} /> 명당 자리 전체 감시</button>
              <button onClick={() => watch('custom')} disabled={saving || !selected.length} className="btn-ghost">
                선택 좌석 감시 {selected.length > 0 && <span className="rounded bg-accent px-1.5 text-xs text-white">{selected.length}</span>}
              </button>
            </div>
          </div>

          <a href={st.booking_url || '#'} target="_blank" rel="noreferrer" className="btn-ghost w-full py-3">
            {CHAINS[st.chain]?.label}에서 예매하기 <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
          </a>
        </aside>
      </div>
    </div>
  )
}
