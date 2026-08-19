import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, CheckCircle2, DatabaseZap } from "lucide-react"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ERPErrorState, ERPLoadingState } from "@/production/components/shared"
import { apiGet } from "@/production/lib/api"
import type { DataQualityIssue } from "@/production/lib/owner-types"

export default function OwnerDataQualityPage() {
  const query = useQuery({
    queryKey: ["owner-data-quality"],
    queryFn: () => apiGet<{ issues: DataQualityIssue[] }>("/owner/data-quality/"),
  })
  if (query.isPending) return <ERPLoadingState rows={6} />
  if (query.isError) return <ERPErrorState title="Data quality checks could not run" message={query.error.message} />
  if (!query.data.issues.length) {
    return <Empty><EmptyHeader><EmptyMedia variant="icon"><CheckCircle2 /></EmptyMedia><EmptyTitle>No known data-quality issues</EmptyTitle><EmptyDescription>The current deterministic checks found nothing requiring review. This is not a guarantee that every business record is perfect.</EmptyDescription></EmptyHeader></Empty>
  }
  return (
    <div className="flex flex-col gap-4">
      <Card size="sm">
        <CardHeader><CardTitle>Data quality review</CardTitle><CardDescription>These checks point to records that need human review. The system never merges, deletes or silently edits data here.</CardDescription></CardHeader>
      </Card>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {query.data.issues.map((issue) => (
          <Card key={issue.type} size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><DatabaseZap />{issue.message}</CardTitle>
              <CardDescription>{issue.recommended_action}</CardDescription>
              <CardAction><Badge variant={issue.severity === "problem" ? "destructive" : "outline"}>{issue.count}</Badge></CardAction>
            </CardHeader>
            <CardContent><Button variant="outline" size="sm" nativeButton={false} render={<Link to={issue.action_url} />}>Review records<ArrowUpRight data-icon="inline-end" /></Button></CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
