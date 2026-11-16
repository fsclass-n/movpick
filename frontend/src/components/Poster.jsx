import { useState } from 'react'

export default function Poster({ url, title, className = '', eager = false }) {
  const [err, setErr] = useState(false)
  if (url && !err) {
    return <img src={url} alt={`${title} 포스터`} loading={eager ? 'eager' : 'lazy'} onError={() => setErr(true)} className={`object-cover ${className}`} />
  }
  return (
    <div className={`@container grid place-items-center overflow-hidden bg-gradient-to-br from-accent/30 via-surface-2 to-gold/20 ${className}`}>
      <span className="title-ko px-[8cqw] text-center text-[16cqw] leading-tight text-fg/80">{title.slice(0, 6)}</span>
    </div>
  )
}
