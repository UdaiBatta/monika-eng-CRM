import type { LucideIcon } from "lucide-react"
import {
  Activity,
  Building2,
  Database,
  HeartPulse,
  ListChecks,
  Search,
  Settings2,
  Users,
} from "lucide-react"
import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { ERPErrorState, ERPLoadingState, formatDateTime } from "@/production/components/shared"
import { apiGet } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { OwnerOverview } from "@/production/lib/owner-types"

type ControlLink = {
  label: string
  description: string
  to: string
  permission: string
}

type ControlGroup = {
  title: string
  description: string
  icon: LucideIcon
  links: ControlLink[]
}

const controlGroups: ControlGroup[] = [
  {
    title: "People & access",
    description: "Employees, login accounts, roles and individual access exceptions.",
    icon: Users,
    links: [
      { label: "Employees", description: "Employment and organization records", to: "/app/employees", permission: "organization.employee.view" },
      { label: "User accounts", description: "Login access and account state", to: "/app/owner/people", permission: "accounts.user.view" },
      { label: "Roles & permissions", description: "Job-based access with plain-language groups", to: "/app/access/roles", permission: "rbac.role.view" },
      { label: "Access check", description: "Explain why somebody can or cannot act", to: "/app/owner/access", permission: "system.access_explanation.view" },
    ],
  },
  {
    title: "Organization",
    description: "The companies, teams and physical locations used by every module.",
    icon: Building2,
    links: [
      { label: "Companies", description: "Legal entities and business identity", to: "/app/organization/companies", permission: "organization.company.view" },
      { label: "Branches", description: "Office and workshop locations", to: "/app/organization/branches", permission: "organization.branch.view" },
      { label: "Departments", description: "Teams and reporting structure", to: "/app/organization/departments", permission: "organization.department.view" },
      { label: "Warehouses", description: "Stores and workshop responsibility", to: "/app/organization/warehouses", permission: "organization.warehouse.view" },
    ],
  },
  {
    title: "Business rules",
    description: "Controlled settings that affect future transactions, never historical documents.",
    icon: Settings2,
    links: [
      { label: "Feature controls", description: "Enable implemented capabilities only", to: "/app/owner/features", permission: "configuration.feature_flag.view" },
      { label: "Numbering", description: "Preview future document numbers", to: "/app/settings/numbering", permission: "numbering.sequence.view" },
      { label: "Approval rules", description: "Versioned business approvals", to: "/app/settings/approval-workflows", permission: "approvals.workflow.view" },
      { label: "Common lists", description: "Currencies, taxes and terms", to: "/app/settings/masters", permission: "masters.view" },
    ],
  },
  {
    title: "Operations",
    description: "See ownership gaps and move open work when somebody is unavailable.",
    icon: ListChecks,
    links: [
      { label: "Work assignment", description: "Open, unassigned and inactive-owner work", to: "/app/owner/work", permission: "system.owner_control.view" },
      { label: "Pending approvals", description: "Requests waiting for a decision", to: "/app/approvals", permission: "approvals.request.view" },
      { label: "Incoming enquiries", description: "New requests waiting for Sales", to: "/app/crm/incoming-enquiries", permission: "crm.external_enquiry.view" },
      { label: "Projects", description: "Sales and Workshop responsibility", to: "/app/projects", permission: "projects.project.view" },
    ],
  },
  {
    title: "Data & governance",
    description: "Imports, data checks and an immutable record of important changes.",
    icon: Database,
    links: [
      { label: "Data quality", description: "Review issues; nothing is silently changed", to: "/app/owner/data-quality", permission: "system.data_quality.view" },
      { label: "Import previous records", description: "Use Excel or CSV on supported registers", to: "/app/organization/companies", permission: "organization.company.manage" },
      { label: "Activity history", description: "Who changed what and when", to: "/app/activity-history", permission: "audit.event.view" },
      { label: "Documents", description: "Controlled versions and archive", to: "/app/documents", permission: "documents.document.view" },
    ],
  },
  {
    title: "System readiness",
    description: "Safe operational status without exposing credentials or technical secrets.",
    icon: HeartPulse,
    links: [
      { label: "System health", description: "Database, realtime, jobs and storage", to: "/app/owner/system-health", permission: "system.system_health.view" },
      { label: "Website connection", description: "Quotation-request intake status", to: "/app/owner/system-health", permission: "system.system_health.view" },
      { label: "Notification settings", description: "Your own operational alerts", to: "/app/settings/notifications", permission: "notifications.notification.manage_preferences" },
      { label: "Permission catalogue", description: "Reference for stable business actions", to: "/app/access/permissions", permission: "rbac.permission.view" },
    ],
  },
]

