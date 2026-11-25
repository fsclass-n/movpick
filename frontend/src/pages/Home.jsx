import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBolt, faCalendarDays, faChevronDown, faChevronLeft, faChevronRight, faCouch, faFilm, faLocationDot, faMagnifyingGlass, faRotate } from '@fortawesome/free-solid-svg-icons'
import { Spinner } from '../components/Guards'
import Poster from '../components/Poster'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { useToast } from '../context/ToastContext'
import { api } from '../lib/api'
import { CHAINS, REGIONS, WEEKDAYS, fmtDateTime, fmtTime, fromDateParam, pct, ratingTone, shortRating, toDateParam } from '../lib/format'

const DAYS = [0, 1].map((offset) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return { offset, param: toDateParam(d), label: offset === 0 ? '오늘' : '내일', sub: `${d.getMonth() + 1}.${d.getDate()}` }
})
const MAX_PICK_DAYS = 6 // 달력에서 고를 수 있는 최대 범위 (오늘 + 6일)

function DateMenu({ day, onPick }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const sel = fromDateParam(day)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const max = new Date(today); max.setDate(max.getDate() + MAX_PICK_DAYS)
  const monthStart = (d) => new Date(d.getFullYear(), d.getMonth(), 1)
  const [view, setView] = useState(() => monthStart(sel))
  const isCustom = !DAYS.some((d) => d.param === day)

  useEffect(() => {
    if (!open) return
    setView(monthStart(sel))
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const esc = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const cells = useMemo(() => {
    const pad = view.getDay()
    const last = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate()
    return [...Array(pad).fill(null), ...Array.from({ length: last }, (_, i) => new Date(view.getFullYear(), view.getMonth(), i + 1))]
  }, [view])
  const canPrev = monthStart(new Date(view.getFullYear(), view.getMonth() - 1, 1)) >= monthStart(today)
  const canNext = monthStart(new Date(view.getFullYear(), view.getMonth() + 1, 1)) <= monthStart(max)

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="dialog"
        className={`chip ${isCustom ? 'border-accent bg-accent-soft text-accent' : 'text-muted hover:text-fg'}`}>
        <FontAwesomeIcon icon={faCalendarDays} />
        {sel.getMonth() + 1}/{sel.getDate()} ({WEEKDAYS[sel.getDay()]})
      </button>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-2 w-72 rounded-2xl border border-line bg-surface p-3 shadow-2xl shadow-black/60">
          <div className="flex items-center justify-between pb-2">
            <button onClick={() => canPrev && setView(monthStart(new Date(view.getFullYear(), view.getMonth() - 1, 1)))}
              disabled={!canPrev} aria-label="이전 달" className="rounded-lg p-1.5 text-muted transition hover:bg-surface-2 hover:text-fg disabled:opacity-30">
              <FontAwesomeIcon icon={faChevronLeft} /></button>
            <p className="text-sm font-bold">{view.getFullYear()}년 {view.getMonth() + 1}월</p>
            <button onClick={() => canNext && setView(monthStart(new Date(view.getFullYear(), view.getMonth() + 1, 1)))}
              disabled={!canNext} aria-label="다음 달" className="rounded-lg p-1.5 text-muted transition hover:bg-surface-2 hover:text-fg disabled:opacity-30">
              <FontAwesomeIcon icon={faChevronRight} /></button>
          </div>
          <div className="grid grid-cols-7 text-center text-[11px] font-semibold text-muted">
            {WEEKDAYS.map((w, i) => <span key={w} className={`py-1 ${i === 0 ? 'text-accent/80' : ''}`}>{w}</span>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) => !d ? <span key={i} /> : (
              <button key={i} disabled={d < today || d > max}
                onClick={() => { onPick(toDateParam(d)); setOpen(false) }}
                className={`rounded-lg py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-25 ${
                  toDateParam(d) === day ? 'bg-accent font-bold text-white'
                    : toDateParam(d) === toDateParam(today) ? 'border border-gold/50 text-gold'
                      : 'text-fg hover:bg-surface-2'}`}>
                {d.getDate()}
              </button>
            ))}
          </div>
          <p className="mt-2 border-t border-line/60 pt-2 text-center text-[10px] text-muted">수집된 기간 내의 날짜만 상영 정보가 표시됩니다</p>
        </div>
      )}
    </div>
  )
}

function SeatPill({ st }) {
  const ratio = st.available_seats / Math.max(1, st.total_seats)
  const tone = st.available_seats === 0 ? 'text-muted line-through' : ratio < 0.15 ? 'text-accent' : ratio < 0.4 ? 'text-gold' : 'text-mint'
  return (
    <Link to={`/showtimes/${st.id}`} className="group rounded-xl border border-line bg-surface-2 px-3 py-2 transition hover:-translate-y-0.5 hover:border-accent">
      <p className="title-cine text-xl leading-none group-hover:text-accent">{fmtTime(st.start_at)}</p>
      <p className={`mt-1 text-[11px] font-medium ${tone}`}>
        <FontAwesomeIcon icon={faCouch} className="mr-1" />{st.available_seats}/{st.total_seats}
      </p>
      <p className="mt-0.5 max-w-24 truncate text-[10px] text-muted">{st.source !== 'real' && <span className="mr-1 font-semibold text-gold/80">DEMO</span>}{st.screen}</p>
    </Link>
  )
}

