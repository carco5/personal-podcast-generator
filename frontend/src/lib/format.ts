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

export function percent(part: number, whole: number): string {
  if (whole <= 0) return "—"
  const value = (100 * part) / whole
  const rounded = Math.round(value)
  if (rounded === 100 && part < whole) return `${Math.floor(value * 10) / 10}%`
  if (rounded === 0 && part > 0) return `${Math.ceil(value * 10) / 10}%`
  return `${rounded}%`
}

export function usd(value: number): string {
  return `$${value.toFixed(2)}`
}

export function count(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: value >= 100_000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value)
}

export function utcDay(iso: string): string {
  return parts(iso, "UTC", { day: "numeric", month: "short" })
}

export function utcMoment(iso: string): string {
  const time = parts(iso, "UTC", { hour: "2-digit", minute: "2-digit" })
  return `${utcDay(iso)}, ${time}`
}
