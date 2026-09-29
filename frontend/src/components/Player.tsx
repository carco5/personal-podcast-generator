import { useRef, useState } from "react"
import { PauseIcon, PlayIcon } from "lucide-react"

import { api, audioUrl, type EpisodeDetail, type Topic } from "@/api/client"
import { clock, duration as spoken, moment } from "@/lib/format"
import { createListenTracker } from "@/lib/listening"
import { TINT_BG, TINT_NAMES, tintOf } from "@/lib/sections"
import { cn } from "@/lib/utils"

type Props = { episode: EpisodeDetail; catalog: Topic[]; timeZone: string }

function report(
  episodeId: number,
  kind: "play" | "heartbeat",
  position: number
) {
  void api.listen(episodeId, kind, position).catch(() => {})
}

export function Player({ episode, catalog, timeZone }: Props) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const length = episode.duration_seconds ?? 0
  const [tracker] = useState(() =>
    createListenTracker(length, (start) =>
      report(episode.id, "heartbeat", start)
    )
  )

  const segments = episode.chapters.map((chapter, index) => ({
    ...chapter,
    from: index === 0 ? 0 : chapter.start_seconds,
    to: episode.chapters[index + 1]?.start_seconds ?? length,
  }))
  const current = segments.findLast((segment) => segment.from <= time)

  function toggle() {
    const element = audio.current
    if (element === null) return
    if (element.paused) void element.play()
    else element.pause()
  }

  function seek(to: number) {
    if (audio.current === null) return
    audio.current.currentTime = to
    setTime(to)
  }

  return (
    <section className="rounded-2xl bg-primary px-6 pt-5 pb-6 text-primary-foreground">
      <p className="flex flex-wrap gap-x-4 text-sm text-white/70">
        <span>
          News as of{" "}
          {moment(episode.news_as_of ?? episode.scheduled_for, timeZone)}
        </span>
        <span>{spoken(length)}</span>
      </p>
      <h2 className="mt-1 mb-4 max-w-[26ch] text-3xl leading-tight font-bold font-stretch-[72%]">
        {episode.title}
      </h2>

      <div className="mb-4 flex items-center gap-4">
        <button
          type="button"
          onClick={toggle}
          aria-label={playing ? "Pause" : "Play"}
          className="grid size-12 place-items-center rounded-full bg-white text-primary focus-visible:ring-3 focus-visible:ring-white/60 focus-visible:outline-none"
        >
          {playing ? (
            <PauseIcon className="size-5" />
          ) : (
            <PlayIcon className="ml-0.5 size-5" />
          )}
        </button>
        <div>
          <p>
            {clock(time)} / {clock(length)}
          </p>
          <p className="text-sm text-white/70">
            Now:{" "}
            <span className="font-semibold text-white">{current?.title}</span>
          </p>
        </div>
      </div>

      <div className="relative rounded-md has-[input:focus-visible]:ring-3 has-[input:focus-visible]:ring-white/60">
        <div className="flex h-9 gap-[3px]">
          {segments.map((segment) => {
            const played = Math.min(
              1,
              Math.max(0, (time - segment.from) / (segment.to - segment.from))
            )
            return (
              <div
                key={segment.key}
                style={{ flexGrow: segment.to - segment.from }}
                className={cn(
                  "relative rounded-sm",
                  TINT_BG[tintOf(segment.key, catalog)]
                )}
              >
                <div className="absolute inset-0 rounded-sm bg-primary/55" />
                <div
                  className={cn(
                    "absolute inset-y-0 left-0 rounded-sm",
                    TINT_BG[tintOf(segment.key, catalog)]
                  )}
                  style={{ width: `${played * 100}%` }}
                />
              </div>
            )
          })}
        </div>
        {/* An invisible native range input over the segments gives click, drag and keyboard */}
        {/* seeking; its 1 px thumb makes its scale span the full width of the track. */}
        <input
          type="range"
          min={0}
          max={length}
          step={1}
          value={time}
          onChange={(event) => seek(Number(event.target.value))}
          onKeyDown={(event) => {
            const jump = {
              ArrowRight: 5,
              ArrowUp: 5,
              ArrowLeft: -5,
              ArrowDown: -5,
            }[event.key]
            if (jump === undefined) return
            event.preventDefault()
            seek(Math.min(length, Math.max(0, time + jump)))
          }}
          aria-label="Position in the episode"
          aria-valuetext={`${clock(time)}, ${current?.title ?? ""}`}
          className="absolute inset-0 h-full w-full cursor-pointer appearance-none opacity-0 [&::-moz-range-thumb]:size-px [&::-webkit-slider-thumb]:size-px [&::-webkit-slider-thumb]:appearance-none"
        />
      </div>
      <div
        className="mt-2 hidden gap-[3px] text-xs text-white/70 sm:flex"
        aria-hidden="true"
      >
        {segments.map((segment) => (
          <span
            key={segment.key}
            style={{ flexGrow: segment.to - segment.from, flexBasis: 0 }}
            className="truncate"
          >
            {segment.title}
          </span>
        ))}
      </div>

      <p className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-white/70">
        {[
          ...new Set(segments.map((segment) => tintOf(segment.key, catalog))),
        ].map((tint) => (
          <span key={tint} className="flex items-center gap-1.5">
            <span className={cn("size-2.5 rounded-[3px]", TINT_BG[tint])} />
            {TINT_NAMES[tint]}
          </span>
        ))}
      </p>

      <audio
        ref={audio}
        src={audioUrl(episode.id)}
        preload="metadata"
        onPlay={(event) => {
          setPlaying(true)
          report(episode.id, "play", event.currentTarget.currentTime)
        }}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onSeeking={() => tracker.seek()}
        onTimeUpdate={(event) => {
          setTime(event.currentTarget.currentTime)
          tracker.update(event.currentTarget.currentTime)
        }}
      />
    </section>
  )
}
