import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Activity, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiGet } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { AuditEvent, Paginated } from "@/production/lib/types"
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPPermissionState, ERPStatusBadge, formatDateTime } from "@/production/components/shared"

function displayChange(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not set"
  if (typeof value === "object") return Array.isArray(value) ? value.join(", ") : "Structured information"
  return String(value).replaceAll("_", " ")
}

export function ERPAuditChangeView({ changes }: { changes: AuditEvent["changes"] }) {
  const entries = Object.entries(changes)
  if (!entries.length) return <p className="text-sm text-muted-foreground">No field-by-field changes were recorded for this action.</p>
  return <div className="space-y-3">{entries.map(([field, change]) => <div key={field} className="rounded-lg border p-3"><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{field.replaceAll("_", " ")}</p><div className="grid gap-2 sm:grid-cols-2"><div className="rounded-md bg-muted/50 p-2"><p className="text-[11px] uppercase text-muted-foreground">Before</p><p className="mt-1 text-sm">{displayChange(change.old)}</p></div><div className="rounded-md bg-primary/5 p-2"><p className="text-[11px] uppercase text-muted-foreground">After</p><p className="mt-1 text-sm">{displayChange(change.new)}</p></div></div></div>)}</div>
}

export default function ActivityHistoryPage() {
  const { data: user } = useCurrentUser()
  const canView = hasPermission(user, "audit.event.view")
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [action, setAction] = useState("")
  const [area, setArea] = useState("")
  const [selected, setSelected] = useState<AuditEvent | null>(null)
  const query = useQuery({
    queryKey: ["audit-events", search, action, area],
    queryFn: () => {
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      if (action) params.set("action", action)
      if (area) params.set("module", area)
      return apiGet<Paginated<AuditEvent>>(`/audit/events/?${params}`)
    },
    enabled: canView,
  })
  if (!canView) return <ERPPermissionState />
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <ERPPageHeader eyebrow="Governance" title="Activity history" description="A permanent, read-only record of meaningful business and security actions. Technical request details stay out of the everyday view." />
      <Card>
        <form className="grid gap-3 border-b p-4 md:grid-cols-[1fr_180px_180px_auto]" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput) }}>
          <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input aria-label="Search activity history" className="pl-9" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search employee, record or description" /></div>
          <NativeSelect aria-label="Filter by action" className="w-full" value={action} onChange={(event) => setAction(event.target.value)}><NativeSelectOption value="">All actions</NativeSelectOption>{["CREATE", "UPDATE", "UPLOAD", "DOWNLOAD", "SUBMIT", "APPROVE", "REJECT", "ARCHIVE", "RESTORE", "LOGIN"].map((item) => <NativeSelectOption key={item} value={item}>{item.replaceAll("_", " ")}</NativeSelectOption>)}</NativeSelect>
          <NativeSelect aria-label="Filter by area" className="w-full" value={area} onChange={(event) => setArea(event.target.value)}><NativeSelectOption value="">All areas</NativeSelectOption>{["accounts", "organization", "documents", "approvals", "rbac", "configuration"].map((item) => <NativeSelectOption key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</NativeSelectOption>)}</NativeSelect>
          <Button variant="outline" type="submit">Search</Button>
        </form>
        <CardContent className="p-4">
          {query.isPending ? <ERPLoadingState /> : query.isError ? <ERPErrorState message={query.error.message} /> : !query.data.results.length ? <ERPEmptyState title="No activity found" description="Adjust the search or filters to find a recorded action." /> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Date & time</TableHead><TableHead>Employee / user</TableHead><TableHead>Action</TableHead><TableHead>Area</TableHead><TableHead>Record</TableHead><TableHead>Description</TableHead><TableHead /></TableRow></TableHeader><TableBody>{query.data.results.map((event) => <TableRow key={event.id}><TableCell className="whitespace-nowrap">{formatDateTime(event.occurred_at)}</TableCell><TableCell>{event.actor_name}</TableCell><TableCell><ERPStatusBadge value={event.action} label={event.action_label} /></TableCell><TableCell className="capitalize">{event.module}</TableCell><TableCell>{event.entity_reference || event.entity_type.replaceAll("_", " ")}</TableCell><TableCell className="max-w-md">{event.summary}</TableCell><TableCell><Button variant="ghost" size="sm" onClick={() => setSelected(event)}>View</Button></TableCell></TableRow>)}</TableBody></Table></div>}
        </CardContent>
      </Card>
      <Sheet open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null) }}>
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader><SheetTitle className="flex items-center gap-2"><Activity className="text-primary" />What happened</SheetTitle><SheetDescription>A readable view of this permanent activity record.</SheetDescription></SheetHeader>
          {selected ? <div className="mt-6 space-y-6"><div className="rounded-lg border bg-muted/20 p-4"><p className="font-semibold">{selected.summary}</p><div className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div><p className="text-xs text-muted-foreground">Who</p><p>{selected.actor_name}</p></div><div><p className="text-xs text-muted-foreground">When</p><p>{formatDateTime(selected.occurred_at)}</p></div><div><p className="text-xs text-muted-foreground">Record</p><p>{selected.entity_reference || selected.entity_type}</p></div><div><p className="text-xs text-muted-foreground">Area</p><p className="capitalize">{selected.module}</p></div></div></div><section><h3 className="mb-3 font-semibold">Changes</h3><ERPAuditChangeView changes={selected.changes} /></section></div> : null}
        </SheetContent>
      </Sheet>
    </div>
  )
}
