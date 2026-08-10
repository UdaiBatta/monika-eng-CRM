import { useQueries } from "@tanstack/react-query"
import { ArrowRight, CheckCircle2, Clock3, Send } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { apiGet } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { ApprovalRequest, Paginated } from "@/production/lib/types"
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPPermissionState, ERPStatusBadge, formatDateTime } from "@/production/components/shared"

const buckets = [
  { key: "needs-action", label: "Needs my action", icon: Clock3, empty: "Nothing needs your approval right now." },
  { key: "submitted", label: "Submitted by me", icon: Send, empty: "You have not submitted an approval request yet." },
  { key: "completed", label: "Completed", icon: CheckCircle2, empty: "No completed approval decisions are available." },
] as const

export function ERPApprovalList({ items, onOpen }: { items: ApprovalRequest[]; onOpen: (item: ApprovalRequest) => void }) {
  return <div className="divide-y rounded-lg border">{items.map((item) => <button key={item.id} type="button" onClick={() => onOpen(item)} className="grid w-full gap-3 bg-card p-4 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring md:grid-cols-[1.2fr_0.9fr_0.8fr_auto] md:items-center"><div><p className="font-semibold">{item.entity_reference}</p><p className="mt-1 text-xs text-muted-foreground">{item.entity_type.replaceAll("_", " ")} · {item.workflow_name}</p></div><div><p className="text-xs text-muted-foreground">Requested by</p><p className="text-sm">{item.requested_by_name}</p></div><div><p className="text-xs text-muted-foreground">{item.current_step_name ? "Current step" : "Completed"}</p><p className="text-sm">{item.current_step_name || formatDateTime(item.completed_at)}</p></div><div className="flex items-center justify-between gap-3 md:justify-end"><ERPStatusBadge value={item.status} label={item.status_label} /><ArrowRight className="text-muted-foreground" /></div></button>)}</div>
}

export default function ApprovalsPage() {
  const { data: user } = useCurrentUser()
  const navigate = useNavigate()
  const canView = hasPermission(user, "approvals.request.view")
  const queries = useQueries({
    queries: buckets.map((bucket) => ({
      queryKey: ["approvals", bucket.key],
      queryFn: () => apiGet<Paginated<ApprovalRequest>>(`/approvals/requests/?bucket=${bucket.key}`),
      enabled: canView,
    })),
  })
  if (!canView) return <ERPPermissionState />
  const attention = queries[0].data?.pagination.count ?? 0
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <ERPPageHeader eyebrow="Shared services" title="My approvals" description="Review assigned work, follow requests you submitted, and keep a permanent decision history without navigating through administration." />
      <section className="grid gap-3 sm:grid-cols-3"><Card className="border-amber-500/30 bg-amber-500/5"><CardContent className="flex items-center justify-between p-4"><div><p className="text-xs uppercase tracking-wider text-muted-foreground">Needs your approval</p><p className="mt-1 text-2xl font-semibold">{attention}</p></div><Clock3 className="text-amber-700" /></CardContent></Card><Card><CardContent className="flex items-center justify-between p-4"><div><p className="text-xs uppercase tracking-wider text-muted-foreground">Submitted by you</p><p className="mt-1 text-2xl font-semibold">{queries[1].data?.pagination.count ?? "—"}</p></div><Send className="text-primary" /></CardContent></Card><Card><CardContent className="flex items-center justify-between p-4"><div><p className="text-xs uppercase tracking-wider text-muted-foreground">Completed</p><p className="mt-1 text-2xl font-semibold">{queries[2].data?.pagination.count ?? "—"}</p></div><CheckCircle2 className="text-emerald-700" /></CardContent></Card></section>
      <Tabs defaultValue="needs-action">
        <TabsList className="h-auto w-full justify-start overflow-x-auto bg-transparent p-0" variant="line">{buckets.map((bucket, index) => { const Icon = bucket.icon; return <TabsTrigger key={bucket.key} value={bucket.key} className="min-h-10 flex-none px-3"><Icon />{bucket.label}{queries[index].data ? <Badge variant="secondary">{queries[index].data?.pagination.count}</Badge> : null}</TabsTrigger> })}</TabsList>
        {buckets.map((bucket, index) => <TabsContent key={bucket.key} value={bucket.key} className="pt-4">{queries[index].isPending ? <ERPLoadingState /> : queries[index].isError ? <ERPErrorState message={queries[index].error?.message ?? "Could not load approvals."} /> : !queries[index].data?.results.length ? <ERPEmptyState title={bucket.label === "Needs my action" ? "You are all caught up" : `No ${bucket.label.toLowerCase()}`} description={bucket.empty} /> : <ERPApprovalList items={queries[index].data!.results} onOpen={(item) => navigate(`/app/approvals/${item.id}`)} />}</TabsContent>)}
      </Tabs>
      <p className="text-xs text-muted-foreground">Approval assignments are resolved from active company configuration. No default Monika Engineers approvers are assumed.</p>
    </div>
  )
}
