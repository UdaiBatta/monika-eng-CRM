import { useQueries, useQuery } from "@tanstack/react-query"
import { Activity, ArrowRight, ClipboardCheck, FileKey2, Files, FileText, Inbox, PencilRuler, ServerCog, Users } from "lucide-react"
import { Link } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { apiGet } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { FoundationRecord, Paginated } from "@/production/lib/types"

const metrics = [
  { label: "Employees", endpoint: "/employees/?page_size=1", permission: "organization.employee.view", icon: Users, href: "/app/employees" },
  { label: "Documents", endpoint: "/documents/?page_size=1", permission: "documents.document.view", icon: Files, href: "/app/documents" },
  { label: "Needs my approval", endpoint: "/approvals/requests/?bucket=needs-action&page_size=1", permission: "approvals.request.view", icon: ClipboardCheck, href: "/app/approvals" },
  { label: "Recorded activity", endpoint: "/audit/events/?page_size=1", permission: "audit.event.view", icon: Activity, href: "/app/activity-history" },
  { label: "Unassigned enquiries", endpoint: "/external-enquiries/?queue=unassigned&page_size=1", permission: "crm.external_enquiry.review", icon: Inbox, href: "/app/crm/incoming-enquiries" },
  { label: "My quotations", endpoint: "/quotations/?queue=mine&page_size=1", permission: "crm.quotation.view", icon: FileText, href: "/app/crm/quotations" },
]

export default function DashboardPage() {
  const { data: user } = useCurrentUser()
  const health = useQuery({ queryKey: ["health"], queryFn: () => apiGet<{ status: string; database: string; cache: string }>("/health/") })
  const visibleMetrics = metrics.filter((metric) => hasPermission(user, metric.permission))
  const metricQueries = useQueries({
    queries: visibleMetrics.map((metric) => ({
      queryKey: ["metric", metric.endpoint],
      queryFn: () => apiGet<Paginated<FoundationRecord>>(metric.endpoint),
    })),
  })

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
      <section className="grid gap-4 xl:grid-cols-[1.5fr_0.8fr]">
        <Card className="overflow-hidden border-erp-sidebar/20">
          <CardHeader className="bg-erp-sidebar text-white">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Badge variant="secondary" className="mb-3">Phase 2 commercial CRM</Badge>
                <CardTitle className="text-2xl">Good to see you, {user?.employee?.display_name || user?.first_name || "administrator"}.</CardTitle>
                <CardDescription className="mt-2 max-w-2xl text-white/60">
                  Incoming enquiries, customer and enquiry workspaces, engineering, estimates, quotations, and shared enterprise controls are connected to live services.
                </CardDescription>
              </div>
              <ServerCog aria-hidden="true" className="opacity-40" />
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-3">
            {[
              ["Django API", health.data?.status === "ok" ? "Operational" : "Checking"],
              ["PostgreSQL", health.data?.database === "ok" ? "Connected" : "Checking"],
              ["Realtime & cache", health.data?.cache === "ok" ? "Operational" : "Checking"],
            ].map(([label, value]) => (
              <div key={label} className="border-l-2 border-primary pl-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
                <p className="mt-1 font-semibold">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Foundation readiness</CardTitle><CardDescription>Current delivery boundary</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div><div className="mb-2 flex justify-between text-sm"><span>Phase 1A–H</span><span>Implemented</span></div><Progress value={100} /></div>
            <div><div className="mb-2 flex justify-between text-sm"><span>Phase 2 commercial CRM</span><span>Through quotation handoff</span></div><Progress value={100} /></div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="border p-3"><p className="font-semibold">Live scope</p><p className="text-muted-foreground">Enquiry to quotation handoff</p></div>
              <div className="border p-3"><p className="font-semibold">Next gate</p><p className="text-muted-foreground">Sales Order and operations</p></div>
            </div>
          </CardContent>
        </Card>
      </section>

      {health.isError ? <Alert variant="destructive"><AlertTitle>Health check failed</AlertTitle><AlertDescription>{health.error.message}</AlertDescription></Alert> : null}

      <section aria-labelledby="foundation-metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="foundation-metrics" className="sr-only">Foundation metrics</h2>
        {visibleMetrics.map((metric, index) => {
          const Icon = metric.icon
          const query = metricQueries[index]
          return (
            <Card key={metric.label}>
              <CardHeader className="flex-row items-start justify-between">
                <div><CardDescription>{metric.label}</CardDescription><CardTitle className="mt-2 text-3xl">{query.data?.pagination.count ?? (query.isPending ? "—" : 0)}</CardTitle></div>
                <Icon aria-hidden="true" className="text-primary" />
              </CardHeader>
              <CardContent>
                {query.isPending ? <Skeleton className="h-8 w-full" /> : (
                  <Button variant="ghost" render={<Link to={metric.href} />} nativeButton={false} className="w-full justify-between">
                    Open register<ArrowRight data-icon="inline-end" />
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </section>

      {hasPermission(user, "crm.external_enquiry.review") || hasPermission(user, "crm.quotation.create") ? (
        <Card className="border-primary/25">
          <CardHeader><CardTitle>Commercial quick actions</CardTitle><CardDescription>Start from the real business event; each path enters the controlled CRM workflow.</CardDescription></CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {hasPermission(user, "crm.external_enquiry.review") ? <Button render={<Link to="/app/crm/incoming-enquiries" />} nativeButton={false}><Inbox data-icon="inline-start" />Review or capture enquiry</Button> : null}
            {hasPermission(user, "crm.quotation.create") ? <Button variant="outline" render={<Link to="/app/crm/quotations" />} nativeButton={false}><FileText data-icon="inline-start" />Create quotation</Button> : null}
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div><CardTitle>Engineering canvas</CardTitle><CardDescription>Drawing and BOM experience direction</CardDescription></div>
              <PencilRuler aria-hidden="true" className="text-primary" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid min-h-56 place-items-center border bg-muted/30 p-8 text-center">
              <div className="max-w-lg">
                <PencilRuler aria-hidden="true" className="mx-auto mb-4 text-primary" />
                <h3 className="font-semibold">Drawing intelligence stays central to the product vision.</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Controlled drawing files can now be uploaded, versioned, linked, approved, and audited. The rich CAD/BOM canvas from Project 360 remains a later Engineering phase and is not falsely simulated here.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Access posture</CardTitle><CardDescription>What this session can administer</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-3">
            {[
              ["Employee register", hasPermission(user, "organization.employee.manage")],
              ["Role and scope design", hasPermission(user, "rbac.role.manage")],
              ["Company configuration", hasPermission(user, "configuration.settings.manage")],
              ["Document numbering", hasPermission(user, "numbering.sequence.manage")],
              ["Document categories", hasPermission(user, "documents.category.manage")],
              ["Approval workflows", hasPermission(user, "approvals.workflow.manage")],
            ].map(([label, allowed]) => (
              <div key={String(label)} className="flex items-center justify-between border-b pb-3 text-sm">
                <span>{String(label)}</span><Badge variant={allowed ? "default" : "outline"}>{allowed ? "Manage" : "View only"}</Badge>
              </div>
            ))}
            <Button variant="outline" render={<Link to="/app/access/roles" />} nativeButton={false}><FileKey2 data-icon="inline-start" />Review access model</Button>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
