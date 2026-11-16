import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowUp, faBell, faFilm, faGaugeHigh, faMagnifyingGlass, faRightFromBracket, faRightToBracket, faTicket, faUserShield,
} from '@fortawesome/free-solid-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { useRealtime } from '../context/RealtimeContext'
import AlertPopup from './AlertPopup'

const NAV = [
  { to: '/', label: '상영작', icon: faFilm, end: true },
  { to: '/alerts', label: '알림 설정', icon: faBell },
]

export function Logo({ className = '' }) {
  return (
    <Link to="/" className={`flex items-center gap-2 ${className}`} aria-label="movpick 홈">
      <span className="grid size-8 place-items-center rounded-lg bg-accent/15 text-accent">
        <FontAwesomeIcon icon={faTicket} />
      </span>
      <span className="title-cine text-2xl leading-none">
        MOV<span className="text-accent">PICK</span>
      </span>
    </Link>
  )
}

function LiveDot() {
  const { status } = useRealtime()
  const tone = { online: 'bg-mint', connecting: 'bg-gold', offline: 'bg-accent' }[status]
  const label = { online: '실시간 연결됨', connecting: '연결 중', offline: '연결 끊김 · 재시도 중' }[status]
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted" title={label}>
      <span className="relative flex size-2">
        {status === 'online' && <span className={`absolute inline-flex size-full animate-ping rounded-full ${tone} opacity-60`} />}
        <span className={`relative inline-flex size-2 rounded-full ${tone}`} />
      </span>
      <span className="hidden lg:inline">{status === 'online' ? 'LIVE' : label}</span>
    </span>
  )
}

function Hamburger({ open, onClick }) {
  const bar = 'absolute left-1/2 h-0.5 w-5 -translate-x-1/2 rounded bg-fg transition-all duration-300 ease-out'
  return (
    <button
      onClick={onClick}
      aria-label={open ? '메뉴 닫기' : '메뉴 열기'}
      aria-expanded={open}
      aria-controls="mobile-drawer"
      className="relative size-10 rounded-xl border border-line bg-surface-2 md:hidden"
    >
      <span className={`${bar} ${open ? 'top-1/2 -translate-y-1/2 rotate-45' : 'top-[13px]'}`} />
      <span className={`${bar} top-1/2 -translate-y-1/2 ${open ? 'scale-x-0 opacity-0' : ''}`} />
      <span className={`${bar} ${open ? 'top-1/2 -translate-y-1/2 -rotate-45' : 'top-[25px]'}`} />
    </button>
  )
}

function Drawer({ open, onClose }) {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const search = (e) => {
    e.preventDefault()
    navigate(q ? `/?q=${encodeURIComponent(q)}` : '/')
    onClose()
  }
  const items = [...NAV, ...(isAdmin ? [{ to: '/admin', label: '관리자', icon: faUserShield }] : [])]
  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity duration-300 md:hidden ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      />
      <aside
        id="mobile-drawer"
        aria-hidden={!open}
        className={`fixed inset-y-0 right-0 z-40 flex w-[82%] max-w-sm flex-col border-l border-line bg-surface px-5 pb-8 pt-20 shadow-2xl transition-transform duration-300 ease-out md:hidden ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <form onSubmit={search} className="relative">
          <FontAwesomeIcon icon={faMagnifyingGlass} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="영화 · 극장 검색" className="input pl-11" tabIndex={open ? 0 : -1} />
        </form>
        <nav className="mt-6 flex flex-col gap-1">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={onClose}
              tabIndex={open ? 0 : -1}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-4 py-3.5 text-base font-medium ${isActive ? 'bg-accent-soft text-accent' : 'text-fg hover:bg-surface-2'}`}
            >
              <FontAwesomeIcon icon={n.icon} fixedWidth />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-line pt-5">
          {user ? (
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.name}</p>
                <p className="truncate text-xs text-muted">{user.email}</p>
              </div>
              <button onClick={() => { logout(); onClose() }} className="btn-ghost" tabIndex={open ? 0 : -1}>
                <FontAwesomeIcon icon={faRightFromBracket} /> 로그아웃
              </button>
            </div>
          ) : (
            <Link to="/login" onClick={onClose} className="btn-primary w-full" tabIndex={open ? 0 : -1}>
              <FontAwesomeIcon icon={faRightToBracket} /> 로그인
            </Link>
          )}
        </div>
      </aside>
    </>
  )
}

function Header() {
  const { user, isAdmin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const link = ({ isActive }) => `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'text-fg bg-surface-2' : 'text-muted hover:text-fg'}`
  return (
    <>
    <header className={`sticky top-0 z-50 border-b transition-colors ${scrolled || open ? 'border-line bg-ink/85 backdrop-blur-xl' : 'border-transparent bg-transparent'}`}>
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 md:flex" aria-label="주요 메뉴">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={link}>
              <FontAwesomeIcon icon={n.icon} /> {n.label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink to="/admin" className={link}>
              <FontAwesomeIcon icon={faGaugeHigh} /> 관리자
            </NavLink>
          )}
        </nav>
        <div className="flex items-center gap-3">
          <LiveDot />
          <div className="hidden items-center gap-3 md:flex">
            {user ? (
              <>
                <span className="max-w-40 truncate text-sm text-muted">
                  {user.role === 'admin' && <FontAwesomeIcon icon={faUserShield} className="mr-1.5 text-gold" />}
                  {user.name}
                </span>
                <button onClick={logout} className="btn-ghost py-2" aria-label="로그아웃">
                  <FontAwesomeIcon icon={faRightFromBracket} />
                </button>
              </>
            ) : (
              <Link to="/login" className="btn-primary py-2">
                <FontAwesomeIcon icon={faRightToBracket} /> 로그인
              </Link>
            )}
          </div>
          <Hamburger open={open} onClick={() => setOpen((v) => !v)} />
        </div>
      </div>
    </header>
    <Drawer open={open} onClose={() => setOpen(false)} />
    </>
  )
}

function Footer() {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <footer className="mt-20 border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div>
          <Logo />
          <p className="mt-3 max-w-md text-sm text-muted">
            RPA 기반 영화 상영 시간표 자동 동기화 · 명당 자리 실시간 예매 추천 플랫폼
          </p>
          <p className="mt-1 text-xs text-muted/70">Team movpick · 박미금 · 김모란 · 이오리 · 홍기흥</p>
        </div>
        <div className="flex items-center gap-3">
          <a href="https://github.com/fsclass-n/movpick" target="_blank" rel="noreferrer" className="btn-ghost">
            <FontAwesomeIcon icon={faGithub} /> GitHub
          </a>
          <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="btn-ghost">
            <FontAwesomeIcon icon={faArrowUp} /> To the Top
          </button>
        </div>
      </div>
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        aria-label="맨 위로"
        className={`fixed bottom-5 right-5 z-40 grid size-12 place-items-center rounded-full bg-accent text-white shadow-xl shadow-accent/30 transition-all duration-300 hover:brightness-110 ${show ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'}`}
      >
        <FontAwesomeIcon icon={faArrowUp} />
      </button>
    </footer>
  )
}

export default function Layout() {
  return (
    <div className="cinema-bg flex min-h-dvh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 pt-6 sm:px-6">
        <Outlet />
      </main>
      <Footer />
      <AlertPopup />
    </div>
  )
}
