import { describe, expect, it } from "vitest"

import { createListenTracker } from "./listening"

function listener(duration = 300) {
  const sent: number[] = []
  const tracker = createListenTracker(duration, (start) => sent.push(start))
  const play = (from: number, to: number, every = 0.25) => {
    for (let position = from; position <= to; position += every)
      tracker.update(position)
  }
  return { sent, tracker, play }
}

describe("createListenTracker", () => {
  it("reports each 15 s slot once, with its start", () => {
    const { sent, play } = listener()
    play(0, 45)
    expect(sent).toEqual([0, 15, 30])
  })

  it("counts audio time, not wall-clock time", () => {
    const { sent, play } = listener()
    play(0, 45, 0.5)
    expect(sent).toEqual([0, 15, 30])
  })

  it("never counts a replayed slot twice", () => {
    const { sent, tracker, play } = listener()
    play(0, 20)
    tracker.seek()
    play(0, 20)
    expect(sent).toEqual([0])
  })

  it("does not add up two partial passes over the same seconds", () => {
    const { sent, tracker, play } = listener()
    play(0, 8)
    tracker.seek()
    play(0, 8)
    expect(sent).toEqual([])
  })

  it("does not count what a jump skips", () => {
    const { sent, tracker, play } = listener()
    play(0, 10)
    tracker.seek()
    play(14, 30)
    expect(sent).toEqual([15])
  })

  it("ignores big or backward steps", () => {
    const { sent, tracker } = listener()
    for (const position of [0, 60, 30, 31]) tracker.update(position)
    expect(sent).toEqual([])
  })

  it("keeps what was heard across a pause", () => {
    const { sent, play } = listener()
    play(0, 12)
    play(12.25, 15)
    expect(sent).toEqual([0])
  })

  it("completes the shorter last slot at the end of the episode", () => {
    const { sent, tracker, play } = listener(50)
    tracker.seek()
    play(30, 50)
    expect(sent).toEqual([30, 45])
  })
})
