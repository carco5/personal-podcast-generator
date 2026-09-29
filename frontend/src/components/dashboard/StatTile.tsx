import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type Props = {
  label: string
  value: string
  detail: ReactNode
  eyebrow?: string
  hero?: boolean
  children?: ReactNode
}

export function StatTile({
  label,
  value,
  detail,
  eyebrow,
  hero,
  children,
}: Props) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1 rounded-xl border bg-card p-4",
        hero && "sm:col-span-2"
      )}
    >
      <p className="text-sm text-muted-foreground">
        {eyebrow && (
          <span className="mr-2 text-xs font-semibold tracking-wide text-foreground uppercase">
            {eyebrow}
          </span>
        )}
        {label}
      </p>
      <p
        className={cn(
          "font-semibold [font-variant-numeric:proportional-nums]",
          hero ? "text-5xl" : "text-3xl"
        )}
      >
        {value}
      </p>
      {children}
      <p className="text-sm text-muted-foreground">{detail}</p>
    </div>
  )
}