function MovieCard({ movie, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  const byTheater = useMemo(() => {
    const m = new Map()
    movie.showtimes.forEach((s) => m.set(s.theater, [...(m.get(s.theater) || []), s]))
    return [...m.entries()]
  }, [movie.showtimes])
  return (
    <article className="card overflow-hidden animate-fade-up">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-stretch gap-4 p-4 text-left">
        <Poster url={movie.poster} title={movie.title} className="aspect-[2/3] w-20 shrink-0 rounded-lg sm:w-24" />
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start gap-2">
            {movie.rating && <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${ratingTone(movie.rating)}`}>{shortRating(movie.rating)}</span>}
            <h3 className="title-ko text-lg leading-snug sm:text-xl">{movie.title}</h3>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {movie.chains.map((c) => (
              <span key={c} className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: `${CHAINS[c]?.color}26`, color: CHAINS[c]?.color }}>{CHAINS[c]?.label || c}</span>
            ))}
            <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] text-muted">{movie.showtimes.length}회차</span>
          </div>
          <div className="mt-auto pt-3">
            <div className="flex justify-between text-xs text-muted"><span>예매율</span><span className="font-semibold text-gold">{pct(movie.rate)}</span></div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-gradient-to-r from-accent to-gold" style={{ width: `${Math.max(3, movie.rate * 100)}%` }} />
            </div>
          </div>
        </div>
        <FontAwesomeIcon icon={faChevronDown} className={`mt-1 text-muted transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="space-y-4 border-t border-line px-4 py-4">
          {byTheater.map(([theater, list]) => (
            <div key={theater}>
              <p className="mb-2 flex items-center text-xs font-semibold text-muted">
                <FontAwesomeIcon icon={faLocationDot} className="mr-1.5 text-accent" />{theater}
                {list[0].region && REGIONS[list[0].region] && (
                  <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-muted">{REGIONS[list[0].region].label}</span>
                )}
              </p>
              <div className="flex flex-wrap gap-2">{list.map((s) => <SeatPill key={s.id} st={s} />)}</div>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

export default function Home() {
  const [params, setParams] = useSearchParams()
  const toast = useToast()
  const [day, setDay] = useState(DAYS[0].param)
  const [chain, setChain] = useState('')
  const [region, setRegion] = useState('')
  const [theater, setTheater] = useState('')
  const [theaters, setTheaters] = useState([])
  const [q, setQ] = useState(params.get('q') || '')
  const [shows, setShows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => setQ(params.get('q') || ''), [params])

  const load = useCallback(() => {
    setError(null)
    return api('/api/showtimes', { query: { date: day, chain, region, theater } }).then(setShows).catch((e) => setError(e.message))
  }, [day, chain, region, theater])
  useEffect(() => { setShows(null); load() }, [load])

  const loadTheaters = useCallback(() => api('/api/theaters').then(setTheaters).catch(() => {}), [])
  useEffect(() => { loadTheaters() }, [loadTheaters])

  const theaterOptions = useMemo(
    () => theaters.filter((t) => (!region || t.region === region) && (!chain || t.chain === chain)),
    [theaters, region, chain])
  useEffect(() => {  // 지역·체인이 바뀌어 목록에서 벗어난 극장은 선택 해제
    if (theater && !theaterOptions.some((t) => t.theater === theater)) setTheater('')
  }, [theaterOptions, theater])

  const pickTheater = (name) => {
    setTheater(name)
    const t = theaters.find((t) => t.theater === name)
    if (t?.region && t.region !== region) setRegion(t.region)
  }

  useRealtimeEvent('seat_update', (m) =>
    setShows((list) => list?.map((s) => (s.id === m.showtime_id ? { ...s, available_seats: m.available_seats } : s))))
  useRealtimeEvent('crawl_finished', () => { load(); loadTheaters(); toast.info('RPA 동기화 완료 · 상영 시간표가 갱신되었습니다.') })

  const movies = useMemo(() => {
    if (!shows) return []
    const needle = q.trim().toLowerCase()
    const map = new Map()
    shows
      .filter((s) => !needle || s.movie_title.toLowerCase().includes(needle) || s.theater.toLowerCase().includes(needle))
      .forEach((s) => {
        const m = map.get(s.movie_title) || { title: s.movie_title, rating: s.rating, poster: null, chains: new Set(), showtimes: [], total: 0, avail: 0 }
        m.poster ||= s.poster_url
        m.chains.add(s.chain)
        m.showtimes.push(s)
        m.total += s.total_seats
        m.avail += s.available_seats
        map.set(s.movie_title, m)
      })
    return [...map.values()]
      .map((m) => ({ ...m, chains: [...m.chains], rate: 1 - m.avail / Math.max(1, m.total) }))
      .map((m) => ({ ...m, real: m.showtimes.some((s) => s.source === 'real') }))
      .sort((a, b) => (b.real - a.real) || b.showtimes.length * (0.5 + b.rate) - a.showtimes.length * (0.5 + a.rate))
  }, [shows, q])

  const live = shows?.filter((s) => s.source === 'real').length ?? 0
  const lastSync = shows?.reduce((t, s) => (s.updated_at > t ? s.updated_at : t), '')

  return (
    <div>
      <section className="animate-fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent"><FontAwesomeIcon icon={faBolt} className="mr-1.5" />RPA SYNCED SHOWTIMES</p>
        <h1 className="title-ko mt-2 text-3xl sm:text-4xl">지금 예매 가능한 상영작</h1>
        <p className="mt-2 text-sm text-muted">
          {shows ? <>총 {shows.length}회차 · 실시간 수집 {live}회차{shows.length > live && <> · 데모 {shows.length - live}회차</>} · 마지막 동기화 {fmtDateTime(lastSync)}</> : '상영 시간표를 불러오는 중…'}
        </p>
      </section>

      <section className="sticky top-16 z-20 -mx-5 mt-6 border-b border-line bg-ink/85 px-5 py-3 backdrop-blur-xl sm:mx-0 sm:rounded-2xl sm:border sm:px-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="flex gap-2">
            {DAYS.map((d) => (
              <button key={d.param} onClick={() => setDay(d.param)} className={`chip ${day === d.param ? 'border-accent bg-accent-soft text-accent' : 'text-muted hover:text-fg'}`}>
                {d.label} <span className="opacity-70">{d.sub}</span>
              </button>
            ))}
            <DateMenu day={day} onPick={setDay} />
          </div>
          <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-0.5">
            {[['', '전체'], ...Object.entries(CHAINS).map(([k, v]) => [k, v.label])].map(([k, label]) => (
              <button key={k || 'all'} onClick={() => setChain(k)} className={`chip shrink-0 ${chain === k ? 'border-fg/60 bg-surface-2 text-fg' : 'text-muted hover:text-fg'}`}>
                {k && <span className="size-2 rounded-full" style={{ background: CHAINS[k].color }} />}{label}
              </button>
            ))}
          </div>
          <div className="relative lg:ml-auto lg:w-72">
            <FontAwesomeIcon icon={faMagnifyingGlass} className="absolute left-4 top-1/2 -translate-y-1/2 text-sm text-muted" />
            <input value={q} onChange={(e) => { setQ(e.target.value); setParams(e.target.value ? { q: e.target.value } : {}, { replace: true }) }}
              placeholder="영화 · 극장 검색" className="input py-2.5 pl-10" aria-label="영화 또는 극장 검색" />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/60 pt-3">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-muted"><FontAwesomeIcon icon={faLocationDot} className="mr-1" />지역</span>
          {[['', '전체'], ...Object.keys(REGIONS).map((k) => [k, REGIONS[k].label])].map(([k, label]) => (
            <button key={k || 'all'} onClick={() => { setRegion(k); setTheater('') }}
              className={`chip ${region === k ? 'border-accent bg-accent-soft text-accent' : 'text-muted hover:text-fg'}`}>
              {label}
            </button>
          ))}
          <div className="relative ml-auto">
            <select value={theater} onChange={(e) => pickTheater(e.target.value)} aria-label="극장 선택"
              className="chip appearance-none border-line bg-surface pr-8 text-fg outline-none transition focus:border-accent">
              <option value="">극장 전체{region || chain ? ` (${theaterOptions.length})` : ''}</option>
              {theaterOptions.map((t) => <option key={t.theater} value={t.theater}>{t.theater}</option>)}
            </select>
            <FontAwesomeIcon icon={faChevronDown} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-muted" />
          </div>
        </div>
      </section>

      <section className="mt-6">
        {error ? (
          <div className="card p-10 text-center">
            <p className="text-sm text-muted">{error}</p>
            <button onClick={load} className="btn-ghost mt-4"><FontAwesomeIcon icon={faRotate} /> 다시 시도</button>
          </div>
        ) : !shows ? <Spinner label="상영 시간표 동기화 데이터를 불러오는 중" /> : movies.length === 0 ? (
          <div className="card p-12 text-center text-muted">
            <FontAwesomeIcon icon={faFilm} size="2x" />
            <p className="mt-3 text-sm">조건에 맞는 상영 회차가 없습니다.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {movies.map((m, i) => <MovieCard key={m.title} movie={m} defaultOpen={i < 2} />)}
          </div>
        )}
      </section>
    </div>
  )
}
