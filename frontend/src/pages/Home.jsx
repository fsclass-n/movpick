import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBolt, faChevronDown, faCouch, faFilm, faLocationDot, faMagnifyingGlass, faRotate } from '@fortawesome/free-solid-svg-icons'
import { Spinner } from '../components/Guards'
import Poster from '../components/Poster'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { useToast } from '../context/ToastContext'
import { api } from '../lib/api'
import { CHAINS, fmtDateTime, fmtTime, pct, ratingTone, shortRating, toDateParam } from '../lib/format'

const DAYS = [0, 1].map((offset) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return { offset, param: toDateParam(d), label: offset === 0 ? '오늘' : '내일', sub: `${d.getMonth() + 1}.${d.getDate()}` }
})

function SeatPill({ st }) {
  const ratio = st.available_seats / Math.max(1, st.total_seats)
  const tone = st.available_seats === 0 ? 'text-muted line-through' : ratio < 0.15 ? 'text-accent' : ratio < 0.4 ? 'text-gold' : 'text-mint'
  return (
    <Link to={`/showtimes/${st.id}`} className="group rounded-xl border border-line bg-surface-2 px-3 py-2 transition hover:-translate-y-0.5 hover:border-accent">
      <p className="title-cine text-xl leading-none group-hover:text-accent">{fmtTime(st.start_at)}</p>
      <p className={`mt-1 text-[11px] font-medium ${tone}`}>
        <FontAwesomeIcon icon={faCouch} className="mr-1" />{st.available_seats}/{st.total_seats}
      </p>
      <p className="mt-0.5 max-w-24 truncate text-[10px] text-muted">{st.screen}</p>
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
              <p className="mb-2 text-xs font-semibold text-muted"><FontAwesomeIcon icon={faLocationDot} className="mr-1.5 text-accent" />{theater}</p>
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
  const [q, setQ] = useState(params.get('q') || '')
  const [shows, setShows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => setQ(params.get('q') || ''), [params])

  const load = useCallback(() => {
    setError(null)
    return api('/api/showtimes', { query: { date: day, chain } }).then(setShows).catch((e) => setError(e.message))
  }, [day, chain])
  useEffect(() => { setShows(null); load() }, [load])

  useRealtimeEvent('seat_update', (m) =>
    setShows((list) => list?.map((s) => (s.id === m.showtime_id ? { ...s, available_seats: m.available_seats } : s))))
  useRealtimeEvent('crawl_finished', () => { load(); toast.info('RPA 동기화 완료 · 상영 시간표가 갱신되었습니다.') })

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
      .sort((a, b) => b.showtimes.length * (0.5 + b.rate) - a.showtimes.length * (0.5 + a.rate))
  }, [shows, q])

  const live = shows?.filter((s) => s.source === 'real').length ?? 0
  const lastSync = shows?.reduce((t, s) => (s.updated_at > t ? s.updated_at : t), '')

  return (
    <div>
      <section className="animate-fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent"><FontAwesomeIcon icon={faBolt} className="mr-1.5" />RPA SYNCED SHOWTIMES</p>
        <h1 className="title-ko mt-2 text-3xl sm:text-4xl">지금 예매 가능한 상영작</h1>
        <p className="mt-2 text-sm text-muted">
          {shows ? <>총 {shows.length}회차 · 실시간 수집 {live}회차 · 마지막 동기화 {fmtDateTime(lastSync)}</> : '상영 시간표를 불러오는 중…'}
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
