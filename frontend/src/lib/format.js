export const CHAINS = {
  cgv: { label: 'CGV', color: '#ff3d57' },
  megabox: { label: '메가박스', color: '#8b5cf6' },
  lotte: { label: '롯데시네마', color: '#f97316' },
}

// 수집 지역 (rpa/models.py REGIONS 와 동일 값 유지)
export const REGIONS = {
  seoul: { label: '서울' },
  gyeonggi: { label: '경기' },
}

export const PASSWORD_RULES = [
  { id: 'len', label: '8자 이상', test: (v) => v.length >= 8 },
  { id: 'lower', label: '영문 소문자', test: (v) => /[a-z]/.test(v) },
  { id: 'upper', label: '영문 대문자', test: (v) => /[A-Z]/.test(v) },
  { id: 'digit', label: '숫자', test: (v) => /\d/.test(v) },
  { id: 'special', label: '특수문자', test: (v) => /[^A-Za-z0-9\s]/.test(v) },
  { id: 'space', label: '공백 없음', test: (v) => v.length > 0 && !/\s/.test(v) },
]
export const isValidPassword = (v) => PASSWORD_RULES.every((r) => r.test(v))
export const isValidEmail = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)

const pad = (n) => String(n).padStart(2, '0')
export const toDateParam = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const fromDateParam = (p) => {
  const [y, m, d] = (p || '').split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}
export const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']
export const fmtTime = (iso) => {
  const d = new Date(iso)
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}
export const fmtDateTime = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
export const pct = (v) => `${Math.round((v || 0) * 100)}%`
export const ratingTone = (r = '') =>
  r.includes('18') || r.includes('청소년') ? 'bg-red-500/20 text-red-300'
    : r.includes('15') ? 'bg-orange-500/20 text-orange-300'
      : r.includes('12') ? 'bg-sky-500/20 text-sky-300'
        : 'bg-emerald-500/20 text-emerald-300'
export const shortRating = (r = '') => (r.match(/\d+/)?.[0] ?? (r.includes('청소년') ? '19' : 'ALL'))
