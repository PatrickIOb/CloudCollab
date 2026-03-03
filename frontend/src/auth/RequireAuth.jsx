import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"

export default function RequireAuth({ children }) {
  const { token, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return null
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />

  return children
}