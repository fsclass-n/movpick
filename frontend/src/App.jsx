import { useEffect, useRef } from 'react'
import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import Layout from './components/Layout'
import { RequireAuth, Spinner } from './components/Guards'
import { useAuth } from './context/AuthContext'
import { useToast } from './context/ToastContext'
import Admin from './pages/Admin'
import Alerts from './pages/Alerts'
import Home from './pages/Home'
import Login from './pages/Login'
import Showtime from './pages/Showtime'

function OAuthCallback() {
  const { acceptToken } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const done = useRef(false)
  useEffect(() => {
    if (done.current) return
    done.current = true
    const params = new URLSearchParams(window.location.hash.slice(1))
    const token = params.get('token')
    window.history.replaceState(null, '', window.location.pathname)
    if (token) acceptToken(token).then(() => { toast.success('소셜 로그인에 성공했습니다.'); navigate('/', { replace: true }) })
    else { toast.error(`소셜 로그인 실패: ${params.get('error') || '알 수 없는 오류'}`); navigate('/login', { replace: true }) }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  return <Spinner label="소셜 로그인 처리 중" />
}

function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="title-cine text-8xl text-accent">404</p>
      <p className="mt-2 text-muted">요청하신 페이지를 찾을 수 없습니다.</p>
      <Link to="/" className="btn-primary mt-6">홈으로</Link>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout bare />}>
        <Route path="/login" element={<Login />} />
      </Route>
      <Route element={<Layout />}>
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        <Route index element={<Home />} />
        <Route path="/showtimes/:id" element={<Showtime />} />
        <Route path="/alerts" element={<RequireAuth><Alerts /></RequireAuth>} />
        <Route path="/admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
