import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  api,
  ApiError,
  type Interest,
  type InterestCreate,
  type Topic,
  type Weight,
} from "@/api/client"
import { RunningOrder } from "@/components/RunningOrder"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { TINT_BG } from "@/lib/sections"
import { cn } from "@/lib/utils"

const WEIGHTS: { value: Weight; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
]
const MAX_INTERESTS = 8

function WeightPicker(props: {
  weight: Weight
  label: string
  onChange: (weight: Weight) => void
}) {
  return (
    <ToggleGroup
      value={[props.weight]}
      onValueChange={(value) => value[0] && props.onChange(value[0] as Weight)}
      variant="outline"
      size="sm"
      aria-label={`Weight of ${props.label}`}
    >
      {WEIGHTS.map((weight) => (
        <ToggleGroupItem key={weight.value} value={weight.value}>
          {weight.label}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}

type Props = { catalog: Topic[]; interests: Interest[] }

export function SectionsEditor({ catalog, interests }: Props) {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [keywords, setKeywords] = useState("")

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["interests"] })
    void queryClient.invalidateQueries({ queryKey: ["generation"] })
  }
  const add = useMutation({
    mutationFn: (body: InterestCreate) => api.addInterest(body),
    onSuccess: (interest) => {
      if (interest.kind === "custom") {
        setName("")
        setKeywords("")
      }
      refresh()
    },
  })
  const remove = useMutation({
    mutationFn: api.removeInterest,
    onSuccess: refresh,
  })
  const weigh = useMutation({
    mutationFn: ({ id, weight }: { id: number; weight: Weight }) =>
      api.setWeight(id, weight),
    onSuccess: refresh,
  })
  const error = add.error ?? remove.error ?? weigh.error
  const busy = add.isPending || remove.isPending || weigh.isPending

  const byTopic = new Map(
    interests.map((interest) => [interest.topic, interest])
  )
  const custom = interests.filter((interest) => interest.kind === "custom")
  const full = interests.length >= MAX_INTERESTS
  const groups = [
    { sport: "football", title: "Football" },
    { sport: "basketball", title: "Basketball" },
  ].map((group) => ({
    ...group,
    topics: catalog.filter((topic) => topic.sport === group.sport),
  }))

  function addCustom(event: React.FormEvent) {
    event.preventDefault()
    const list = keywords
      .split(",")
      .map((word) => word.trim())
      .filter(Boolean)
    add.mutate({
      kind: "custom",
      topic: name.trim(),
      keywords: list,
      weight: "medium",
    })
  }

  return (
    <section aria-labelledby="your-sections" className="flex flex-col gap-6">
      <div>
        <h2
          id="your-sections"
          className="text-2xl font-bold font-stretch-[80%]"
        >
          Your sections
        </h2>
        <p className="text-muted-foreground">
          Each section you follow becomes a part of the episode. The weight sets
          how much time it gets. Changes are saved as you make them.
        </p>
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            {error instanceof ApiError
              ? error.message
              : "Something went wrong."}
          </AlertDescription>
        </Alert>
      )}

      {groups.map((group) => (
        <FieldSet key={group.sport}>
          <FieldLegend className="flex items-center gap-2">
            <span
              className={cn(
                "h-4 w-1 rounded-full",
                TINT_BG[group.sport === "football" ? "pitch" : "court"]
              )}
            />
            {group.title}
          </FieldLegend>
          <ul className="flex flex-col divide-y rounded-xl border bg-card">
            {group.topics.map((topic) => {
              const interest = byTopic.get(topic.key)
              return (
                <li
                  key={topic.key}
                  className="flex flex-wrap items-center gap-3 px-4 py-2.5"
                >
                  <Switch
                    checked={interest !== undefined}
                    disabled={busy || (interest === undefined && full)}
                    onCheckedChange={(on) =>
                      on
                        ? add.mutate({
                            kind: "catalog",
                            topic: topic.key,
                            weight: "medium",
                          })
                        : interest && remove.mutate(interest.id)
                    }
                    aria-label={topic.name}
                  />
                  <span
                    className={cn("grow", !interest && "text-muted-foreground")}
                  >
                    {topic.name}
                  </span>
                  {interest && (
                    <WeightPicker
                      weight={interest.weight}
                      label={topic.name}
                      onChange={(weight) =>
                        weigh.mutate({ id: interest.id, weight })
                      }
                    />
                  )}
                </li>
              )
            })}
          </ul>
        </FieldSet>
      ))}

      <FieldSet>
        <FieldLegend className="flex items-center gap-2">
          <span className={cn("h-4 w-1 rounded-full", TINT_BG.own)} />
          Your own topics
        </FieldLegend>
        <FieldDescription>
          Keywords are matched in the news this app already collects (the sports
          above).
        </FieldDescription>
        {custom.length > 0 && (
          <ul className="flex flex-col divide-y rounded-xl border bg-card">
            {custom.map((interest) => (
              <li
                key={interest.id}
                className="flex flex-wrap items-center gap-3 px-4 py-2.5"
              >
                <span className="grow">
                  {interest.topic}{" "}
                  <span className="text-sm text-muted-foreground">
                    ({interest.keywords.join(", ")})
                  </span>
                </span>
                <WeightPicker
                  weight={interest.weight}
                  label={interest.topic}
                  onChange={(weight) =>
                    weigh.mutate({ id: interest.id, weight })
                  }
                />
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busy}
                  onClick={() => remove.mutate(interest.id)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={addCustom}>
          <FieldGroup className="gap-3 sm:flex-row sm:items-end">
            <Field>
              <FieldLabel htmlFor="topic-name">Topic</FieldLabel>
              <Input
                id="topic-name"
                value={name}
                maxLength={60}
                onChange={(event) => setName(event.target.value)}
                placeholder="Luka Dončić"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="topic-keywords">
                Keywords, separated by commas
              </FieldLabel>
              <Input
                id="topic-keywords"
                value={keywords}
                onChange={(event) => setKeywords(event.target.value)}
                placeholder="Doncic, Dončić"
              />
            </Field>
            <Button
              type="submit"
              disabled={busy || full || !name.trim() || !keywords.trim()}
            >
              Add topic
            </Button>
          </FieldGroup>
        </form>
        {full && (
          <FieldDescription>
            You follow {MAX_INTERESTS} sections, the maximum.
          </FieldDescription>
        )}
      </FieldSet>

      <RunningOrder interests={interests} catalog={catalog} />
    </section>
  )
}
