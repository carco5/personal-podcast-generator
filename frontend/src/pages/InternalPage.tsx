import { useState } from "react"
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import { api } from "@/api/client"
import { OperationsTab } from "@/components/dashboard/OperationsTab"
import { ProductTab } from "@/components/dashboard/ProductTab"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

export function InternalPage() {
  const queryClient = useQueryClient()
  const [includeSimulated, setIncludeSimulated] = useState(true)

  const product = useQuery({
    queryKey: ["internal", "product", includeSimulated],
    queryFn: () => api.product(includeSimulated),
    placeholderData: keepPreviousData,
  })
  const operations = useQuery({
    queryKey: ["internal", "operations", includeSimulated],
    queryFn: () => api.operations(includeSimulated),
    placeholderData: keepPreviousData,
  })
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog })
  const generation = useQuery({
    queryKey: ["generation"],
    queryFn: api.generation,
  })
  const retry = useMutation({
    mutationFn: api.retryRun,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["internal"] }),
  })

  if (
    product.isError ||
    operations.isError ||
    catalog.isError ||
    generation.isError
  ) {
    return <p role="alert">The dashboard could not load. Is the API running?</p>
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold font-stretch-[85%]">
          Internal dashboard
        </h1>
        <p className="text-muted-foreground">
          How the product is doing, for the team. Listeners never see this page.
        </p>
      </header>

      <div className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm">
          <Badge variant="outline" className="mr-2">
            Simulated data
          </Badge>
          {product.data?.simulated_listeners ?? "…"} simulated listeners,
          created when the app first started, share the tables with the real
          ones so the charts have something to show. Turn them off to see only
          real use.
        </p>
        <label className="flex shrink-0 items-center gap-2 text-sm font-medium">
          <Switch
            checked={includeSimulated}
            onCheckedChange={setIncludeSimulated}
          />
          Include simulated data
        </label>
      </div>

      {retry.error && (
        <Alert variant="destructive">
          <AlertDescription>{retry.error.message}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="product">
        <TabsList>
          <TabsTrigger value="product">Product</TabsTrigger>
          <TabsTrigger value="operations">Operations</TabsTrigger>
        </TabsList>
        <TabsContent
          value="product"
          className={cn(
            "pt-4 transition-opacity",
            product.isPlaceholderData && "opacity-60"
          )}
        >
          {product.data && catalog.data ? (
            <ProductTab data={product.data} catalog={catalog.data} />
          ) : (
            <p className="text-muted-foreground">Loading…</p>
          )}
        </TabsContent>
        <TabsContent
          value="operations"
          className={cn(
            "pt-4 transition-opacity",
            operations.isPlaceholderData && "opacity-60"
          )}
        >
          {operations.data && generation.data ? (
            <OperationsTab
              data={operations.data}
              missingKeys={generation.data.missing_keys}
              onRetry={(id) => retry.mutate(id)}
              retrying={retry.isPending ? (retry.variables ?? null) : null}
            />
          ) : (
            <p className="text-muted-foreground">Loading…</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
