import type { EpisodeDetail } from "@/api/client"
import { Badge } from "@/components/ui/badge"
import { shortDay } from "@/lib/format"

type Props = { sources: EpisodeDetail["sources"]; timeZone: string }

export function Sources({ sources, timeZone }: Props) {
  return (
    <section aria-labelledby="sources">
      <h3 id="sources" className="mb-2 text-xl font-bold font-stretch-[80%]">
        Sources
      </h3>
      <ol>
        {sources.map((source) => (
          <li
            key={source.source_id}
            id={`source-${source.source_id}`}
            className="scroll-mt-4 border-t py-2.5"
          >
            <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>
                {source.source_id} {source.outlet},{" "}
                {shortDay(source.published_at, timeZone)}
              </span>
              {source.official && (
                <Badge variant="secondary">
                  {source.kind === "data" ? "Official data" : "Official"}
                </Badge>
              )}
            </p>
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="underline underline-offset-2"
            >
              {source.title}
            </a>
          </li>
        ))}
      </ol>
    </section>
  )
}
