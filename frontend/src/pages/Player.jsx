import { useEffect, useMemo, useState } from "react"
import { useParams } from "react-router-dom"
import { api } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"

function formatTime(seconds) {
  const s = Math.max(0, Number(seconds || 0))
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m}:${String(r).padStart(2, "0")}`
}

export default function Player() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const payload = await api(`/projects/${id}/player`)
        if (alive) setData(payload)
      } catch (err) {
        if (alive) setError(err.message)
      }
    })()
    return () => {
      alive = false
    }
  }, [id])

  const timeline = useMemo(() => data?.timeline_comments || [], [data])
  const publicComments = useMemo(() => data?.public_comments || [], [data])

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const videoUrl = data.active_video?.file_url

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{data.project?.title}</h1>
        <p className="text-muted-foreground">{data.project?.description || ""}</p>
      </div>

      <Card>
        <CardContent className="p-4 space-y-4">
          {videoUrl ? (
            <video controls className="w-full rounded-lg">
              <source src={videoUrl} type={data.active_video?.file_mime || "video/mp4"} />
            </video>
          ) : (
            <p className="text-sm text-muted-foreground">No active video URL.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="p-4 space-y-3">
            <h2 className="font-semibold">Timeline comments</h2>
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No timeline comments (or you’re not authenticated / not allowed).
              </p>
            ) : (
              <div className="space-y-3">
                {timeline.map((c) => (
                  <div key={c.id} className="border rounded-md p-3">
                    <div className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>{c.author?.username || c.author?.email || "User"}</span>
                      <span>{c.timecode_seconds != null ? formatTime(c.timecode_seconds) : ""}</span>
                    </div>
                    <div className="mt-1 text-sm">{c.body}</div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 space-y-3">
            <h2 className="font-semibold">Public comments</h2>
            {publicComments.length === 0 ? (
              <p className="text-sm text-muted-foreground">No public comments.</p>
            ) : (
              <div className="space-y-3">
                {publicComments.map((c) => (
                  <div key={c.id} className="border rounded-md p-3">
                    <div className="text-xs text-muted-foreground">
                      {c.author?.username || c.author?.email || "User"}
                    </div>
                    <div className="mt-1 text-sm">{c.body}</div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
