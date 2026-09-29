import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  api,
  ApiError,
  type PodcastSettings,
  type PodcastSettingsUpdate,
} from "@/api/client"
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
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

const LENGTHS = [3, 5, 7] as const
const TONES = [
  { value: "casual", label: "Casual" },
  { value: "analytical", label: "Analytical" },
] as const
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const VOICES = { host: "George", analyst: "Sarah" } as const
const TIME_ZONES = Intl.supportedValuesOf("timeZone")

function editable(settings: PodcastSettings): PodcastSettingsUpdate {
  return {
    show_name: settings.show_name,
    length_minutes: settings.length_minutes,
    tone: settings.tone,
    hosts: settings.hosts,
    schedule_days: settings.schedule_days,
    schedule_time: settings.schedule_time.slice(0, 5),
    timezone: settings.timezone,
  }
}

export function ShowSettingsForm({ settings }: { settings: PodcastSettings }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(() => editable(settings))

  const save = useMutation({
    mutationFn: () => api.saveSettings(form),
    onSuccess: (saved) => {
      setForm(editable(saved))
      queryClient.setQueryData(["settings"], saved)
      void queryClient.invalidateQueries({ queryKey: ["generation"] })
    },
  })

  function set<K extends keyof PodcastSettingsUpdate>(
    key: K,
    value: PodcastSettingsUpdate[K]
  ) {
    setForm((current) => ({ ...current, [key]: value }))
    save.reset()
  }
  function setHost(
    index: number,
    field: "name" | "personality",
    value: string
  ) {
    set(
      "hosts",
      form.hosts.map((host, i) =>
        i === index ? { ...host, [field]: value } : host
      )
    )
  }

  return (
    <section aria-labelledby="your-show">
      <h2 id="your-show" className="mb-4 text-2xl font-bold font-stretch-[80%]">
        Your show
      </h2>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <FieldGroup>
          <FieldSet>
            <FieldLegend>Show</FieldLegend>
            <Field>
              <FieldLabel htmlFor="show-name">Name</FieldLabel>
              <Input
                id="show-name"
                value={form.show_name}
                maxLength={60}
                onChange={(event) => set("show_name", event.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel>Length</FieldLabel>
              <ToggleGroup
                value={[String(form.length_minutes)]}
                onValueChange={(value) =>
                  value[0] &&
                  set("length_minutes", Number(value[0]) as 3 | 5 | 7)
                }
                variant="outline"
                aria-label="Episode length"
              >
                {LENGTHS.map((minutes) => (
                  <ToggleGroupItem key={minutes} value={String(minutes)}>
                    {minutes} min
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </Field>
            <Field>
              <FieldLabel>Tone</FieldLabel>
              <ToggleGroup
                value={[form.tone]}
                onValueChange={(value) =>
                  value[0] &&
                  set("tone", value[0] as PodcastSettingsUpdate["tone"])
                }
                variant="outline"
                aria-label="Tone"
              >
                {TONES.map((tone) => (
                  <ToggleGroupItem key={tone.value} value={tone.value}>
                    {tone.label}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
              <FieldDescription>
                Casual is chattier; analytical brings more numbers and context.
              </FieldDescription>
            </Field>
          </FieldSet>

          <FieldSet>
            <FieldLegend>Hosts</FieldLegend>
            {form.hosts.map((host, index) => (
              <Field key={host.role}>
                <FieldLabel htmlFor={`host-${host.role}`}>
                  {host.role === "host" ? "Presenter" : "Analyst"}
                </FieldLabel>
                <Input
                  id={`host-${host.role}`}
                  value={host.name}
                  maxLength={30}
                  onChange={(event) =>
                    setHost(index, "name", event.target.value)
                  }
                />
                <Textarea
                  aria-label={`${host.role === "host" ? "Presenter" : "Analyst"} personality`}
                  value={host.personality}
                  maxLength={300}
                  rows={2}
                  onChange={(event) =>
                    setHost(index, "personality", event.target.value)
                  }
                />
                <FieldDescription>Voice: {VOICES[host.role]}.</FieldDescription>
              </Field>
            ))}
          </FieldSet>

          <FieldSet>
            <FieldLegend>Schedule</FieldLegend>
            <Field>
              <FieldLabel>Days</FieldLabel>
              <ToggleGroup
                multiple
                value={form.schedule_days.map(String)}
                onValueChange={(value) =>
                  set(
                    "schedule_days",
                    value.map(Number).sort((a, b) => a - b)
                  )
                }
                variant="outline"
                aria-label="Days"
              >
                {DAYS.map((day, index) => (
                  <ToggleGroupItem key={day} value={String(index + 1)}>
                    {day}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
              <FieldDescription>
                With no days selected, episodes come only when you ask.
              </FieldDescription>
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="schedule-time">Time</FieldLabel>
                <Input
                  id="schedule-time"
                  type="time"
                  value={form.schedule_time}
                  onChange={(event) => set("schedule_time", event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="time-zone">Time zone</FieldLabel>
                <Input
                  id="time-zone"
                  list="time-zones"
                  value={form.timezone}
                  onChange={(event) => set("timezone", event.target.value)}
                />
                <datalist id="time-zones">
                  {TIME_ZONES.map((zone) => (
                    <option key={zone} value={zone} />
                  ))}
                </datalist>
              </Field>
            </div>
          </FieldSet>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={save.isPending}>
              Save changes
            </Button>
            {save.isSuccess && (
              <span className="text-sm text-muted-foreground">Saved.</span>
            )}
          </div>
          {save.error && (
            <Alert variant="destructive">
              <AlertDescription>
                {save.error instanceof ApiError
                  ? save.error.message
                  : "Something went wrong."}
              </AlertDescription>
            </Alert>
          )}
        </FieldGroup>
      </form>
    </section>
  )
}
