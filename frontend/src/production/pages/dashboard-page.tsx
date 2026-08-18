import { useQueries, useQuery } from "@tanstack/react-query"
import { Activity, ArrowRight, ClipboardCheck, FileKey2, Files, FileText, FolderKanban, Inbox, PencilRuler, ServerCog, ShoppingCart, Users } from "lucide-react"
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
  { label: "Unassigned enquiries", endpoint: "/external-enquiries/?queue=unassigned&page_size=1", permission: "crm.external_enquiry.review", icon: Inbox, href: "/app/crm/incoming-enquiries?queue=unassigned" },
  { label: "My enquiries", endpoint: "/external-enquiries/?queue=mine&page_size=1", permission: "crm.external_enquiry.review", icon: Inbox, href: "/app/crm/incoming-enquiries?queue=mine" },
  { label: "My quotations", endpoint: "/quotations/?queue=mine&page_size=1", permission: "crm.quotation.view", icon: FileText, href: "/app/crm/quotations?queue=mine" },
  { label: "My Sales Orders", endpoint: "/sales/orders/?queue=mine&page_size=1", permission: "sales.sales_order.view", icon: ShoppingCart, href: "/app/sales/orders?queue=mine" },
  { label: "Unassigned Engineering", endpoint: "/projects/?queue=unassigned&page_size=1", permission: "projects.handoff.take_ownership", icon: FolderKanban, href: "/app/engineering/work?queue=unassigned" },
  { label: "My Engineering work", endpoint: "/projects/?queue=mine&page_size=1", permission: "projects.handoff.take_ownership", icon: PencilRuler, href: "/app/engineering/work?queue=mine" },
]

const administrationPermissions = [
  "organization.employee.manage",
  "rbac.role.manage",
  "configuration.settings.manage",
  "numbering.sequence.manage",
  "documents.category.manage",
  "approvals.workflow.manage",
]

const salesJourney = [
  { title: "Review new enquiries", description: "Check website and manually captured enquiries, then assign the genuine opportunities.", href: "/app/crm/incoming-enquiries", permission: "crm.external_enquiry.review" },
  { title: "Understand the requirement", description: "Open the enquiry, confirm the customer need, and keep the next follow-up visible.", href: "/app/crm/enquiries", permission: "enquiry.enquiry.view" },
  { title: "Prepare the quotation", description: "Build, send, negotiate, and record the customer's confirmation.", href: "/app/crm/quotations", permission: "crm.quotation.view" },
  { title: "Record the Customer PO", description: "Upload the PO when it arrives and review any difference from the quotation.", href: "/app/sales/customer-pos", permission: "sales.customer_po.view" },
  { title: "Prepare the Sales Order", description: "Create the order from the quotation, check the terms, and submit it for approval.", href: "/app/sales/orders", permission: "sales.sales_order.view" },
  { title: "Send the project to Engineering", description: "Open Project 360, complete the handoff, and answer Engineering questions.", href: "/app/projects", permission: "projects.handoff.view" },
]

