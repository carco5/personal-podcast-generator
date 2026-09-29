// Thin typed client for the backend API; the types are generated from FastAPI's OpenAPI
// document (npm run api:types).
import type { components } from "./schema"

type Schemas = components["schemas"]
export type Topic = Schemas["Topic"]
export type PodcastSettings = Schemas["PodcastSettingsRead"]
export type PodcastSettingsUpdate = Schemas["PodcastSettingsUpdate"]
export type Host = Schemas["Host"]
export type Interest = Schemas["InterestRead"]
export type InterestCreate = Schemas["InterestCreate"]
export type Weight = Interest["weight"]
export type Episode = Schemas["EpisodeRead"]
export type EpisodeDetail = Schemas["EpisodeDetail"]
export type EpisodePage = Schemas["EpisodePage"]
export type Generation = Schemas["Generation"]
export type ListenKind = Schemas["ListenEventCreate"]["kind"]
export type ProductMetrics = Schemas["ProductMetrics"]
export type OperationsMetrics = Schemas["OperationsMetrics"]
export type Run = Schemas["RunRow"]

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail))
    return detail
      .map((problem) => String(problem.msg).replace(/^Value error, /, ""))
      .join("; ")
  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, errorMessage(body, response.statusText))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function json(method: string, body: unknown): RequestInit {
  return { method, body: JSON.stringify(body) }
}

export const api = {
  catalog: () => request<Topic[]>("/catalog"),
  settings: () => request<PodcastSettings>("/settings"),
  saveSettings: (body: PodcastSettingsUpdate) =>
    request<PodcastSettings>("/settings", json("PUT", body)),
  interests: () => request<Interest[]>("/interests"),
  addInterest: (body: InterestCreate) =>
    request<Interest>("/interests", json("POST", body)),
  setWeight: (id: number, weight: Weight) =>
    request<Interest>(`/interests/${id}`, json("PATCH", { weight })),
  removeInterest: (id: number) =>
    request<void>(`/interests/${id}`, { method: "DELETE" }),
  episodes: () => request<EpisodePage>("/episodes"),
  episode: (id: number) => request<EpisodeDetail>(`/episodes/${id}`),
  generate: () => request<Episode>("/episodes", { method: "POST" }),
  retry: (id: number) =>
    request<Episode>(`/episodes/${id}/retry`, { method: "POST" }),
  listen: (id: number, kind: ListenKind, position_seconds: number) =>
    request<void>(
      `/episodes/${id}/listen-events`,
      json("POST", { kind, position_seconds })
    ),
  generation: () => request<Generation>("/generation"),
  product: (includeSimulated: boolean) =>
    request<ProductMetrics>(
      `/internal/product?include_simulated=${includeSimulated}`
    ),
  operations: (includeSimulated: boolean) =>
    request<OperationsMetrics>(
      `/internal/operations?include_simulated=${includeSimulated}`
    ),
  retryRun: (id: number) =>
    request<Episode>(`/internal/episodes/${id}/retry`, { method: "POST" }),
}

export function audioUrl(id: number): string {
  return `/api/v1/episodes/${id}/audio`
}
