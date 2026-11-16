import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBell, faCircleCheck, faCircleExclamation, faCircleInfo, faXmark } from '@fortawesome/free-solid-svg-icons'

const ToastContext = createContext(null)
const ICONS = {
  success: [faCircleCheck, 'text-mint'],
  error: [faCircleExclamation, 'text-accent'],
  info: [faCircleInfo, 'text-sky'],
  alert: [faBell, 'text-gold'],
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const seq = useRef(0)

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback(
    (type, title, opts = {}) => {
      const id = ++seq.current
      setToasts((t) => [...t.slice(-4), { id, type, title, ...opts }])
      setTimeout(() => dismiss(id), opts.duration ?? (type === 'alert' ? 9000 : 4000))
    },
    [dismiss],
  )
  const value = useMemo(
    () => ({
      success: (t, o) => push('success', t, o),
      error: (t, o) => push('error', t, o),
      info: (t, o) => push('info', t, o),
      alert: (t, o) => push('alert', t, o),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-3 top-20 z-[70] flex flex-col items-center gap-2 sm:inset-x-auto sm:right-5 sm:items-end"
      >
        {toasts.map((t) => {
          const [icon, tone] = ICONS[t.type]
          return (
            <div
              key={t.id}
              role="status"
              className={`card pointer-events-auto flex w-full max-w-sm animate-fade-up items-start gap-3 p-4 shadow-2xl shadow-black/50 ${t.type === 'alert' ? 'border-gold/50' : ''}`}
            >
              <FontAwesomeIcon icon={icon} className={`mt-0.5 ${tone}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{t.title}</p>
                {t.description && <p className="mt-0.5 whitespace-pre-line text-xs text-muted">{t.description}</p>}
                {t.action && (
                  <button onClick={() => { t.action.onClick(); dismiss(t.id) }} className="mt-2 text-xs font-semibold text-gold hover:underline">
                    {t.action.label} →
                  </button>
                )}
              </div>
              <button onClick={() => dismiss(t.id)} aria-label="닫기" className="text-muted hover:text-fg">
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
