import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  XAxis,
  YAxis,
} from "recharts"

import type { ProductMetrics, Topic } from "@/api/client"
import { Panel } from "@/components/dashboard/Panel"
import { StatTile } from "@/components/dashboard/StatTile"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { count, percent, utcDay } from "@/lib/format"
import { TINT_BG, tintOf } from "@/lib/sections"
import { cn } from "@/lib/utils"

const WEEKLY: ChartConfig = {
  listens: { label: "Engaged listens", color: "var(--chart)" },
}
const DROP_OFF: ChartConfig = {
  listening: { label: "Still listening (%)", color: "var(--chart)" },
}

type Props = { data: ProductMetrics; catalog: Topic[] }

export function ProductTab({ data, catalog }: Props) {
  const weeks = data.weeks
  const [before, lastFull] = [weeks[weeks.length - 3], weeks[weeks.length - 2]]
  const change = lastFull.engaged_listens - before.engaged_listens
  const { funnel, activation, delivery, depth } = data

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile
          hero
          eyebrow="North Star"
          label="Engaged listens, last full week"
          value={count(lastFull.engaged_listens)}
          detail={`${change === 0 ? "No change" : `${change > 0 ? "▲" : "▼"} ${Math.abs(change)}`} vs the week before · week of ${utcDay(lastFull.week_start)}`}
        />
        <StatTile
          label="Engaged listeners"
          value={count(lastFull.engaged_listeners)}
          detail="People with an engaged listen in that week"
        />
        <StatTile
          label="Activation"
          value={percent(activation.activated, activation.new_listeners)}
          detail={`Of ${activation.new_listeners} new ${activation.new_listeners === 1 ? "listener" : "listeners"}, heard their first episode within 24 h`}
        />
        <StatTile
          label="On-time delivery"
          value={percent(delivery.on_time, delivery.due)}
          detail={`${delivery.on_time} of ${delivery.due} scheduled episodes ready by their time (28 days)`}
        />
      </div>

      <Panel
        title="Engaged listens per week"
        description="Episodes heard for at least 40% of their length, counted in the week they crossed it (Monday to Sunday, UTC). The last bar is this week, still in progress."
        table={<WeeklyTable data={data} />}
      >
        <ChartContainer config={WEEKLY} className="aspect-auto h-60 w-full">
          <BarChart
            data={weeks.map((week, index) => ({
              label:
                index === weeks.length - 1
                  ? "This week"
                  : utcDay(week.week_start),
              listens: week.engaged_listens,
              labelled:
                index === weeks.length - 2 ? week.engaged_listens : null,
              current: index === weeks.length - 1,
            }))}
            margin={{ top: 24, left: 0, right: 8 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={36}
              allowDecimals={false}
            />
            <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
            <Bar dataKey="listens" radius={[4, 4, 0, 0]} maxBarSize={24}>
              {weeks.map((week, index) => (
                <Cell
                  key={week.week_start}
                  fill={
                    index === weeks.length - 1
                      ? "var(--chart-soft)"
                      : "var(--color-listens)"
                  }
                />
              ))}
              <LabelList
                dataKey="labelled"
                position="top"
                className="fill-foreground font-semibold"
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Funnel"
          description={`Episodes ready between ${utcDay(funnel.since)} and ${utcDay(funnel.until)}, so each had at least a day to be heard.`}
        >
          <Funnel data={data} />
        </Panel>

        <Panel
          title="Where listeners drop off"
          description={
            depth.played === 0
              ? "The share of played episodes still listening at each point."
              : `Of ${depth.played} played episodes, the share still listening at each point. On average they heard ${percent(depth.average_share_heard, 1)} of the episode.`
          }
          table={<DropOffTable data={data} />}
        >
          {depth.played === 0 ? (
            <p className="text-muted-foreground">
              No played episodes in this window yet.
            </p>
          ) : (
            <ChartContainer
              config={DROP_OFF}
              className="aspect-auto h-60 w-full"
            >
              <AreaChart
                data={depth.drop_off.map((point) => ({
                  at: `${Math.round(point.share_of_episode * 100)}%`,
                  listening: Math.round((100 * point.listening) / depth.played),
                }))}
                margin={{ top: 12, left: 0, right: 8 }}
              >
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="at"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tickFormatter={(value: number) => `${value}%`}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area
                  dataKey="listening"
                  type="linear"
                  stroke="var(--color-listening)"
                  strokeWidth={2}
                  fill="var(--color-listening)"
                  fillOpacity={0.1}
                />
              </AreaChart>
            </ChartContainer>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Topics"
          description="In played episodes: how many reached each section, and of those, how many heard it to the end."
        >
          <TopicsTable data={data} catalog={catalog} />
        </Panel>

        <Panel
          title="Retention by signup week"
          description="Share of each week's new listeners with an engaged listen in their first week (days 0–6) and in their fourth (days 21–27). Darker is higher; — means not reached yet."
        >
          <CohortTable data={data} />
        </Panel>
      </div>
    </div>
  )
}

function WeeklyTable({ data }: { data: ProductMetrics }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Week of (UTC)</TableHead>
          <TableHead className="text-right">Engaged listens</TableHead>
          <TableHead className="text-right">Engaged listeners</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.weeks.map((week, index) => (
          <TableRow key={week.week_start}>
            <TableCell>
              {utcDay(week.week_start)}
              {index === data.weeks.length - 1 && " (in progress)"}
            </TableCell>
            <TableCell className="text-right">{week.engaged_listens}</TableCell>
            <TableCell className="text-right">
              {week.engaged_listeners}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Funnel({ data }: { data: ProductMetrics }) {
  const { funnel } = data
  const steps = [
    { label: "Generated", note: "episodes ready", value: funnel.generated },
    { label: "Played", note: "pressed play", value: funnel.played },
    { label: "Streamed", note: "heard 60 s or more", value: funnel.streamed },
    { label: "Engaged", note: "heard 40% or more", value: funnel.engaged },
  ]
  return (
    <ol className="flex flex-col gap-4">
      {steps.map((step) => (
        <li
          key={step.label}
          className="grid grid-cols-[7.5rem_1fr] items-center gap-3"
        >
          <span className="flex flex-col">
            <span className="font-medium">{step.label}</span>
            <span className="text-xs text-muted-foreground">{step.note}</span>
          </span>
          <span className="flex items-center gap-3">
            <span className="flex-1">
              <span
                className="block h-4 rounded-r-[4px] bg-chart"
                style={{
                  width: `${funnel.generated ? (100 * step.value) / funnel.generated : 0}%`,
                  minWidth: step.value > 0 ? 2 : 0,
                }}
              />
            </span>
            <span className="w-24 text-right text-sm">
              <span className="font-semibold">{count(step.value)}</span>{" "}
              <span className="text-muted-foreground">
                {percent(step.value, funnel.generated)}
              </span>
            </span>
          </span>
        </li>
      ))}
    </ol>
  )
}

function DropOffTable({ data }: { data: ProductMetrics }) {
  const { depth } = data
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Point of the episode</TableHead>
          <TableHead className="text-right">Episodes still playing</TableHead>
          <TableHead className="text-right">Share</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {depth.drop_off.map((point) => (
          <TableRow key={point.share_of_episode}>
            <TableCell>{Math.round(point.share_of_episode * 100)}%</TableCell>
            <TableCell className="text-right">{point.listening}</TableCell>
            <TableCell className="text-right">
              {percent(point.listening, depth.played)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TopicsTable({
  data,
  catalog,
}: {
  data: ProductMetrics
  catalog: Topic[]
}) {
  const share = (row: ProductMetrics["topics"][number]) =>
    row.started ? row.finished / row.started : -1
  const rows = [...data.topics].sort((a, b) => share(b) - share(a))
  if (rows.length === 0)
    return (
      <p className="text-muted-foreground">
        No played episodes in this window yet.
      </p>
    )
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Topic</TableHead>
          <TableHead className="hidden text-right sm:table-cell">
            Episodes
          </TableHead>
          <TableHead className="text-right">Reached</TableHead>
          <TableHead>Finished</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.topic}>
            <TableCell className="whitespace-normal">
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    "size-2 shrink-0 rounded-full",
                    TINT_BG[tintOf(row.topic, catalog)]
                  )}
                />
                {row.name}
              </span>
            </TableCell>
            <TableCell className="hidden text-right sm:table-cell">
              {row.episodes}
            </TableCell>
            <TableCell className="text-right">
              {percent(row.started, row.episodes)}
            </TableCell>
            <TableCell>
              <span className="flex items-center gap-2 whitespace-nowrap">
                <span className="hidden h-1.5 w-12 overflow-hidden rounded-full bg-seq-1 sm:block">
                  <span
                    className="block h-full bg-chart"
                    style={{
                      width: `${row.started ? (100 * row.finished) / row.started : 0}%`,
                    }}
                  />
                </span>
                {percent(row.finished, row.started)}
              </span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function CohortTable({ data }: { data: ProductMetrics }) {
  const cell = (retained: number, eligible: number) => {
    if (eligible === 0)
      return <TableCell className="text-muted-foreground">—</TableCell>
    const share = retained / eligible
    const shade =
      share >= 0.75
        ? "bg-seq-3"
        : share >= 0.5
          ? "bg-seq-2"
          : share >= 0.25
            ? "bg-seq-1"
            : ""
    return (
      <TableCell className={shade}>
        {percent(retained, eligible)}{" "}
        <span className="hidden text-xs sm:inline">
          ({retained}/{eligible})
        </span>
      </TableCell>
    )
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Signup week</TableHead>
          <TableHead className="text-right">Listeners</TableHead>
          <TableHead>Week 1</TableHead>
          <TableHead>Week 4</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.cohorts.map((cohort) => (
          <TableRow key={cohort.week_start}>
            <TableCell>{utcDay(cohort.week_start)}</TableCell>
            <TableCell className="text-right">{cohort.listeners}</TableCell>
            {cell(cohort.week1_retained, cohort.week1_eligible)}
            {cell(cohort.week4_retained, cohort.week4_eligible)}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
