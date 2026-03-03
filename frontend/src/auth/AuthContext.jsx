import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("access_token"))
  const [me, setMe] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  function setAccessToken(nextToken) {
    if (nextToken) {
      localStorage.setItem("access_token", nextToken)
      setToken(nextToken)
    } else {
      localStorage.removeItem("access_token")
      setToken(null)
    }
  }

  async function refreshMe() {
    if (!token) {
      setMe(null)
      setIsLoading(false)
      return
    }

    try {
      const data = await api("/auth/me")
      setMe(data)
    } catch {
      // invalid token
      setAccessToken(null)
      setMe(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshMe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const value = useMemo(
    () => ({ token, me, isLoading, setAccessToken, refreshMe }),
    [token, me, isLoading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
