import type { Interest, Topic } from "@/api/client"
import { TINT_BG, tintOf } from "@/lib/sections"
import { cn } from "@/lib/utils"

type Props = { interests: Interest[]; catalog: Topic[] }

export function RunningOrder({ interests, catalog }: Props) {
  const nameOf = (interest: Interest) =>
    catalog.find((topic) => topic.key === interest.topic)?.name ??
    interest.topic

  return (
    <section aria-labelledby="running-order">
      <h3 id="running-order" className="text-xl font-bold font-stretch-[80%]">
        Running order
      </h3>
      <p className="mb-2 text-sm text-muted-foreground">
        Sections play grouped by sport, the sport with your highest weight
        first. Within a sport, higher weights play first, then the order you
        added them. A section with no fresh news that day is left out.
      </p>
      {interests.length === 0 ? (
        <p className="text-muted-foreground">
          Turn on a section to build your episode.
        </p>
      ) : (
        <ol className="list-inside list-decimal">
          {interests.map((interest) => (
            <li key={interest.id} className="py-1">
              <span
                className={cn(
                  "mr-2 inline-block size-2.5 rounded-[3px]",
                  TINT_BG[tintOf(interest.topic, catalog)]
                )}
              />
              {nameOf(interest)}{" "}
              <span className="text-sm text-muted-foreground">
                ({interest.weight})
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