export default function OwnerControlPage() {
  const { data: user } = useCurrentUser()
  const [search, setSearch] = useState("")
  const query = useQuery({ queryKey: ["owner"], queryFn: () => apiGet<OwnerOverview>("/owner/") })
  const groups = useMemo(() => {
    const term = search.trim().toLowerCase()
    return controlGroups
      .map((group) => ({
        ...group,
        links: group.links.filter(
          (link) =>
            hasPermission(user, link.permission)
            && (!term || `${group.title} ${link.label} ${link.description}`.toLowerCase().includes(term)),
        ),
      }))
      .filter((group) => group.links.length)
  }, [search, user])

  if (query.isPending) return <ERPLoadingState rows={7} />
  if (query.isError) return <ERPErrorState title="Owner Control could not load" message={query.error.message} />
  const overview = query.data

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 md:grid-cols-3">
        <Card size="sm">
          <CardHeader><CardTitle>People ready</CardTitle><CardDescription>Active employee and login records</CardDescription></CardHeader>
          <CardContent><p className="text-2xl font-semibold">{overview.people.active_employees}</p><p className="text-xs text-muted-foreground">{overview.people.active_accounts} active accounts · {overview.people.roles} roles</p></CardContent>
        </Card>
        <Card size="sm">
          <CardHeader><CardTitle>Work needing ownership</CardTitle><CardDescription>Open work with nobody assigned</CardDescription><CardAction><Badge variant={overview.work.unassigned ? "destructive" : "secondary"}>{overview.work.unassigned}</Badge></CardAction></CardHeader>
          <CardContent><Button variant="outline" size="sm" nativeButton={false} render={<Link to="/app/owner/work?queue=unassigned" />}><ListChecks data-icon="inline-start" />Review work</Button></CardContent>
        </Card>
        <Card size="sm">
          <CardHeader><CardTitle>Needs attention</CardTitle><CardDescription>Data issues and pending approvals</CardDescription><CardAction><Badge variant={overview.attention.data_quality ? "destructive" : "secondary"}>{overview.attention.data_quality + overview.attention.pending_approvals}</Badge></CardAction></CardHeader>
          <CardContent><p className="text-xs text-muted-foreground">{overview.attention.data_quality} data checks · {overview.attention.pending_approvals} approvals</p></CardContent>
        </Card>
      </div>

      <Card size="sm">
        <CardHeader><CardTitle>Find a control</CardTitle><CardDescription>Search in business language, such as Rahul, numbering, warehouse, role or Audit.</CardDescription></CardHeader>
        <CardContent><div className="relative max-w-xl"><Search className="pointer-events-none absolute left-3 top-2.5 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search Owner Control…" className="pl-9" /></div></CardContent>
      </Card>

      <div className="grid items-start gap-4 xl:grid-cols-2">
        {groups.map((group) => {
          const Icon = group.icon
          return (
            <Card key={group.title} size="sm">
              <CardHeader><CardTitle className="flex items-center gap-2"><Icon />{group.title}</CardTitle><CardDescription>{group.description}</CardDescription></CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2">
                {group.links.map((link) => (
                  <Button key={`${group.title}-${link.label}`} variant="ghost" nativeButton={false} render={<Link to={link.to} />} className="h-auto justify-start py-3 text-left">
                    <span className="flex min-w-0 flex-col items-start"><span>{link.label}</span><span className="whitespace-normal text-xs font-normal text-muted-foreground">{link.description}</span></span>
                  </Button>
                ))}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card size="sm">
        <CardHeader><CardTitle className="flex items-center gap-2"><Activity />Recent important activity</CardTitle><CardDescription>Business and administration events, not every page view.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {overview.recent_admin_activity.length ? overview.recent_admin_activity.map((event) => (
            <div key={event.id} className="flex flex-col gap-1 border-b pb-3 last:border-b-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
              <div><p className="text-sm font-medium">{event.summary}</p><p className="text-xs text-muted-foreground">{event.actor}</p></div>
              <p className="text-xs text-muted-foreground">{formatDateTime(event.occurred_at)}</p>
            </div>
          )) : <p className="text-sm text-muted-foreground">No important activity has been recorded yet.</p>}
        </CardContent>
      </Card>
    </div>
  )
}
