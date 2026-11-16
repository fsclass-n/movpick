import { Navigate, useLocation } from 'react-router-dom'
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
  if (admin && user.role !== 'admin') return <Navigate to="/" replace />
  return children
}
