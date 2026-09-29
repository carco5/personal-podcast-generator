import { AlertTriangle } from "lucide-react"

import type { OperationsMetrics, Run } from "@/api/client"
import { Panel } from "@/components/dashboard/Panel"
import { StatTile } from "@/components/dashboard/StatTile"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { count, duration, percent, usd, utcMoment } from "@/lib/format"
import { cn } from "@/lib/utils"

const PROVIDERS: Record<string, string> = {
  fetch: "News sites",
  select: "OpenAI",
  write: "OpenAI",
  check: "OpenAI",
  voice: "ElevenLabs",
  master: "ffmpeg (local)",
}

const CATEGORIES: Record<string, string> = {
  "spending cap": "Stopped by the daily spending cap",
  Interrupted: "Interrupted (the worker stopped)",
}

type Props = {
  data: OperationsMetrics
  missingKeys: string[]
  onRetry: (id: number) => void
  retrying: number | null
}

function seconds(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  return value < 100 ? `${Math.round(value)} s` : duration(value)
}

export function OperationsTab({ data, missingKeys, onRetry, retrying }: Props) {
  const { outcomes, cost, spend, voice_month: voice } = data
  const ran = outcomes.completed + outcomes.failed
  const total = cost.openai_usd + cost.elevenlabs_usd
  const perEpisode = (value: number) =>
    cost.completed ? value / cost.completed : 0
  const overCap = spend.last_24h_usd >= spend.daily_cap_usd
  const used = spend.daily_cap_usd
    ? Math.min(1, spend.last_24h_usd / spend.daily_cap_usd)
    : 1

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Pipeline success"
          value={percent(outcomes.completed, ran)}
          detail={`${outcomes.failed} failed · ${outcomes.capped} stopped by the spending cap · ${outcomes.skipped} skipped (nothing new)`}
        />
        <StatTile
          label="Cost per episode"
          value={cost.completed ? usd(perEpisode(total)) : "—"}
          detail={`OpenAI ${usd(perEpisode(cost.openai_usd))} · ElevenLabs ${usd(perEpisode(cost.elevenlabs_usd))}, all attempts`}
        />
        <StatTile
          label="Spent in the last 24 hours"
          value={usd(spend.last_24h_usd)}
          detail={`Real calls only. Daily cap ${usd(spend.daily_cap_usd)}`}
        >
          <span className="my-1 block h-2 overflow-hidden rounded-full bg-seq-1">
            <span
              className={cn(
                "block h-full",
                overCap ? "bg-destructive" : "bg-chart"
              )}
              style={{ width: `${100 * used}%` }}
            />
          </span>
          {overCap && (
            <span className="flex items-center gap-1 text-sm font-medium text-destructive">
              <AlertTriangle className="size-4" aria-hidden />
              Cap reached: new episodes wait
            </span>
          )}
        </StatTile>
        <StatTile
          label="ElevenLabs characters this month"
          value={count(voice.billed_characters)}
          detail={`Billed since ${utcMoment(voice.month_start).split(",")[0]}. ${count(voice.reused_characters)} reused from the cache, not billed again`}
        />
      </div>

      <Panel
        title="Stages"
        description="Every stage run in the last 28 days. Durations are for successful runs; each stage talks to one provider, so its failures are that provider's."
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Stage</TableHead>
              <TableHead>Talks to</TableHead>
              <TableHead className="text-right">Runs</TableHead>
              <TableHead className="text-right">Success</TableHead>
              <TableHead className="text-right">Median</TableHead>
              <TableHead className="text-right">p95</TableHead>
              <TableHead className="text-right">Cost per run</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.stages.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-muted-foreground">
                  No stage runs in the last 28 days.
                </TableCell>
              </TableRow>
            )}
            {data.stages.map((stage) => (
              <TableRow key={stage.stage}>
                <TableCell className="font-medium">{stage.stage}</TableCell>
                <TableCell className="text-muted-foreground">
                  {PROVIDERS[stage.stage]}
                </TableCell>
                <TableCell className="text-right">
                  {count(stage.runs)}
                </TableCell>
                <TableCell className="text-right">
                  {percent(stage.runs - stage.failed, stage.runs)}
                  {stage.failed > 0 && (
                    <span className="text-muted-foreground">
                      {" "}
                      ({stage.failed} failed)
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {seconds(stage.p50_seconds)}
                </TableCell>
                <TableCell className="text-right">
                  {seconds(stage.p95_seconds)}
                </TableCell>
                <TableCell className="text-right">
                  {usd(stage.runs ? stage.cost_usd / stage.runs : 0)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>

      <Panel
        title="Why episodes failed"
        description="Failed episodes in the last 28 days, by the stage that stopped them."
      >
        {data.failures.length === 0 ? (
          <p className="text-muted-foreground">
            No failures in the last 28 days.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {data.failures.map((failure) => (
              <li key={failure.category} className="flex flex-col gap-0.5">
                <span>
                  <span className="font-semibold">{failure.count}</span>{" "}
                  {CATEGORIES[failure.category] ??
                    `Failed at ${failure.category}`}
                </span>
                <span className="text-sm text-muted-foreground">
                  Latest: {failure.latest}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Latest runs"
        description="The 20 most recent episodes, with the stages of their last attempt. Times in UTC."
      >
        <RunsTable
          runs={data.runs}
          missingKeys={missingKeys}
          onRetry={onRetry}
          retrying={retrying}
        />
      </Panel>
    </div>
  )
}

function RunsTable({
  runs,
  missingKeys,
  onRetry,
  retrying,
}: {
  runs: Run[]
  missingKeys: string[]
  onRetry: (id: number) => void
  retrying: number | null
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Episode</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Due</TableHead>
          <TableHead>Ready</TableHead>
          <TableHead className="hidden md:table-cell">Stages</TableHead>
          <TableHead className="text-right">Cost</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const late =
            run.trigger === "scheduled" &&
            run.status === "completed" &&
            run.finished_at !== null &&
            run.finished_at > run.scheduled_for
          return (
            <TableRow key={run.id}>
              <TableCell>
                <span className="flex flex-col">
                  <span className="font-medium">#{run.id}</span>
                  <span className="text-xs text-muted-foreground">
                    {run.simulated ? "Simulated" : "Real"} · {run.trigger}
                  </span>
                </span>
              </TableCell>
              <TableCell>
                <Badge
                  variant={run.status === "failed" ? "destructive" : "outline"}
                >
                  {run.status.replace("_", " ")}
                </Badge>
              </TableCell>
              <TableCell className="whitespace-nowrap">
                {utcMoment(run.scheduled_for)}
                {run.trigger === "manual" && (
                  <span className="text-muted-foreground"> (asked)</span>
                )}
              </TableCell>
              <TableCell className="whitespace-nowrap">
                {run.finished_at ? utcMoment(run.finished_at) : "—"}
                {late && <span className="text-muted-foreground"> (late)</span>}
              </TableCell>
              <TableCell className="hidden max-w-72 text-xs whitespace-normal text-muted-foreground md:table-cell">
                {run.stages.length === 0
                  ? (run.status_reason ??
                    (run.status === "completed"
                      ? "No stage records"
                      : "Not started"))
                  : run.stages.map((stage, index) => (
                      <span
                        key={index}
                        className={cn(
                          stage.status === "failed" &&
                            "font-medium text-destructive"
                        )}
                      >
                        {index > 0 && " · "}
                        {stage.stage} {seconds(stage.seconds)}
                        {stage.status === "failed" && " (failed)"}
                      </span>
                    ))}
              </TableCell>
              <TableCell className="text-right">{usd(run.cost_usd)}</TableCell>
              <TableCell className="text-right">
                {run.status === "failed" && !run.simulated && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={missingKeys.length > 0 || retrying === run.id}
                    title={
                      missingKeys.length > 0
                        ? `Needs ${missingKeys.join(" and ")} in .env`
                        : undefined
                    }
                    onClick={() => onRetry(run.id)}
                  >
                    Retry
                  </Button>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
