const fallback = import.meta.env.DEV ? 'http://localhost:8000' : 'https://movpick-api.onrender.com'
export const API_URL = (import.meta.env.VITE_API_URL || fallback).replace(/\/$/, '')
export const WS_URL = API_URL.replace(/^http/, 'ws') + '/ws'

const TOKEN_KEY = 'movpick_token'
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function detailMessage(detail) {
  if (Array.isArray(detail)) return detail.map((d) => d.msg?.replace(/^Value error, /, '')).join('\n')
  return detail || '요청을 처리하지 못했습니다.'
}

export async function api(path, { method = 'GET', body, query, raw } = {}) {
  const url = new URL(API_URL + path)
  Object.entries(query || {}).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && url.searchParams.set(k, v))
  const token = tokenStore.get()
  let res
  try {
    res = await fetch(url, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없습니다. (Render 무료 티어는 첫 요청 시 기동까지 시간이 걸릴 수 있어요)')
  }
  if (res.status === 204) return null
  if (raw) return res.ok ? res.text() : Promise.reject(new ApiError(res.status, await res.text()))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, detailMessage(data.detail))
  return data
}

export const oauthLoginUrl = (provider) =>
  `${API_URL}/api/auth/oauth/${provider}/login?redirect=${encodeURIComponent(window.location.origin)}`
