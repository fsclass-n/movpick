import { useMemo } from 'react'

/**
 * 반응형 좌석 배치도: 컨테이너 폭에 맞춰 좌석 크기가 자동 스케일링(1fr 그리드)되며
 * 명당 자리(prime)는 골드 하이라이트, 추천 좌석은 글로우 애니메이션으로 표시.
 */
export default function SeatMap({ data, selected = [], onToggle, heatmap = false, flash = [] }) {
  const { rows, cols, aisles, prime, taken, scores, recommended, blocked } = data
  const sets = useMemo(() => ({
    prime: new Set(prime), taken: new Set(taken), blocked: new Set(blocked), rec: new Set(recommended),
    sel: new Set(selected), flash: new Set(flash),
  }), [prime, taken, blocked, recommended, selected, flash])

  const columns = []
  for (let c = 0; c < cols; c++) {
    if (aisles.includes(c)) columns.push('aisle')
    columns.push(c)
  }
  const template = columns.map((c) => (c === 'aisle' ? 'minmax(4px,0.5fr)' : 'minmax(0,1fr)')).join(' ')
  const rowLabel = (r) => String.fromCharCode(65 + r)

  return (
    <div className="w-full select-none">
      <div className="mx-auto mb-8 w-[85%]">
        <div className="screen-arc h-6 w-full opacity-70" />
        <p className="mt-2 text-center text-[10px] font-semibold tracking-[0.5em] text-muted">SCREEN</p>
      </div>
      <div className="mx-auto flex max-w-4xl flex-col gap-[clamp(2px,0.6vw,6px)]">
        {Array.from({ length: rows }, (_, r) => (
          <div key={r} className="flex items-center gap-[clamp(4px,1vw,10px)]">
            <span className="w-4 shrink-0 text-center text-[clamp(8px,1.6vw,11px)] font-semibold text-muted">{rowLabel(r)}</span>
            <div className="grid flex-1 gap-[clamp(2px,0.5vw,6px)]" style={{ gridTemplateColumns: template }}>
              {columns.map((c, i) => {
                if (c === 'aisle') return <span key={`a${i}`} />
                const id = `${rowLabel(r)}${c + 1}`
                if (sets.blocked.has(id)) return <span key={id} />
                const isTaken = sets.taken.has(id)
                const isPrime = sets.prime.has(id)
                const isSel = sets.sel.has(id)
                const score = scores[id] ?? 0
                let cls = 'border-line bg-surface-2 text-muted hover:border-fg/60'
                if (isPrime) cls = 'border-gold/70 bg-gold-soft text-gold hover:bg-gold/30'
                if (heatmap && !isTaken) cls = 'border-transparent text-ink'
                if (isTaken) cls = `border-transparent ${isPrime ? 'bg-gold/15' : 'bg-white/5'} text-transparent cursor-not-allowed`
                if (isSel) cls = 'border-accent bg-accent text-white'
                return (
                  <button
                    key={id}
                    type="button"
                    title={`${id}${isPrime ? ' · 명당' : ''}${isTaken ? ' · 예매됨' : ''} · 점수 ${Math.round(score * 100)}`}
                    aria-label={`${id} ${isTaken ? '예매됨' : '선택 가능'}${isPrime ? ' 명당 자리' : ''}`}
                    aria-pressed={isSel}
                    onClick={() => onToggle?.(id, { isTaken, isPrime })}
                    style={heatmap && !isTaken && !isSel ? { background: `hsl(${score * 50} 95% ${45 + score * 15}%)` } : undefined}
                    className={`relative aspect-square rounded-[clamp(2px,0.6vw,6px)] border text-[clamp(0px,1.3vw,10px)] font-semibold leading-none transition ${cls} ${sets.rec.has(id) && !isTaken && !isSel ? 'animate-glow' : ''} ${sets.flash.has(id) ? 'ring-2 ring-mint ring-offset-1 ring-offset-ink' : ''}`}
                  >
                    <span className="hidden sm:inline">{c + 1}</span>
                  </button>
                )
              })}
            </div>
            <span className="w-4 shrink-0 text-center text-[clamp(8px,1.6vw,11px)] font-semibold text-muted">{rowLabel(r)}</span>
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-muted">
        <Legend cls="border-line bg-surface-2" label="선택 가능" />
        <Legend cls="border-gold/70 bg-gold-soft" label="명당 자리" />
        <Legend cls="border-transparent bg-white/5" label="예매됨" />
        <Legend cls="border-accent bg-accent" label="선택" />
        <Legend cls="border-mint ring-2 ring-mint" label="방금 취소표" />
      </div>
    </div>
  )
}

function Legend({ cls, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`size-3.5 rounded border ${cls}`} /> {label}
    </span>
  )
}
