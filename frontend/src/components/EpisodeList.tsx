import type { Episode } from "@/api/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { clock, shortDay } from "@/lib/format"
import { cn } from "@/lib/utils"

const STAGES: Record<NonNullable<Episode["stage"]>, string> = {
  fetch: "Fetching the news",
  select: "Choosing the stories",
  write: "Writing the script",
  check: "Checking the facts",
  voice: "Recording the voices",
  master: "Mastering the audio",
}

const STATUS: Record<Episode["status"], string> = {
  queued: "Queued",
  in_progress: "In progress",
  completed: "Ready",
  skipped: "Skipped",
  failed: "Failed",
}

const WORKER_HINT_AFTER_MS = 60_000

type Props = {
  episodes: Episode[]
  selectedId: number | null
  timeZone: string
  onSelect: (id: number) => void
  onRetry: (id: number) => void
  retrying: number | null
  // When the list was fetched: passed in because rendering must stay pure.
  now: number
}

function describe(episode: Episode, now: number): string {
  if (episode.status === "in_progress")
    return episode.stage
      ? `Generating: ${STAGES[episode.stage].toLowerCase()}`
      : "Generating"
  if (episode.status === "queued") {
    const waiting = now - new Date(episode.created_at).getTime()
    return waiting > WORKER_HINT_AFTER_MS
      ? "Still queued. Is the worker running? Start it with: docker compose --profile worker up -d"
      : "Waiting for the worker"
  }
  return episode.title ?? episode.status_reason ?? ""
}

export function EpisodeList({
  episodes,
  selectedId,
  timeZone,
  onSelect,
  onRetry,
  retrying,
  now,
}: Props) {
  if (episodes.length === 0) {
    return (
      <p className="text-muted-foreground">
        No episodes yet. Generate one now, or wait for the next one.
      </p>
    )
  }

  return (
    <ul className="overflow-hidden rounded-xl border bg-card">
      {episodes.map((episode) => {
        const ready = episode.status === "completed"
        const day = shortDay(
          episode.news_as_of ?? episode.scheduled_for,
          timeZone
        )
        const row = (
          <>
            <span className="text-muted-foreground">{day}</span>
            <span
              className={cn(
                "order-first col-span-2 sm:order-none sm:col-span-1",
                !ready && "text-muted-foreground"
              )}
            >
              {describe(episode, now)}
            </span>
            <span className="hidden text-muted-foreground sm:block">
              {episode.duration_seconds ? clock(episode.duration_seconds) : ""}
            </span>
            <span className="flex items-center justify-end gap-2">
              {episode.status === "failed" && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={retrying === episode.id}
                  onClick={() => onRetry(episode.id)}
                >
                  Retry
                </Button>
              )}
              <Badge
                variant={
                  episode.status === "failed" ? "destructive" : "outline"
                }
              >
                {STATUS[episode.status]}
              </Badge>
            </span>
          </>
        )
        const grid =
          "grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 px-4 py-3 text-left sm:grid-cols-[7rem_1fr_3.5rem_9rem]"
        return (
          <li key={episode.id} className="border-t first:border-t-0">
            {ready ? (
              <button
                type="button"
                onClick={() => onSelect(episode.id)}
                aria-current={episode.id === selectedId}
                className={cn(
                  grid,
                  "w-full hover:bg-muted aria-current:bg-muted aria-current:font-semibold"
                )}
              >
                {row}
              </button>
            ) : (
              <div className={grid}>{row}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
