import { Link, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/auth/AuthContext"

export default function TopNav() {
  const nav = useNavigate()
  const { token, me, setAccessToken } = useAuth()

  function logout() {
    setAccessToken(null)
    nav("/login")
  }

  return (
    <header className="border-b">
      <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold">
          ScoreMatch
        </Link>

        <div className="flex items-center gap-3">
          <Link to="/projects/completed" className="text-sm text-muted-foreground hover:underline">
            Completed
          </Link>
          <Link to="/projects/active" className="text-sm text-muted-foreground hover:underline">
            Active/Draft
          </Link>

          {token ? (
            <>
              <span className="text-sm text-muted-foreground">
                {me?.username || me?.email || "Logged in"}
              </span>
              <Button variant="outline" onClick={logout}>
                Logout
              </Button>
            </>
          ) : (
            <Button asChild>
              <Link to="/login">Login</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
