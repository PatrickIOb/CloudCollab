import { Link } from "react-router-dom"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-semibold">ScoreMatch</h1>
        <p className="text-muted-foreground">
          Browse completed public projects or work on active/draft collaborations.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="p-6 space-y-3">
            <h2 className="text-xl font-semibold">Completed</h2>
            <p className="text-muted-foreground">
              Public, finished projects that anyone can watch and comment on.
            </p>
            <Button asChild>
              <Link to="/projects/completed">Explore completed</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 space-y-3">
            <h2 className="text-xl font-semibold">Active / Draft</h2>
            <p className="text-muted-foreground">
              Collaboration space (owner + members). Requires login.
            </p>
            <Button asChild variant="outline">
              <Link to="/projects/active">Go to workspace</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
