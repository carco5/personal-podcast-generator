import { useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import { SectionsEditor } from "@/components/SectionsEditor"
import { ShowSettingsForm } from "@/components/ShowSettingsForm"

export function SettingsPage() {
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog })
  const interests = useQuery({
    queryKey: ["interests"],
    queryFn: api.interests,
  })
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings })

  if (catalog.isError || interests.isError || settings.isError) {
    return (
      <p role="alert">
        The app could not reach the API. Is the api container running?
      </p>
    )
  }
  if (!catalog.data || !interests.data || !settings.data) {
    return <p className="text-muted-foreground">Loading your settings…</p>
  }

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-4xl leading-none font-extrabold font-stretch-[72%] sm:text-5xl">
        Settings
      </h1>
      <div className="grid gap-10 lg:grid-cols-[1.25fr_1fr]">
        <SectionsEditor catalog={catalog.data} interests={interests.data} />
        <ShowSettingsForm settings={settings.data} />
      </div>
    </div>
  )
}
