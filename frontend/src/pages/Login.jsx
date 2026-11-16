import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowLeft, faArrowRight, faCheck, faCircleNotch, faComment, faCouch, faCrown, faEnvelope, faEye, faEyeSlash, faFilm,
  faLock, faTicket, faUser, faUserShield, faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { faGithub, faGoogle } from '@fortawesome/free-brands-svg-icons'
import { Logo } from '../components/Layout'
import Poster from '../components/Poster'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { api, oauthLoginUrl } from '../lib/api'
import { PASSWORD_RULES, isValidEmail, isValidPassword, pct, ratingTone, shortRating } from '../lib/format'

const DEMO = {
  user: { email: 'user@movpick.app', password: 'Movpick!2026' },
  admin: { email: 'admin@movpick.app', password: 'Admin!2026' },
}
const COPY = {
  login: { eyebrow: 'WELCOME BACK', title: '다시 만나서 반가워요', desc: '로그인하고 명당 자리 취소표 알림을 이어서 받아보세요.' },
  signup: { eyebrow: 'JOIN MOVPICK', title: 'movpick 시작하기', desc: '30초면 가입 완료. 원하는 좌석이 비는 순간 바로 알려드려요.' },
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function useBookingStats() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    let alive = true
    const load = () => api('/api/stats/booking-rates').then((d) => alive && setStats(d)).catch(() => alive && setStats((s) => s || { top: [] }))
    load()
    const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  return stats
}

function Metric({ label, value, tone = 'text-fg' }) {
  return (
    <div className="min-w-0">
      <p className="truncate text-[11px] tracking-wide text-fg/60">{label}</p>
      <p className={`title-cine text-2xl leading-tight sm:text-3xl ${tone}`}>{value}</p>
    </div>
  )
}

