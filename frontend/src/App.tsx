import { lazy, Suspense } from "react"
import { NavLink, Route, Routes } from "react-router"

import { cn } from "@/lib/utils"
import { EpisodesPage } from "@/pages/EpisodesPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import { SettingsPage } from "@/pages/SettingsPage"

const InternalPage = lazy(() =>
  import("@/pages/InternalPage").then((module) => ({
    default: module.InternalPage,
  }))
)

function linkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "text-muted-foreground hover:text-foreground",
    isActive &&
      "font-semibold text-foreground underline decoration-2 underline-offset-8"
  )
}

export function App() {
  return (
    <div className="min-h-svh">
      <header className="border-b bg-card">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="flex items-center gap-2 font-bold font-stretch-[85%]">
            <img src="/favicon.svg" alt="" className="size-6" />
            Personal Podcast
          </span>
          <NavLink to="/" end className={linkClass}>
            Episodes
          </NavLink>
          <NavLink to="/settings" className={linkClass}>
            Settings
          </NavLink>
          <NavLink
            to="/internal"
            className={(state) => cn(linkClass(state), "ml-auto text-sm")}
          >
            Internal
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<EpisodesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route
            path="/internal"
            element={
              <Suspense
                fallback={<p className="text-muted-foreground">Loading…</p>}
              >
                <InternalPage />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  )
}
