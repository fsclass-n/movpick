import { useCallback, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowsRotate, faCircleCheck, faCircleNotch, faCircleXmark, faClock, faDatabase, faMagnifyingGlass, faPlay, faRobot,
  faTowerBroadcast, faUserShield, faUsers,
} from '@fortawesome/free-solid-svg-icons'
import { Spinner } from '../components/Guards'
import { useAuth } from '../context/AuthContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { useToast } from '../context/ToastContext'
import { api } from '../lib/api'
import { CHAINS, fmtDateTime } from '../lib/format'

const TABS = [
  { id: 'crawler', label: 'RPA 크롤러', icon: faRobot },
  { id: 'users', label: '회원 권한', icon: faUsers },
]

function StatCard({ icon, label, value, tone = 'text-fg' }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-muted"><FontAwesomeIcon icon={icon} className="mr-1.5" />{label}</p>
      <p className={`title-cine mt-1 text-3xl ${tone}`}>{value ?? '-'}</p>
    </div>
  )
}

function StatusBadge({ status, source }) {
  const ok = status === 'success'
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? 'bg-mint/15 text-mint' : 'bg-accent/15 text-accent'}`}>
        <FontAwesomeIcon icon={ok ? faCircleCheck : faCircleXmark} /> {ok ? '성공' : '실패'}
      </span>
      <span className={`rounded-full px-2 py-0.5 text-[11px] ${source === 'real' ? 'bg-sky/15 text-sky' : 'bg-surface-2 text-muted'}`}>{source === 'real' ? 'REAL' : 'MOCK'}</span>
    </span>
  )
}

function CrawlerTab() {
  const toast = useToast()
  const [status, setStatus] = useState(null)
  const [summary, setSummary] = useState(null)
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('')
  const [interval, setIntervalMin] = useState(30)
  const [report, setReport] = useState('')

  const load = useCallback(async () => {
    const [s, sum, l] = await Promise.all([
      api('/api/admin/crawler'), api('/api/admin/summary'), api('/api/admin/crawler/logs', { query: { limit: 60, status: filter } }),
    ])
    setStatus(s); setSummary(sum); setLogs(l); setIntervalMin(s.interval_minutes)
    api('/api/admin/reports/crawl', { raw: true }).then(setReport).catch(() => {})
  }, [filter])

  useEffect(() => { load().catch((e) => toast.error(e.message)) }, [load, toast])
  useEffect(() => { const t = setInterval(() => load().catch(() => {}), 15000); return () => clearInterval(t) }, [load])
  useRealtimeEvent('crawl_started', () => setStatus((s) => s && { ...s, running: true }))
  useRealtimeEvent('crawl_finished', (m) => {
    load()
    const failed = m.results.filter((r) => !r.ok).length
    toast[failed ? 'error' : 'success'](`크롤링 완료 · ${m.results.length - failed}/${m.results.length} 성공`)
  })

  const run = async (chain) => {
    try {
      await api('/api/admin/crawler/run', { method: 'POST', query: { chain } })
      setStatus((s) => ({ ...s, running: true }))
      toast.info(`${chain ? CHAINS[chain].label : '전체'} 크롤링을 시작했습니다.`)
    } catch (e) { toast.error(e.message) }
  }
  const saveConfig = async (enabled = status.enabled) => {
    try {
      setStatus(await api('/api/admin/crawler/config', { method: 'PUT', body: { interval_minutes: Number(interval), enabled } }))
      toast.success('크롤링 스케줄을 저장했습니다.')
    } catch (e) { toast.error(e.message) }
  }

  if (!status) return <Spinner />
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={faDatabase} label="동기화된 상영 회차" value={summary?.showtimes} />
        <StatCard icon={faCircleCheck} label="24h 성공" value={summary?.crawl_24h?.success ?? 0} tone="text-mint" />
        <StatCard icon={faCircleXmark} label="24h 실패/대체" value={summary?.crawl_24h?.failed ?? 0} tone="text-accent" />
        <StatCard icon={faTowerBroadcast} label="WebSocket 접속 / 감시" value={`${summary?.ws_connections ?? 0} / ${summary?.active_watches ?? 0}`} tone="text-gold" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold"><FontAwesomeIcon icon={faRobot} className="mr-2 text-accent" />Playwright 크롤러 상태</p>
            <span className={`flex items-center gap-1.5 text-xs font-semibold ${status.running ? 'text-gold' : status.enabled ? 'text-mint' : 'text-muted'}`}>
              {status.running ? <><FontAwesomeIcon icon={faCircleNotch} spin /> 실행 중</> : status.enabled ? '대기 중' : '일시 정지'}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <dt className="text-muted">수집 모드</dt><dd>{status.mode} · {status.headless ? 'Headless' : 'Headed'}</dd>
            <dt className="text-muted">마지막 실행</dt><dd>{fmtDateTime(status.last_finished_at)}</dd>
            <dt className="text-muted">다음 실행</dt><dd>{status.enabled ? fmtDateTime(status.next_run_at) : '-'}</dd>
            <dt className="text-muted">좌석 모니터</dt><dd>{status.seat_monitor_interval_seconds}초 주기</dd>
          </dl>
          <div className="mt-5 flex items-end gap-2 border-t border-line pt-4">
            <label className="flex-1 text-xs text-muted">
              <FontAwesomeIcon icon={faClock} className="mr-1" />크롤링 주기(분)
              <input type="number" min={5} max={1440} value={interval} onChange={(e) => setIntervalMin(e.target.value)} className="input mt-1 py-2" />
            </label>
            <button onClick={() => saveConfig()} className="btn-ghost">저장</button>
            <button onClick={() => saveConfig(!status.enabled)} className="btn-ghost">{status.enabled ? '일시정지' : '재개'}</button>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <button onClick={() => run()} disabled={status.running} className="btn-primary col-span-2 sm:col-span-1"><FontAwesomeIcon icon={faPlay} /> 전체</button>
            {status.chains.map((c) => (
              <button key={c} onClick={() => run(c)} disabled={status.running} className="btn-ghost text-xs">{CHAINS[c]?.label}</button>
            ))}
          </div>
          {status.last_results?.length > 0 && (
            <ul className="mt-4 space-y-1.5 text-xs">
              {status.last_results.map((r, i) => (
                <li key={i} className="flex items-center justify-between gap-2 rounded-lg bg-surface-2 px-3 py-2">
                  <span className="truncate">{CHAINS[r.chain]?.label} · {r.date.slice(5)}</span>
                  <span className="flex items-center gap-2 text-muted">{r.items}건 · {r.duration_ms}ms <StatusBadge status={r.ok ? 'success' : 'failed'} source={r.source} /></span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card overflow-hidden">
          <p className="px-5 pt-5 text-sm font-semibold">크롤링 성능 리포트 <span className="text-xs font-normal text-muted">(pandas · Plotly)</span></p>
          {report ? <iframe title="crawl report" srcDoc={report} className="h-[380px] w-full" sandbox="allow-scripts" /> : <Spinner />}
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-5">
          <p className="text-sm font-semibold">실행 로그</p>
          <div className="flex gap-2">
            {[['', '전체'], ['success', '성공'], ['failed', '실패']].map(([k, l]) => (
              <button key={k} onClick={() => setFilter(k)} className={`chip ${filter === k ? 'border-fg/60 text-fg' : 'text-muted'}`}>{l}</button>
            ))}
            <button onClick={() => load()} className="chip text-muted" aria-label="새로고침"><FontAwesomeIcon icon={faArrowsRotate} /></button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-y border-line bg-surface-2/60 text-xs text-muted">
              <tr><th className="px-5 py-2.5">시각</th><th>체인</th><th>결과</th><th>건수</th><th>소요</th><th>트리거</th><th className="pr-5">메시지</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {logs.map((l) => (
                <tr key={l.id} className="hover:bg-surface-2/40">
                  <td className="whitespace-nowrap px-5 py-2.5 text-muted">{fmtDateTime(l.started_at)}</td>
                  <td>{CHAINS[l.chain]?.label || l.chain}</td>
                  <td><StatusBadge status={l.status} source={l.source} /></td>
                  <td>{l.items}</td>
                  <td className="text-muted">{l.duration_ms}ms</td>
                  <td className="text-muted">{l.trigger}</td>
                  <td className="max-w-xs truncate pr-5 text-xs text-muted" title={l.message}>{l.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function UsersTab() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [users, setUsers] = useState(null)
  const [q, setQ] = useState('')
  const [pending, setPending] = useState(null)

  useEffect(() => {
    const t = setTimeout(() => api('/api/admin/users', { query: { q } }).then(setUsers).catch((e) => toast.error(e.message)), 250)
    return () => clearTimeout(t)
  }, [q, toast])

  const changeRole = async (u, role) => {
    setPending(u.id)
    try {
      const updated = await api(`/api/admin/users/${u.id}/role`, { method: 'PATCH', body: { role } })
      setUsers((list) => list.map((x) => (x.id === u.id ? updated : x)))
      toast.success(`${u.name}님의 권한을 '${role === 'admin' ? '관리자' : '일반 사용자'}'(으)로 변경했습니다.`)
    } catch (e) { toast.error(e.message) } finally { setPending(null) }
  }

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 p-5">
        <p className="text-sm font-semibold">전체 회원 {users && <span className="text-muted">({users.length})</span>}</p>
        <div className="relative w-full sm:w-64">
          <FontAwesomeIcon icon={faMagnifyingGlass} className="absolute left-4 top-1/2 -translate-y-1/2 text-sm text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="이름 · 이메일 검색" className="input py-2 pl-10" />
        </div>
      </div>
      {!users ? <Spinner /> : (
        <ul className="divide-y divide-line border-t border-line">
          {users.map((u) => (
            <li key={u.id} className="flex flex-col gap-3 px-5 py-3.5 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">
                  {u.role === 'admin' && <FontAwesomeIcon icon={faUserShield} className="mr-1.5 text-gold" />}{u.name}
                  {u.id === me.id && <span className="ml-2 rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-muted">나</span>}
                </p>
                <p className="truncate text-xs text-muted">{u.email} · {u.provider} · 가입 {fmtDateTime(u.created_at)} · 최근 로그인 {fmtDateTime(u.last_login_at)}</p>
              </div>
              <div className="flex rounded-xl border border-line bg-surface-2 p-1 text-xs" role="radiogroup" aria-label={`${u.name} 권한`}>
                {[['user', '일반 사용자'], ['admin', '관리자']].map(([r, label]) => (
                  <button key={r} role="radio" aria-checked={u.role === r} disabled={pending === u.id || u.role === r || (u.id === me.id && r === 'user')}
                    onClick={() => changeRole(u, r)}
                    className={`rounded-lg px-3 py-1.5 font-semibold transition disabled:cursor-default ${u.role === r ? (r === 'admin' ? 'bg-gold text-ink' : 'bg-fg text-ink') : 'text-muted hover:text-fg'}`}>
                    {pending === u.id && u.role !== r ? <FontAwesomeIcon icon={faCircleNotch} spin /> : label}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Admin() {
  const [tab, setTab] = useState('crawler')
  return (
    <div className="animate-fade-up">
      <p className="text-xs font-semibold uppercase tracking-[0.35em] text-gold"><FontAwesomeIcon icon={faUserShield} className="mr-1.5" />ADMIN CONSOLE</p>
      <h1 className="title-ko mt-2 text-3xl">관리자 대시보드</h1>
      <div className="mt-6 flex gap-2 border-b border-line" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
            className={`-mb-px flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition ${tab === t.id ? 'border-accent text-fg' : 'border-transparent text-muted hover:text-fg'}`}>
            <FontAwesomeIcon icon={t.icon} /> {t.label}
          </button>
        ))}
      </div>
      <div className="mt-6">{tab === 'crawler' ? <CrawlerTab /> : <UsersTab />}</div>
    </div>
  )
}