/** 좌측: 오늘 인기 1위 영화 포스터 히어로 */
function NowPlayingHero() {
  const stats = useBookingStats()
  const [top, ...rest] = stats?.top || []
  const loading = !stats

  return (
    <section className="relative isolate flex min-h-[260px] overflow-hidden rounded-3xl border border-line bg-surface lg:min-h-0">
      {top?.poster_url && (
        <img src={top.poster_url} alt="" aria-hidden className="absolute inset-0 -z-10 size-full scale-110 object-cover opacity-50 blur-2xl" />
      )}
      <div className="absolute inset-0 -z-10 bg-gradient-to-t from-ink via-ink/80 to-ink/30" />
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(600px_300px_at_0%_0%,#ff3d5733,transparent_70%)]" />

      <div className="flex w-full flex-col p-5 sm:p-8 lg:p-10">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 rounded-full border border-gold/40 bg-gold-soft px-3 py-1 text-[11px] font-bold tracking-[0.2em] text-gold">
            <FontAwesomeIcon icon={faCrown} /> TODAY&apos;S NO.1
          </span>
          <span className="flex items-center gap-1.5 text-[11px] font-semibold text-mint">
            <span className="size-1.5 animate-pulse rounded-full bg-mint" /> RPA LIVE
          </span>
        </div>

        <div className="mt-5 flex flex-1 items-center gap-5 sm:gap-8 lg:mt-8">
          <div className="relative shrink-0">
            <div className="absolute -inset-3 -z-10 rounded-3xl bg-accent/25 blur-2xl" />
            {loading ? (
              <div className="aspect-[2/3] w-28 animate-pulse rounded-2xl bg-surface-2 sm:w-44 lg:w-56 xl:w-64" />
            ) : (
              <Poster url={top?.poster_url} title={top?.title || 'movpick'} eager
                className="aspect-[2/3] w-28 rounded-2xl shadow-2xl shadow-black/60 ring-1 ring-white/10 sm:w-44 lg:w-56 xl:w-64" />
            )}
            <span className="title-cine absolute -bottom-3 -left-3 grid size-12 place-items-center rounded-2xl bg-accent text-3xl text-white shadow-lg shadow-accent/40 sm:size-14 sm:text-4xl">1</span>
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-accent">Box Office · 실시간 판매 좌석 기준</p>
            {loading ? (
              <div className="mt-3 h-9 w-3/4 animate-pulse rounded-lg bg-surface-2" />
            ) : (
              <h2 className="title-ko mt-2 line-clamp-3 text-2xl leading-tight sm:text-3xl xl:text-4xl">{top?.title || '상영 시간표 동기화 중'}</h2>
            )}
            {top && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                {top.rating && <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${ratingTone(top.rating)}`}>{shortRating(top.rating)}</span>}
                {top.chains.map((c) => <span key={c} className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-medium text-fg/80">{c}</span>)}
              </div>
            )}
            <div className="mt-5 hidden grid-cols-3 gap-4 border-t border-white/10 pt-4 sm:grid">
              <Metric label="오늘 판매 좌석" value={top ? top.sold.toLocaleString() : '-'} tone="text-gold" />
              <Metric label="예매율" value={top ? pct(top.rate) : '-'} />
              <Metric label="상영 회차" value={top ? top.showtimes : '-'} />
            </div>
            <p className="mt-3 text-xs text-fg/60 sm:hidden">{top ? `판매 ${top.sold.toLocaleString()}석 · 예매율 ${pct(top.rate)} · ${top.showtimes}회차` : ''}</p>
          </div>
        </div>

        {rest.length > 0 && (
          <ol className="mt-8 hidden grid-cols-2 gap-2 lg:grid xl:grid-cols-4">
            {rest.map((m, i) => (
              <li key={m.title} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-ink/50 p-2.5 backdrop-blur">
                <Poster url={m.poster_url} title={m.title} className="aspect-[2/3] w-9 shrink-0 rounded-md" />
                <div className="min-w-0">
                  <p className="text-[10px] font-bold text-muted">NO.{i + 2}</p>
                  <p className="truncate text-xs font-semibold">{m.title}</p>
                  <p className="text-[10px] text-gold">{pct(m.rate)}</p>
                </div>
              </li>
            ))}
          </ol>
        )}

        <div className="mt-8 hidden items-end justify-between gap-6 lg:flex">
          <h1 className="title-ko text-3xl leading-tight xl:text-4xl">
            명당 자리가 비는 순간,<br /><span className="text-gold">가장 먼저</span> 알려드려요
          </h1>
          {stats?.totals && (
            <div className="flex shrink-0 gap-6 text-right">
              <Metric label="오늘 회차" value={stats.totals.showtimes.toLocaleString()} />
              <Metric label="잔여석" value={stats.totals.available.toLocaleString()} tone="text-mint" />
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

const SOCIAL = [
  { id: 'google', label: 'Google', cls: 'bg-white text-neutral-800 hover:bg-neutral-100', icon: <FontAwesomeIcon icon={faGoogle} /> },
  { id: 'naver', label: '네이버', cls: 'bg-[#03C75A] text-white hover:brightness-105', icon: <span className="font-black">N</span> },
  { id: 'kakao', label: '카카오', cls: 'bg-[#FEE500] text-[#191600] hover:brightness-95', icon: <FontAwesomeIcon icon={faComment} /> }, // FA 무료 세트에 카카오 로고가 없어 말풍선 사용
]

function AuthFooter() {
  return (
    <footer className="mx-auto mt-8 w-full max-w-7xl border-t border-line pt-6">
      <div className="flex flex-col gap-4 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <p className="flex items-center gap-2 text-fg/80"><FontAwesomeIcon icon={faTicket} className="text-accent" /> RPA 기반 상영 시간표 동기화 · 명당 자리 실시간 예매 추천</p>
          <p>© {new Date().getFullYear()} Team movpick · 박미금 · 김모란 · 이오리 · 홍기흥</p>
        </div>
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2" aria-label="바닥글">
          <Link to="/" className="hover:text-fg"><FontAwesomeIcon icon={faFilm} className="mr-1.5" />상영작</Link>
          <a href="https://fsclass-n.github.io/movpick/" target="_blank" rel="noreferrer" className="hover:text-fg">프로젝트 안내</a>
          <a href="https://github.com/fsclass-n/movpick" target="_blank" rel="noreferrer" className="hover:text-fg"><FontAwesomeIcon icon={faGithub} className="mr-1.5" />GitHub</a>
        </nav>
      </div>
    </footer>
  )
}

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
  const copy = COPY[mode]

  const go = (u) => navigate(location.state?.from || (u.role === 'admin' ? '/admin' : '/'), { replace: true })
  const switchMode = (m) => { setMode(m); setTouched({}) }

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
      toast.success(kind === 'admin' ? '테스트 관리자로 로그인했습니다. (읽기 전용)' : '일반 회원 테스트 계정으로 로그인했습니다.')
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
    <div className="cinema-bg flex min-h-dvh flex-col px-4 pb-6 pt-4 sm:px-6 lg:px-10 lg:pt-6">
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between py-2">
        <Logo />
        <Link to="/" className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted transition hover:bg-surface-2 hover:text-fg">
          <FontAwesomeIcon icon={faArrowLeft} /> <span className="hidden sm:inline">상영작 둘러보기</span><span className="sm:hidden">둘러보기</span>
        </Link>
      </header>

      <main className="mx-auto mt-4 grid w-full max-w-7xl flex-1 gap-5 lg:mt-6 lg:grid-cols-[1.15fr_1fr] lg:gap-8">
        <NowPlayingHero />

        <section className="card flex items-center justify-center rounded-3xl px-5 py-8 sm:px-10 sm:py-10 lg:px-12">
          <div className="w-full max-w-md animate-fade-up">
            <div key={mode} className="animate-fade-up">
              <p className="text-[11px] font-bold tracking-[0.35em] text-accent">{copy.eyebrow}</p>
              <h1 className="title-ko mt-2 text-3xl leading-tight sm:text-4xl">{copy.title}</h1>
              <p className="mt-2 text-sm text-muted">{copy.desc}</p>
            </div>

            <div className="mt-7 flex rounded-xl border border-line bg-ink/60 p-1" role="tablist">
              {[['login', '로그인'], ['signup', '회원가입']].map(([k, label]) => (
                <button key={k} role="tab" aria-selected={mode === k} onClick={() => switchMode(k)}
                  className={`flex-1 rounded-lg py-2.5 text-sm font-semibold transition ${mode === k ? 'bg-surface-2 text-fg shadow' : 'text-muted hover:text-fg'}`}>
                  {label}
                </button>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button onClick={() => demo('user')} disabled={!!busy} className="btn-ghost flex-col gap-1 py-3 text-xs sm:text-[13px]">
                <FontAwesomeIcon icon={busy === 'user' ? faCircleNotch : faUser} spin={busy === 'user'} className="text-sky" />
                일반 회원 테스트 로그인
              </button>
              <button onClick={() => demo('admin')} disabled={!!busy} className="btn-ghost relative flex-col gap-1 border-gold/30 py-3 text-xs sm:text-[13px]">
                <span className="absolute -top-2 right-2 rounded-full border border-gold/40 bg-ink px-1.5 text-[10px] font-semibold text-gold">읽기 전용</span>
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
                  <ul className="grid grid-cols-3 gap-x-2 gap-y-1.5 rounded-xl border border-line bg-ink/40 p-3 text-[11px]" aria-label="비밀번호 규칙">
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
            <p className="mt-6 flex items-center justify-center gap-2 text-center text-xs text-muted">
              <FontAwesomeIcon icon={faCouch} className="text-gold/70" />
              {isSignup ? '비밀번호: 영문 대·소문자 · 숫자 · 특수문자 조합 8자 이상' : <>계정이 없으신가요? <button onClick={() => switchMode('signup')} className="font-semibold text-fg hover:text-accent">회원가입</button></>}
            </p>
          </div>
        </section>
      </main>

      <AuthFooter />
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
