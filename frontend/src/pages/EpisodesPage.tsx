import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, ApiError } from "@/api/client"
import { EpisodeList } from "@/components/EpisodeList"
import { Player } from "@/components/Player"
import { ShowHeader } from "@/components/ShowHeader"
import { Sources } from "@/components/Sources"
import { Transcript } from "@/components/Transcript"
import { Alert, AlertDescription } from "@/components/ui/alert"

const POLL_MS = 3000

export function EpisodesPage() {
  const queryClient = useQueryClient()
  const [chosenId, setChosenId] = useState<number | null>(null)

  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings })
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog })
  const generation = useQuery({
    queryKey: ["generation"],
    queryFn: api.generation,
  })
  const episodes = useQuery({
    queryKey: ["episodes"],
    queryFn: api.episodes,
    refetchInterval: (query) =>
      query.state.data?.episodes.some(
        (e) => e.status === "queued" || e.status === "in_progress"
      )
        ? POLL_MS
        : false,
  })

  const list = episodes.data?.episodes ?? []
  const selectedId =
    chosenId ?? list.find((e) => e.status === "completed")?.id ?? null
  const detail = useQuery({
    queryKey: ["episode", selectedId],
    queryFn: () => api.episode(selectedId!),
    enabled: selectedId !== null,
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["episodes"] })
    void queryClient.invalidateQueries({ queryKey: ["generation"] })
  }
  const generate = useMutation({ mutationFn: api.generate, onSuccess: refresh })
  const retry = useMutation({ mutationFn: api.retry, onSuccess: refresh })
  const error = generate.error ?? retry.error

  if (
    settings.isError ||
    catalog.isError ||
    generation.isError ||
    episodes.isError
  ) {
    return (
      <p role="alert">
        The app could not reach the API. Is the api container running?
      </p>
    )
  }
  if (!settings.data || !catalog.data || !generation.data || !episodes.data) {
    return <p className="text-muted-foreground">Loading your podcast…</p>
  }
  const timeZone = settings.data.timezone

  return (
    <div className="flex flex-col gap-8">
      <div>
        <ShowHeader
          settings={settings.data}
          generation={generation.data}
          onGenerate={() => generate.mutate()}
          pending={generate.isPending}
        />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              {error instanceof ApiError
                ? error.message
                : "Something went wrong."}
            </AlertDescription>
          </Alert>
        )}
      </div>

      {detail.data && (
        <Player
          key={detail.data.id}
          episode={detail.data}
          catalog={catalog.data}
          timeZone={timeZone}
        />
      )}

      <section aria-labelledby="your-episodes">
        <h3
          id="your-episodes"
          className="mb-2 text-xl font-bold font-stretch-[80%]"
        >
          Your episodes
        </h3>
        <EpisodeList
          episodes={list}
          selectedId={selectedId}
          timeZone={timeZone}
          onSelect={setChosenId}
          onRetry={(id) => retry.mutate(id)}
          retrying={retry.isPending ? (retry.variables ?? null) : null}
          now={episodes.dataUpdatedAt}
        />
      </section>

      {detail.data && (
        <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
          <Transcript
            sections={detail.data.transcript}
            hosts={settings.data.hosts}
            catalog={catalog.data}
          />
          <Sources sources={detail.data.sources} timeZone={timeZone} />
        </div>
      )}
    </div>
  )
}
