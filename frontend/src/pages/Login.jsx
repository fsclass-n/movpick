import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight, faCheck, faCircleNotch, faComment, faCouch, faEnvelope, faEye, faEyeSlash, faLock, faRobot, faUser, faUserShield, faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { faGoogle } from '@fortawesome/free-brands-svg-icons'
import { Logo } from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { api, oauthLoginUrl } from '../lib/api'
import { PASSWORD_RULES, isValidEmail, isValidPassword, pct } from '../lib/format'

const DEMO = {
  user: { email: 'user@movpick.app', password: 'Movpick!2026' },
  admin: { email: 'admin@movpick.app', password: 'Admin!2026' },
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function useBookingStats() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    let alive = true
    const load = () => api('/api/stats/booking-rates').then((d) => alive && setStats(d)).catch(() => {})
    load()
    const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  return stats
}

function CinematicPanel() {
  const stats = useBookingStats()
  const movies = stats?.movies?.length ? stats.movies : [1, 2, 3, 4, 5].map((i) => ({ name: '데이터 동기화 중…', rate: 0.1 * i, ph: true }))
  const marquee = (stats?.movies || []).map((m) => m.name)
  return (
    <section className="relative overflow-hidden border-b border-line md:border-b-0 md:border-r">
      <div className="absolute inset-0 bg-[radial-gradient(800px_400px_at_20%_0%,#ff3d5740,transparent_60%),radial-gradient(600px_400px_at_100%_100%,#f5c51822,transparent_60%)]" />
      <div className="relative flex h-full flex-col p-6 sm:p-8 lg:p-12">
        <Logo />
        <div className="mt-6 md:mt-auto">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-accent">RPA · REAL-TIME · PRIME SEAT</p>
          <h1 className="title-ko mt-3 text-3xl leading-tight sm:text-4xl lg:text-5xl">
            명당 자리가 비는 순간,<br className="hidden sm:block" /> <span className="text-gold">가장 먼저</span> 알려드려요
          </h1>
          <p className="mt-3 hidden max-w-md text-sm text-muted sm:block">
            CGV · 메가박스 · 롯데시네마의 상영 시간표와 잔여석을 Playwright RPA가 자동 수집하고, 취소표가 생기면 WebSocket으로 즉시 알림을 보냅니다.
          </p>
        </div>

        {/* 모바일: 핵심 지표만 한 줄로 → 스크롤 최소화 */}
        <div className="mt-5 grid grid-cols-3 gap-2 md:hidden">
          <Stat label="오늘 회차" value={stats?.totals.showtimes ?? '-'} />
          <Stat label="잔여석" value={stats ? stats.totals.available.toLocaleString() : '-'} />
          <Stat label="실시간 수집" value={stats ? pct(stats.live_ratio) : '-'} />
        </div>

        <div className="mt-10 hidden md:block">
          <div className="card p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold"><FontAwesomeIcon icon={faRobot} className="mr-2 text-accent" />실시간 예매율 TOP 5</p>
              <span className="flex items-center gap-1.5 text-xs text-mint"><span className="size-1.5 animate-pulse rounded-full bg-mint" /> LIVE</span>
            </div>
            <ul className="mt-4 space-y-3">
              {movies.map((m, i) => (
                <li key={m.name + i} className={m.ph ? 'animate-pulse opacity-50' : ''}>
                  <div className="flex justify-between text-xs">
                    <span className="truncate pr-3"><span className="title-cine mr-2 text-base text-muted">{i + 1}</span>{m.name}</span>
                    <span className="font-semibold text-gold">{pct(m.rate)}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                    <div className="h-full rounded-full bg-gradient-to-r from-accent to-gold transition-all duration-1000" style={{ width: `${Math.max(4, m.rate * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
            <div className="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4">
              {(stats?.chains || []).map((c) => <Stat key={c.name} label={c.name} value={pct(c.rate)} />)}
            </div>
          </div>
          {marquee.length > 0 && (
            <div className="film-strip mt-6 overflow-hidden rounded-lg border-y-4 border-dashed border-line/80 py-2">
              <div className="flex w-max animate-film gap-8 whitespace-nowrap text-sm text-muted">
                {[...marquee, ...marquee].map((t, i) => <span key={i}><FontAwesomeIcon icon={faCouch} className="mr-2 text-gold/70" />{t}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl bg-surface-2/80 px-3 py-2">
      <p className="truncate text-[11px] text-muted">{label}</p>
      <p className="title-cine text-xl leading-tight">{value}</p>
    </div>
  )
}

const SOCIAL = [
  { id: 'google', label: 'Google', cls: 'bg-white text-neutral-800 hover:bg-neutral-100', icon: <FontAwesomeIcon icon={faGoogle} /> },
  { id: 'naver', label: '네이버', cls: 'bg-[#03C75A] text-white hover:brightness-105', icon: <span className="font-black">N</span> },
  { id: 'kakao', label: '카카오', cls: 'bg-[#FEE500] text-[#191600] hover:brightness-95', icon: <FontAwesomeIcon icon={faComment} /> }, // FA 무료 세트에 카카오 로고가 없어 말풍선 사용
]

export default function Login() {
  const { login, signup, demoLogin, user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', name: '', confirm: '' })
  const [showPw, setShowPw] = useState(false)
  const [busy, setBusy] = useState(null)
  const [touched, setTouched] = useState({})
  const [providers, setProviders] = useState({})

  useEffect(() => { api('/api/auth/providers').then(setProviders).catch(() => {}) }, [])
  const manual = useRef(false) // 직접 로그인 시에는 go()가 이동을 담당 (이미 로그인된 상태로 진입한 경우만 자동 이동)
  useEffect(() => { if (user && !manual.current) navigate(location.state?.from || '/', { replace: true }) }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const isSignup = mode === 'signup'
  const emailOk = isValidEmail(form.email)
  const pwOk = isSignup ? isValidPassword(form.password) : form.password.length > 0
  const confirmOk = !isSignup || form.password === form.confirm
  const canSubmit = emailOk && pwOk && confirmOk && (!isSignup || form.name.trim())

  const go = (u) => navigate(location.state?.from || (u.role === 'admin' ? '/admin' : '/'), { replace: true })

  const submit = async (e) => {
    e.preventDefault()
    setTouched({ email: true, password: true, confirm: true, name: true })
    if (!canSubmit) return
    manual.current = true
    setBusy('form')
    try {
      const u = isSignup
        ? await signup({ email: form.email, password: form.password, name: form.name.trim() })
        : await login(form.email, form.password)
      toast.success(`${u.name}님, 환영합니다!`)
      go(u)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(null)
    }
  }

  const demo = async (kind) => {
    manual.current = true
    setBusy(kind)
    setMode('login')
    const { email, password } = DEMO[kind]
    for (let i = 1; i <= email.length; i += 2) { setForm((f) => ({ ...f, email: email.slice(0, i) })); await sleep(18) }
    setForm((f) => ({ ...f, email }))
    for (let i = 1; i <= password.length; i++) { setForm((f) => ({ ...f, password: password.slice(0, i) })); await sleep(25) }
    try {
      const u = await demoLogin(kind)
      toast.success(kind === 'admin' ? '시스템 관리자 권한으로 로그인했습니다.' : '일반 회원 테스트 계정으로 로그인했습니다.')
      go(u)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(null)
    }
  }

  const social = (id) => {
    if (!providers[id]) return toast.info(`${SOCIAL.find((s) => s.id === id).label} OAuth 키가 서버에 설정되지 않았습니다.`, { description: '.env 의 *_CLIENT_ID / *_CLIENT_SECRET 을 등록하세요.' })
    window.location.href = oauthLoginUrl(id)
  }

  return (
    <div className="cinema-bg grid min-h-dvh md:grid-cols-[1.1fr_1fr]">
      <CinematicPanel />
      <section className="flex items-start justify-center px-5 py-8 sm:px-8 md:items-center md:py-12">
        <div className="w-full max-w-md animate-fade-up">
          <div className="flex rounded-xl border border-line bg-surface p-1" role="tablist">
            {[['login', '로그인'], ['signup', '회원가입']].map(([k, label]) => (
              <button key={k} role="tab" aria-selected={mode === k} onClick={() => setMode(k)}
                className={`flex-1 rounded-lg py-2.5 text-sm font-semibold transition ${mode === k ? 'bg-surface-2 text-fg shadow' : 'text-muted hover:text-fg'}`}>
                {label}
              </button>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2">
            <button onClick={() => demo('user')} disabled={!!busy} className="btn-ghost flex-col gap-1 py-3.5 text-xs sm:flex-row sm:text-sm">
              <FontAwesomeIcon icon={busy === 'user' ? faCircleNotch : faUser} spin={busy === 'user'} className="text-sky" />
              일반 회원 테스트 로그인
            </button>
            <button onClick={() => demo('admin')} disabled={!!busy} className="btn-ghost flex-col gap-1 border-gold/30 py-3.5 text-xs sm:flex-row sm:text-sm">
              <FontAwesomeIcon icon={busy === 'admin' ? faCircleNotch : faUserShield} spin={busy === 'admin'} className="text-gold" />
              시스템 관리자 테스트 로그인
            </button>
          </div>

          <div className="my-6 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />또는 이메일로 {isSignup ? '가입' : '로그인'}<span className="h-px flex-1 bg-line" /></div>

          <form onSubmit={submit} noValidate className="space-y-3">
            {isSignup && (
              <Field icon={faUser} error={touched.name && !form.name.trim() && '이름을 입력하세요.'}>
                <input className="input pl-11" placeholder="이름" value={form.name} onChange={set('name')} onBlur={() => setTouched((t) => ({ ...t, name: true }))} autoComplete="name" />
              </Field>
            )}
            <Field icon={faEnvelope} error={touched.email && !emailOk && '올바른 이메일 형식이 아닙니다.'}>
              <input className="input pl-11" type="email" inputMode="email" placeholder="이메일" value={form.email} onChange={set('email')} onBlur={() => setTouched((t) => ({ ...t, email: true }))} autoComplete="email" />
            </Field>
            <Field icon={faLock} error={touched.password && !pwOk && (isSignup ? '비밀번호 규칙을 확인하세요.' : '비밀번호를 입력하세요.')}>
              <input className="input px-11" type={showPw ? 'text' : 'password'} placeholder="비밀번호" value={form.password} onChange={set('password')} onBlur={() => setTouched((t) => ({ ...t, password: true }))} autoComplete={isSignup ? 'new-password' : 'current-password'} />
              <button type="button" onClick={() => setShowPw((v) => !v)} aria-label={showPw ? '비밀번호 숨기기' : '비밀번호 보기'} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-fg">
                <FontAwesomeIcon icon={showPw ? faEyeSlash : faEye} />
              </button>
            </Field>
            {isSignup && (
              <>
                <ul className="grid grid-cols-3 gap-x-2 gap-y-1.5 rounded-xl border border-line bg-surface/60 p-3 text-[11px]" aria-label="비밀번호 규칙">
                  {PASSWORD_RULES.map((r) => {
                    const ok = r.test(form.password)
                    return (
                      <li key={r.id} className={`flex items-center gap-1.5 ${ok ? 'text-mint' : 'text-muted'}`}>
                        <FontAwesomeIcon icon={ok ? faCheck : faXmark} fixedWidth /> {r.label}
                      </li>
                    )
                  })}
                </ul>
                <Field icon={faLock} error={touched.confirm && !confirmOk && '비밀번호가 일치하지 않습니다.'}>
                  <input className="input pl-11" type={showPw ? 'text' : 'password'} placeholder="비밀번호 확인" value={form.confirm} onChange={set('confirm')} onBlur={() => setTouched((t) => ({ ...t, confirm: true }))} autoComplete="new-password" />
                </Field>
              </>
            )}
            <button type="submit" disabled={!!busy} className="btn-primary w-full py-3.5 text-base">
              {busy === 'form' ? <FontAwesomeIcon icon={faCircleNotch} spin /> : <>{isSignup ? '회원가입' : '로그인'} <FontAwesomeIcon icon={faArrowRight} /></>}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />간편 로그인<span className="h-px flex-1 bg-line" /></div>
          <div className="grid grid-cols-3 gap-2">
            {SOCIAL.map((s) => (
              <button key={s.id} onClick={() => social(s.id)} className={`btn py-3 ${s.cls}`} aria-label={`${s.label}로 로그인`}>
                {s.icon}<span className="hidden sm:inline">{s.label}</span>
              </button>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-muted">
            비밀번호는 영문 대·소문자, 숫자, 특수문자를 조합한 8자리 이상이어야 합니다.
          </p>
        </div>
      </section>
    </div>
  )
}

function Field({ icon, error, children }) {
  return (
    <div>
      <div className="relative">
        <FontAwesomeIcon icon={icon} className="pointer-events-none absolute left-4 top-1/2 z-10 -translate-y-1/2 text-muted" />
        {children}
      </div>
      {error && <p className="mt-1.5 pl-1 text-xs text-accent" role="alert">{error}</p>}
    </div>
  )
}
