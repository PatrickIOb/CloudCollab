import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"

export default function CompletedProjects() {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const data = await api("/projects?status=COMPLETED&limit=50")
        if (alive) setItems(data)
      } catch (err) {
        if (alive) setError(err.message)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 space-y-4">
      <h1 className="text-2xl font-semibold">Completed projects</h1>
      {error ? <p className="text-red-600 text-sm">{error}</p> : null}

      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((p) => (
          <Link key={p.id} to={`/projects/${p.id}/player`}>
            <Card className="hover:shadow-sm transition">
              <CardContent className="p-5 space-y-1">
                <div className="font-semibold">{p.title}</div>
                <div className="text-sm text-muted-foreground line-clamp-2">
                  {p.description || ""}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
