import { Link, Navigate, useLocation } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'

export function Spinner({ label = '불러오는 중' }) {
  return (
    <div className="grid place-items-center py-24 text-muted" role="status">
      <span className="size-8 animate-spin rounded-full border-2 border-line border-t-accent" />
      <span className="mt-3 text-sm">{label}</span>
    </div>
  )
}

export function RequireAuth({ children, admin = false }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (admin && user.role !== 'admin') return <AdminOnly />
  return children
}

function AdminOnly() {
  return (
    <div className="mx-auto max-w-lg py-24 text-center animate-fade-up" role="alert">
      <span className="mx-auto grid size-16 place-items-center rounded-full bg-accent-soft text-2xl text-accent">
        <FontAwesomeIcon icon={faLock} />
      </span>
      <h1 className="title-ko mt-6 text-3xl">관리자 전용 화면입니다</h1>
      <p className="mt-3 text-sm text-muted">현재 계정은 일반 회원 권한입니다. 관리자 기능은 관리자 계정만 사용할 수 있으며, 서버도 관리자 API를 다시 검사합니다.</p>
      <Link to="/" className="btn-primary mt-8">상영작으로 돌아가기</Link>
    </div>
  )
}
