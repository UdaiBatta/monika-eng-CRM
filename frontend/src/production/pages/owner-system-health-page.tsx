import { useQuery } from "@tanstack/react-query"
import { CircleAlert, HeartPulse, RefreshCw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ERPErrorState, ERPLoadingState, formatDateTime } from "@/production/components/shared"
import { apiGet } from "@/production/lib/api"
import type { SystemHealth } from "@/production/lib/owner-types"

export default function OwnerSystemHealthPage() {
  const query = useQuery({
    queryKey: ["owner-system-health"],
    queryFn: () => apiGet<SystemHealth>("/owner/system-health/"),
    refetchInterval: 60_000,
  })
  if (query.isPending) return <ERPLoadingState rows={7} />
  if (query.isError) return <ERPErrorState title="System health could not be checked" message={query.error.message} />
  return (
    <div className="flex flex-col gap-4">
      <Card size="sm">
        <CardHeader>
          <CardTitle>System readiness</CardTitle>
          <CardDescription>Safe live checks only. Credentials and technical error details are never displayed.</CardDescription>
          <CardAction><Button variant="outline" size="sm" disabled={query.isFetching} onClick={() => query.refetch()}><RefreshCw data-icon="inline-start" className={query.isFetching ? "animate-spin" : ""} />Refresh</Button></CardAction>
        </CardHeader>
        <CardContent><p className="text-xs text-muted-foreground">Last checked {formatDateTime(query.data.checked_at)}</p></CardContent>
      </Card>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {query.data.services.map((service) => {
          const unavailable = service.status === "Unavailable"
          return (
            <Card key={service.name} size="sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">{unavailable ? <CircleAlert /> : <HeartPulse />}{service.name}</CardTitle>
                <CardDescription>{service.detail}</CardDescription>
                <CardAction><Badge variant={unavailable ? "destructive" : "outline"}>{service.status}</Badge></CardAction>
              </CardHeader>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