export default function DashboardPage() {
  const { data: user } = useCurrentUser()
  const canAdminister = administrationPermissions.some((permission) => hasPermission(user, permission))
  const canWorkEngineering = hasPermission(user, "engineering.feasibility.review")
  const isSalesWorkspace = hasPermission(user, "crm.external_enquiry.review") || hasPermission(user, "crm.quotation.view") || hasPermission(user, "sales.sales_order.view")
  const roleName = user?.roles?.[0]?.name || (isSalesWorkspace ? "Sales" : "Daily")
  const visibleSalesJourney = salesJourney.filter((step) => hasPermission(user, step.permission))
  const salesAccess = [
    { label: "Enquiries", detail: "Review, assign, update, win or close", canWork: hasPermission(user, "enquiry.enquiry.edit"), canView: hasPermission(user, "enquiry.enquiry.view") },
    { label: "Customers & follow-ups", detail: "Maintain customer details and daily follow-ups", canWork: hasPermission(user, "crm.customer.edit") && hasPermission(user, "crm.activity.edit"), canView: hasPermission(user, "crm.customer.view") },
    { label: "Quotations", detail: "Create, send, negotiate and confirm", canWork: hasPermission(user, "crm.quotation.change"), canView: hasPermission(user, "crm.quotation.view") },
    { label: "Customer POs", detail: "Record, revise, link and review differences", canWork: hasPermission(user, "sales.customer_po.create"), canView: hasPermission(user, "sales.customer_po.view") },
    { label: "Sales Orders", detail: "Prepare drafts and submit for approval", canWork: hasPermission(user, "sales.sales_order.submit"), canView: hasPermission(user, "sales.sales_order.view") },
    { label: "Projects & handoff", detail: "Track the project and send information to Engineering", canWork: hasPermission(user, "projects.handoff.submit"), canView: hasPermission(user, "projects.project.view") },
  ]
  const health = useQuery({ queryKey: ["health"], queryFn: () => apiGet<{ status: string; database: string; cache: string }>("/health/"), enabled: canAdminister })
  const visibleMetrics = metrics.filter((metric) => hasPermission(user, metric.permission))
  const metricQueries = useQueries({
    queries: visibleMetrics.map((metric) => ({
      queryKey: ["metric", metric.endpoint],
      queryFn: () => apiGet<Paginated<FoundationRecord>>(metric.endpoint),
    })),
  })

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
      <section className={canAdminister ? "grid gap-4 xl:grid-cols-[1.5fr_0.8fr]" : "grid gap-4"}>
        <Card className="overflow-hidden border-erp-sidebar/20">
          <CardHeader className="bg-erp-sidebar text-white">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Badge variant="secondary" className="mb-3">{canAdminister ? "Phase 3 order-to-project" : `${roleName} workspace`}</Badge>
                <CardTitle className="text-2xl">Good to see you, {user?.employee?.display_name || user?.first_name || "administrator"}.</CardTitle>
                <CardDescription className="mt-2 max-w-2xl text-white/60">
                  {canAdminister
                    ? "Customer orders now continue through Sales Order release, Project 360, and an accountable Sales-to-Engineering handoff."
                    : "Review new enquiries, keep customer follow-ups moving, prepare quotations, and release confirmed Sales Orders from one daily workspace."}
                </CardDescription>
              </div>
              <ServerCog aria-hidden="true" className="opacity-40" />
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-3">
            {(canAdminister
              ? [
                  ["Django API", health.data?.status === "ok" ? "Operational" : "Checking"],
                  ["PostgreSQL", health.data?.database === "ok" ? "Connected" : "Checking"],
                  ["Realtime & cache", health.data?.cache === "ok" ? "Operational" : "Checking"],
                ]
              : [
                  ["New business", "Review and claim enquiries"],
                  ["Customer response", "Keep follow-ups on time"],
                  ["Commercial work", "Quotation through Sales Order"],
                ]
            ).map(([label, value]) => (
              <div key={label} className="border-l-2 border-primary pl-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
                <p className="mt-1 font-semibold">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {canAdminister ? <Card>
          <CardHeader><CardTitle>Foundation readiness</CardTitle><CardDescription>Current delivery boundary</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div><div className="mb-2 flex justify-between text-sm"><span>Phase 1A–H</span><span>Implemented</span></div><Progress value={100} /></div>
            <div><div className="mb-2 flex justify-between text-sm"><span>Phase 2 commercial CRM</span><span>Through quotation handoff</span></div><Progress value={100} /></div>
            <div><div className="mb-2 flex justify-between text-sm"><span>Phase 3 order-to-project</span><span>Core operational flow</span></div><Progress value={100} /></div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="border p-3"><p className="font-semibold">Live scope</p><p className="text-muted-foreground">Enquiry to Engineering handoff</p></div>
              <div className="border p-3"><p className="font-semibold">Next gate</p><p className="text-muted-foreground">Detailed Engineering</p></div>
            </div>
          </CardContent>
        </Card> : null}
      </section>

      {canAdminister && health.isError ? <Alert variant="destructive"><AlertTitle>Health check failed</AlertTitle><AlertDescription>{health.error.message}</AlertDescription></Alert> : null}

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

      {isSalesWorkspace ? <section className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="border-primary/25">
          <CardHeader><CardTitle>Your daily sales flow</CardTitle><CardDescription>Follow these steps from a new enquiry to a clear Engineering handoff. Open the step that needs attention today.</CardDescription></CardHeader>
          <CardContent><ol className="grid gap-3 sm:grid-cols-2">
            {visibleSalesJourney.map((step, index) => <li key={step.title} className="flex gap-3 rounded-lg border p-4">
              <Badge className="size-7 shrink-0 justify-center rounded-full">{index + 1}</Badge>
              <div className="min-w-0 flex-1"><p className="font-semibold">{step.title}</p><p className="mt-1 text-sm leading-5 text-muted-foreground">{step.description}</p><Button className="mt-3 px-0" variant="link" render={<Link to={step.href} />} nativeButton={false}>Open this step<ArrowRight data-icon="inline-end" /></Button></div>
            </li>)}
          </ol></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Your access</CardTitle><CardDescription>This is what the current {roleName} role can do—not a technical permission list.</CardDescription></CardHeader>
          <CardContent className="flex flex-col gap-3">
            {salesAccess.map((item) => {
              const level = item.canWork ? "Work" : item.canView ? "View" : "Restricted"
              return <div key={item.label} className="flex items-start justify-between gap-3 border-b pb-3 last:border-b-0 last:pb-0"><div><p className="text-sm font-medium">{item.label}</p><p className="text-xs leading-5 text-muted-foreground">{item.detail}</p></div><Badge variant={level === "Work" ? "default" : level === "View" ? "secondary" : "outline"}>{level}</Badge></div>
            })}
            <Alert>
              <AlertTitle>Manager-controlled actions</AlertTitle>
              <AlertDescription>{hasPermission(user, "sales.sales_order.release") ? "You can release an approved Sales Order. Approval still follows the configured workflow." : "You prepare and submit the Sales Order. Approval, release, cancellation, and critical PO-difference acceptance stay with an authorized manager."}</AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </section> : null}

      {canWorkEngineering || canAdminister ? <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        {canWorkEngineering ? <Card>
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
        </Card> : null}

        {canAdminister ? <Card>
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
        </Card> : null}
      </section> : null}
    </div>
  )
}
