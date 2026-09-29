import type { Generation, PodcastSettings } from "@/api/client"
import { Button } from "@/components/ui/button"
import { whenNext } from "@/lib/format"

const LENGTHS: Record<number, string> = {
  3: "Three minutes",
  5: "Five minutes",
  7: "Seven minutes",
}

type Props = {
  settings: PodcastSettings
  generation: Generation
  onGenerate: () => void
  pending: boolean
}

export function ShowHeader({
  settings,
  generation,
  onGenerate,
  pending,
}: Props) {
  const [host, analyst] = settings.hosts
  const missing = generation.missing_keys
  const next = generation.next_episode_at
    ? `Next episode ${whenNext(generation.next_episode_at, settings.timezone)} (${settings.timezone}).`
    : "No episodes scheduled: choose days in Settings."

  return (
    <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-4xl leading-none font-extrabold font-stretch-[72%] sm:text-5xl">
          {settings.show_name}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {next} {LENGTHS[settings.length_minutes]}, {settings.tone}, with{" "}
          {host.name} and {analyst.name}.
        </p>
      </div>
      <div className="flex flex-col gap-1 sm:items-end">
        <Button
          size="lg"
          onClick={onGenerate}
          disabled={missing.length > 0 || pending}
        >
          Generate now
        </Button>
        {missing.length > 0 ? (
          <p className="max-w-xs text-sm text-muted-foreground sm:text-right">
            Generating needs {missing.join(" and ")} in .env.
          </p>
        ) : (
          generation.voice === "tone" && (
            <p className="max-w-xs text-sm text-muted-foreground sm:text-right">
              Audio is a test tone. Set WORKER_VOICE=elevenlabs for real voices.
            </p>
          )
        )}
      </div>
    </div>
  )
}
