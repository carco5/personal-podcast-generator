import type { EpisodeDetail, Host, Topic } from "@/api/client"
import { TINT_BG, tintOf } from "@/lib/sections"
import { cn } from "@/lib/utils"

type Props = {
  sections: EpisodeDetail["transcript"]
  hosts: Host[]
  catalog: Topic[]
}

export function Transcript({ sections, hosts, catalog }: Props) {
  const names = Object.fromEntries(hosts.map((host) => [host.role, host.name]))

  return (
    <section aria-labelledby="transcript">
      <h3 id="transcript" className="mb-2 text-xl font-bold font-stretch-[80%]">
        Transcript
      </h3>
      {sections.map((section) => (
        <div key={section.key}>
          <h4 className="mt-5 mb-2 flex items-center gap-2.5 font-semibold">
            <span
              className={cn(
                "h-4.5 w-1 rounded-full",
                TINT_BG[tintOf(section.key, catalog)]
              )}
            />
            {section.title}
          </h4>
          {section.turns.map((turn, index) => (
            <p
              key={index}
              className="my-1.5 grid max-w-[70ch] grid-cols-[4.5rem_1fr] gap-2.5"
            >
              <span className="font-semibold text-muted-foreground">
                {names[turn.speaker]}
              </span>
              <span>
                {turn.text}
                {turn.source_ids.map((sourceId) => (
                  <a
                    key={sourceId}
                    href={`#source-${sourceId}`}
                    className="ml-1.5 rounded-sm border px-1 text-xs whitespace-nowrap text-muted-foreground hover:text-foreground"
                  >
                    {sourceId}
                  </a>
                ))}
              </span>
            </p>
          ))}
        </div>
      ))}
    </section>
  )
}
