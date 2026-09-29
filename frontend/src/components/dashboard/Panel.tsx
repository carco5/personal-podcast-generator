import { useState, type ReactNode } from "react"

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

type Props = {
  title: string
  description: ReactNode
  table?: ReactNode
  children: ReactNode
}

export function Panel({ title, description, table, children }: Props) {
  const [asTable, setAsTable] = useState(false)
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        {table && (
          <CardAction>
            <ToggleGroup
              value={[asTable ? "table" : "chart"]}
              onValueChange={(value) =>
                value[0] && setAsTable(value[0] === "table")
              }
              aria-label={`Show ${title} as`}
            >
              <ToggleGroupItem value="chart">Chart</ToggleGroupItem>
              <ToggleGroupItem value="table">Table</ToggleGroupItem>
            </ToggleGroup>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>{asTable && table ? table : children}</CardContent>
    </Card>
  )
}
