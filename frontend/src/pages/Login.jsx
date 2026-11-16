import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight, faCheck, faCircleNotch, faComment, faCouch, faCrown, faEnvelope, faEye, faEyeSlash, faLock, faUser,
  faUserShield, faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { faGoogle } from '@fortawesome/free-brands-svg-icons'
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
    <div className="min-w-0 px-4 first:pl-0 last:pr-0">
      <dt className="truncate text-[11px] tracking-wide text-fg/60">{label}</dt>
      <dd className={`title-cine text-2xl leading-tight sm:text-3xl ${tone}`}>{value}</dd>
    </div>
  )
}

// 헤더(max-w-7xl) 컨테이너 가장자리와 정렬되는 좌우 여백
const EDGE_L = 'px-5 sm:px-8 lg:pl-[max(2.5rem,calc((100vw-80rem)/2+2.5rem))] lg:pr-12'
const EDGE_R = 'px-5 sm:px-8 lg:pr-[max(2.5rem,calc((100vw-80rem)/2+2.5rem))] lg:pl-14'

/** 좌측: 오늘 인기 1위 영화 포스터 히어로 (풀블리드) */
function NowPlayingHero() {
  const stats = useBookingStats()
  const [top, ...rest] = stats?.top || []
  const loading = !stats

  return (
    <section className="relative isolate overflow-hidden lg:min-h-[calc(100dvh-4rem)]">
      {top?.poster_url && (
        <img src={top.poster_url} alt="" aria-hidden className="absolute inset-0 -z-20 size-full scale-110 object-cover opacity-60 blur-md" />
      )}
      <div className="absolute inset-0 -z-10 bg-gradient-to-t from-ink via-ink/75 to-ink/20" />
      <div className="absolute inset-0 -z-10 hidden bg-gradient-to-r from-ink/60 via-transparent to-ink lg:block" />
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(700px_380px_at_10%_0%,#ff3d5740,transparent_70%)]" />

      <div className={`flex h-full flex-col py-8 lg:py-14 ${EDGE_L}`}>
        <div className="flex items-center gap-4 text-[11px] font-bold tracking-[0.25em]">
          <span className="flex items-center gap-2 text-gold"><FontAwesomeIcon icon={faCrown} /> TODAY&apos;S NO.1</span>
          <span className="h-px flex-1 bg-gradient-to-r from-gold/50 to-transparent" />
          <span className="flex items-center gap-1.5 text-mint"><span className="size-1.5 animate-pulse rounded-full bg-mint" /> RPA LIVE</span>
        </div>

        <div className="mt-6 flex flex-1 items-center gap-2 sm:gap-6 lg:mt-10">
          <div className="relative flex shrink-0 items-end">
            <span aria-hidden className="title-cine text-stroke -mr-6 select-none text-[9rem] leading-[0.75] sm:-mr-10 sm:text-[14rem] lg:text-[17rem] xl:text-[20rem]">1</span>
            {loading ? (
              <div className="relative aspect-[2/3] w-24 animate-pulse bg-surface-2 sm:w-40 lg:w-52 xl:w-60" />
            ) : (
              <Poster url={top?.poster_url} title={top?.title || 'movpick'} eager
                className="relative aspect-[2/3] w-24 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] sm:w-40 lg:w-52 xl:w-60" />
            )}
          </div>

          <div className="min-w-0 flex-1 pl-4 sm:pl-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-accent sm:text-[11px]">Box Office · 판매 좌석 기준</p>
            {loading ? (
              <div className="mt-3 h-9 w-3/4 animate-pulse bg-surface-2" />
            ) : (
              <h2 className="title-ko mt-2 line-clamp-3 text-2xl leading-tight sm:text-4xl xl:text-5xl">{top?.title || '상영 시간표 동기화 중'}</h2>
            )}
            {top && (
              <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-fg/70">
                {top.rating && <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${ratingTone(top.rating)}`}>{shortRating(top.rating)}</span>}
                {top.chains.join(' · ')}
              </p>
            )}
            <dl className="mt-6 hidden max-w-md grid-cols-3 divide-x divide-white/10 sm:grid">
              <Metric label="판매 좌석" value={top ? top.sold.toLocaleString() : '-'} tone="text-gold" />
              <Metric label="예매율" value={top ? pct(top.rate) : '-'} />
              <Metric label="상영 회차" value={top ? top.showtimes : '-'} />
            </dl>
            <p className="mt-3 text-xs text-fg/60 sm:hidden">{top ? `판매 ${top.sold.toLocaleString()}석 · 예매율 ${pct(top.rate)} · ${top.showtimes}회차` : ''}</p>
          </div>
        </div>

        {rest.length > 0 && (
          <ol className="mt-10 hidden grid-cols-4 border-t border-white/10 lg:grid">
            {rest.map((m, i) => (
              <li key={m.title} className="flex items-center gap-3 border-white/10 py-4 pr-3 [&:not(:first-child)]:border-l [&:not(:first-child)]:pl-4">
                <span className="title-cine text-3xl text-fg/30">{i + 2}</span>
                <Poster url={m.poster_url} title={m.title} className="aspect-[2/3] w-8 shrink-0" />
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold">{m.title}</p>
                  <p className="text-[11px] text-gold">{pct(m.rate)}</p>
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
            <dl className="flex shrink-0 divide-x divide-white/10 text-right">
              <Metric label="오늘 회차" value={stats.totals.showtimes.toLocaleString()} />
              <Metric label="잔여석" value={stats.totals.available.toLocaleString()} tone="text-mint" />
            </dl>
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
    <div className="grid flex-1 lg:grid-cols-[1.12fr_1fr]">
      <NowPlayingHero />

      <section className={`relative flex items-center py-10 lg:py-14 ${EDGE_R}`}>
        <div aria-hidden className="absolute inset-y-14 left-0 hidden w-px bg-gradient-to-b from-transparent via-line to-transparent lg:block" />
          <div className="mx-auto w-full max-w-md animate-fade-up">
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
