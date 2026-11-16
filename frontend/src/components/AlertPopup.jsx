import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUpRightFromSquare, faCouch, faXmark } from '@fortawesome/free-solid-svg-icons'
import { useRealtime } from '../context/RealtimeContext'
import { fmtDateTime } from '../lib/format'

/** 잔여석 발생 시 WebSocket으로 수신한 알림을 팝업으로 표시 */
export default function AlertPopup() {
  const { popup, closePopup } = useRealtime()
  const navigate = useNavigate()
  if (!popup) return null
  return (
    <div className="fixed inset-0 z-[65] grid place-items-end bg-black/50 p-3 backdrop-blur-sm sm:place-items-center" onClick={closePopup}>
      <div role="alertdialog" aria-labelledby="alert-title" onClick={(e) => e.stopPropagation()} className="card w-full max-w-md animate-fade-up border-gold/40 p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <span className="grid size-12 animate-glow place-items-center rounded-2xl bg-gold-soft text-xl text-gold">
            <FontAwesomeIcon icon={faCouch} />
          </span>
          <button onClick={closePopup} aria-label="닫기" className="text-muted hover:text-fg">
            <FontAwesomeIcon icon={faXmark} size="lg" />
          </button>
        </div>
        <p className="mt-4 text-xs font-semibold uppercase tracking-widest text-gold">RPA LIVE ALERT</p>
        <h2 id="alert-title" className="title-ko mt-1 text-2xl">명당 자리가 비었어요!</h2>
        <p className="mt-3 text-sm text-fg">{popup.movie_title}</p>
        <p className="text-sm text-muted">{popup.theater} {popup.screen} · {fmtDateTime(popup.start_at)}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {popup.seats.slice(0, 12).map((s) => (
            <span key={s} className="rounded-lg border border-gold/50 bg-gold-soft px-2.5 py-1 font-mono text-sm text-gold">{s}</span>
          ))}
        </div>
        <div className="mt-6 grid grid-cols-2 gap-2">
          <button className="btn-ghost" onClick={() => { closePopup(); navigate(`/showtimes/${popup.showtime_id}`) }}>
            좌석 배치도
          </button>
          <a className="btn-primary" href={popup.booking_url || '#'} target="_blank" rel="noreferrer" onClick={closePopup}>
            지금 예매 <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
          </a>
        </div>
      </div>
    </div>
  )
}
