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
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5 sm:px-8 lg:px-10">
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
            ) : pathname !== '/login' && (
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

const FOOTER_LINKS = [
  {
    title: '서비스',
    links: [
      { label: '상영작 · 시간표', to: '/' },
      { label: '명당 자리 알림', to: '/alerts' },
      { label: '로그인 · 회원가입', to: '/login' },
    ],
  },
  {
    title: '제휴 영화관',
    links: [
      { label: 'CGV', href: 'https://cgv.co.kr' },
      { label: '메가박스', href: 'https://www.megabox.co.kr' },
      { label: '롯데시네마', href: 'https://www.lottecinema.co.kr' },
    ],
  },
  {
    title: '프로젝트',
    links: [
      { label: '프로젝트 안내', href: 'https://fsclass-n.github.io/movpick/' },
      { label: 'API 문서', href: 'https://movpick-api.onrender.com/docs' },
      { label: 'GitHub', href: 'https://github.com/fsclass-n/movpick' },
    ],
  },
]

function Footer() {
  const linkCls = 'text-sm text-muted transition hover:text-fg'
  return (
    <footer className="mt-24 border-t border-line bg-ink/60">
      <div className="mx-auto grid max-w-7xl grid-cols-3 gap-x-6 gap-y-10 px-5 py-12 sm:px-8 md:grid-cols-[1.4fr_repeat(3,1fr)] lg:px-10">
        <div className="col-span-3 max-w-sm md:col-span-1">
          <Logo />
          <p className="mt-4 text-sm leading-relaxed text-muted">
            멀티플렉스 상영 시간표와 잔여석을 RPA로 자동 동기화하고, 명당 자리에 취소표가 생기는 순간 실시간으로 알려드립니다.
          </p>
          <div className="mt-5 flex gap-2">
            <a href="https://github.com/fsclass-n/movpick" target="_blank" rel="noreferrer" aria-label="GitHub"
              className="grid size-9 place-items-center rounded-full border border-line text-muted transition hover:border-fg/40 hover:text-fg">
              <FontAwesomeIcon icon={faGithub} />
            </a>
          </div>
        </div>
        {FOOTER_LINKS.map((col) => (
          <nav key={col.title} aria-label={col.title}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-fg/80">{col.title}</p>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.label}>
                  {l.to ? <Link to={l.to} className={linkCls}>{l.label}</Link>
                    : <a href={l.href} target="_blank" rel="noreferrer" className={linkCls}>{l.label}</a>}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-6 text-xs text-muted/80 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-10">
          <div className="space-y-1">
            <p>팀 movpick <span className="mx-1.5 text-line">|</span> 조장 박미금 <span className="mx-1.5 text-line">|</span> 팀원 김모란 · 이오리 · 홍기흥</p>
            <p>상영 정보와 잔여석은 각 영화관의 공개 데이터를 RPA로 수집한 값으로, 실제 예매 화면과 차이가 있을 수 있습니다.</p>
          </div>
          <p className="shrink-0">© {new Date().getFullYear()} movpick. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}

function ToTop() {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="맨 위로"
      className={`fixed bottom-5 right-5 z-40 grid size-12 place-items-center rounded-full bg-accent text-white shadow-xl shadow-accent/30 transition-all duration-300 hover:-translate-y-0.5 hover:brightness-110 sm:bottom-8 sm:right-8 ${show ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'}`}
    >
      <FontAwesomeIcon icon={faArrowUp} />
    </button>
  )
}

/** bare: 전체 폭(full-bleed) 페이지용 — 헤더/푸터는 동일하게 유지하고 본문 컨테이너만 제거 */
export default function Layout({ bare = false }) {
  return (
    <div className="cinema-bg flex min-h-dvh flex-col">
      <Header />
      <main className={bare ? 'flex w-full flex-1 flex-col' : 'mx-auto w-full max-w-7xl flex-1 px-5 pt-6 sm:px-8 lg:px-10'}>
        <Outlet />
      </main>
      <Footer />
      <ToTop />
      <AlertPopup />
    </div>
  )
}
