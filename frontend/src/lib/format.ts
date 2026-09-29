export function clock(seconds: number): string {
  const whole = Math.floor(seconds)
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`
}

export function duration(seconds: number): string {
  const whole = Math.floor(seconds)
  return `${Math.floor(whole / 60)} min ${whole % 60} s`
}

function parts(
  iso: string,
  timeZone: string,
  options: Intl.DateTimeFormatOptions
): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone, ...options }).format(
    new Date(iso)
  )
}

function dayKey(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(date)
}

export function moment(iso: string, timeZone: string): string {
  const day = parts(iso, timeZone, {
    weekday: "long",
    day: "numeric",
    month: "long",
  })
  const time = parts(iso, timeZone, { hour: "2-digit", minute: "2-digit" })
  return `${day}, ${time}`
}

export function shortDay(iso: string, timeZone: string): string {
  return parts(iso, timeZone, {
    weekday: "short",
    day: "numeric",
    month: "short",
  })
}

export function whenNext(iso: string, timeZone: string): string {
  const now = new Date()
  const time = parts(iso, timeZone, { hour: "2-digit", minute: "2-digit" })
  const tomorrow = new Date(now.getTime() + 24 * 3600 * 1000)
  const day = dayKey(new Date(iso), timeZone)
  if (day === dayKey(now, timeZone)) return `today at ${time}`
  if (day === dayKey(tomorrow, timeZone)) return `tomorrow at ${time}`
  return `${parts(iso, timeZone, { weekday: "long", day: "numeric", month: "long" })} at ${time}`
}
