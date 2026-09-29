import type { Topic } from "@/api/client"

export type Tint = "pitch" | "court" | "frame" | "own"

export const TINT_BG: Record<Tint, string> = {
  pitch: "bg-pitch",
  court: "bg-court",
  frame: "bg-frame",
  own: "bg-own",
}

export const TINT_NAMES: Record<Tint, string> = {
  pitch: "Football",
  court: "Basketball",
  frame: "Intro and closing",
  own: "Your own topics",
}

export function tintOf(key: string, catalog: Topic[]): Tint {
  if (key === "intro" || key === "closing") return "frame"
  const topic = catalog.find((item) => item.key === key)
  if (topic === undefined) return "own"
  return topic.sport === "football" ? "pitch" : "court"
}
