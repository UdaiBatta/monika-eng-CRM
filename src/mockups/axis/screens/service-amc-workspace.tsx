import { useState } from "react"
import {
  CalendarDays,
  Camera,
  ClipboardSignature,
  FileText,
  History,
  PackageOpen,
  Plus,
  Search,
  ShieldCheck,
  UserRound,
  Wrench,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  ERPDataTable,
  ERPDetailPanel,
  ERPFilterBar,
  ERPPageHeader,
  ERPPanel,
  ERPProcessStepper,
  ERPStatusBadge,
} from "@/mockups/axis/erp-components"
import { serviceRequests, type ServiceRequest } from "@/mockups/axis/mock-data"

const serviceSteps = ["Logged", "Assigned", "Visit Scheduled", "On Site", "Report Pending", "Closed"]

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex min-w-40 flex-1 flex-col gap-1.5"><Label className="text-xs font-semibold text-muted-foreground">{label}</Label>{children}</div>
}

function DetailSection({ icon, title, action, children }: { icon: React.ReactNode; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="border-b border-border py-4 last:border-b-0">
      <div className="flex items-center justify-between gap-3"><h3 className="flex items-center gap-2 text-sm font-semibold">{icon}{title}</h3>{action}</div>
      <div className="mt-3 text-sm">{children}</div>
    </section>
  )
}

export default function ServiceAmcWorkspace() {
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("all")
  const [selected, setSelected] = useState<ServiceRequest>(serviceRequests[0])
  const normalizedSearch = search.trim().toLowerCase()
  const rows = serviceRequests.filter((request) => {
    const matchesSearch = !normalizedSearch || [request.id, request.customer, request.asset, request.site].some((value) => value.toLowerCase().includes(normalizedSearch))
    return matchesSearch && (status === "all" || request.status === status)
  })

  return (
    <div>
      <ERPPageHeader
        breadcrumbs={["Service", "Service & AMC"]}
        title="Service & AMC"
        description="Plan visits, assign engineers and complete service records with customer sign-off."
        actions={<Button><Plus data-icon="inline-start" />New Service Request</Button>}
      />

      <div className="flex flex-col gap-4 p-4 lg:p-6">
        <ERPFilterBar activeCount={Number(Boolean(search)) + Number(status !== "all")} onReset={() => { setSearch(""); setStatus("all") }}>
          <FilterField label="Search"><div className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input aria-label="Search service requests" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Request, customer, asset or site" className="pl-9" /></div></FilterField>
          <FilterField label="Visit Date"><Input aria-label="Filter by visit date" type="date" defaultValue="2026-08-11" /></FilterField>
          <FilterField label="Engineer"><Select defaultValue="all"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All engineers</SelectItem><SelectItem value="rohan">Rohan Patil</SelectItem><SelectItem value="kiran">Kiran Jadhav</SelectItem><SelectItem value="vikas">Vikas More</SelectItem></SelectGroup></SelectContent></Select></FilterField>
          <FilterField label="Status"><Select value={status} onValueChange={setStatus}><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All statuses</SelectItem><SelectItem value="Visit Scheduled">Visit Scheduled</SelectItem><SelectItem value="On Site">On Site</SelectItem><SelectItem value="Report Pending">Report Pending</SelectItem><SelectItem value="Closed">Closed</SelectItem></SelectGroup></SelectContent></Select></FilterField>
          <FilterField label="Warranty / AMC"><Select defaultValue="all"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All coverage</SelectItem><SelectItem value="amc">AMC active</SelectItem><SelectItem value="warranty">Under warranty</SelectItem><SelectItem value="chargeable">Chargeable</SelectItem></SelectGroup></SelectContent></Select></FilterField>
        </ERPFilterBar>

        <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(24rem,0.78fr)]">
          <ERPPanel title="Service Requests" description={`${rows.length} requests shown`} icon={<Wrench className="size-4 text-primary" aria-hidden="true" />}>
            <ERPDataTable
              caption="Service requests"
              rows={rows}
              getRowId={(request) => request.id}
              selectedId={selected.id}
              onSelect={setSelected}
              columns={[
                { key: "id", label: "Request", render: (request) => <span className="font-semibold text-primary">{request.id}</span> },
                { key: "customer", label: "Customer", render: (request) => request.customer },
                { key: "asset", label: "Asset", render: (request) => request.asset },
                { key: "site", label: "Site", render: (request) => request.site },
                { key: "visit", label: "Visit", render: (request) => request.visit },
                { key: "engineer", label: "Engineer", render: (request) => request.engineer },
                { key: "priority", label: "Priority", render: (request) => <ERPStatusBadge status={request.priority} /> },
                { key: "status", label: "Status", render: (request) => <ERPStatusBadge status={request.status} /> },
              ]}
            />
          </ERPPanel>

          <ERPDetailPanel title={`${selected.id} · ${selected.customer}`} subtitle={selected.asset} status={selected.status} actions={<><Button><FileText data-icon="inline-start" />Complete Service Report</Button><Button variant="outline"><ClipboardSignature data-icon="inline-start" />Capture Customer Sign-off</Button></>}>
            <div className="overflow-x-auto border-b border-border"><ERPProcessStepper steps={serviceSteps} current={selected.status === "Closed" ? 5 : selected.status === "Report Pending" ? 4 : selected.status === "On Site" ? 3 : 2} /></div>
            <DetailSection icon={<UserRound className="size-4 text-primary" aria-hidden="true" />} title="Engineer Assignment" action={<Button variant="ghost" size="sm">Edit</Button>}>
              <dl className="grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">Engineer</dt><dd className="mt-1 font-medium">{selected.engineer}</dd></div><div><dt className="text-xs text-muted-foreground">Team</dt><dd className="mt-1 font-medium">Field Service · West</dd></div></dl>
            </DetailSection>
            <DetailSection icon={<CalendarDays className="size-4 text-primary" aria-hidden="true" />} title="Visit Schedule" action={<Button variant="ghost" size="sm">Edit</Button>}>
              <p className="font-medium">{selected.visit}</p><p className="mt-1 text-xs text-muted-foreground">Planned visit · Site contact: Sandeep Kulkarni</p>
            </DetailSection>
            <DetailSection icon={<Wrench className="size-4 text-primary" aria-hidden="true" />} title="Asset">
              <p className="font-medium">{selected.asset}</p><p className="mt-1 text-xs text-muted-foreground">{selected.site} · Process recovery system</p>
            </DetailSection>
            <DetailSection icon={<ShieldCheck className="size-4 text-status-success" aria-hidden="true" />} title="Warranty / AMC">
              <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium text-status-success">AMC Active until 31 Mar 2027</p><ERPStatusBadge status="Comprehensive" /></div>
            </DetailSection>
            <DetailSection icon={<Wrench className="size-4 text-primary" aria-hidden="true" />} title="Service Progress">
              <div className="grid gap-3 sm:grid-cols-2"><div><p className="text-xs text-muted-foreground">Current status</p><div className="mt-1"><ERPStatusBadge status={selected.status} /></div></div><div><p className="text-xs text-muted-foreground">Next step</p><p className="mt-1 font-medium">Engineer to reach site</p></div></div>
            </DetailSection>
            <DetailSection icon={<Camera className="size-4 text-primary" aria-hidden="true" />} title="Photos" action={<Button variant="outline" size="sm"><Plus data-icon="inline-start" />Add Photos</Button>}>
              <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {["Asset overview", "Nameplate", "Leak point", "Control panel"].map((photo) => <li key={photo} className="flex aspect-[4/3] items-center justify-center rounded-lg border border-border bg-muted/45 px-2 text-center text-xs text-muted-foreground"><Camera className="mr-1 size-4" aria-hidden="true" />{photo}</li>)}
              </ul>
            </DetailSection>
            <DetailSection icon={<PackageOpen className="size-4 text-primary" aria-hidden="true" />} title="Parts Used"><div className="flex justify-between gap-3"><span>Mechanical seal kit · 1 No</span><strong>₹8,450</strong></div></DetailSection>
            <DetailSection icon={<FileText className="size-4 text-status-warning" aria-hidden="true" />} title="Service Report"><ERPStatusBadge status={selected.status === "Closed" ? "Completed" : "Report Pending"} /></DetailSection>
            <DetailSection icon={<ClipboardSignature className="size-4 text-status-warning" aria-hidden="true" />} title="Customer Sign-off"><ERPStatusBadge status={selected.status === "Closed" ? "Completed" : "Pending"} /></DetailSection>
            <DetailSection icon={<History className="size-4 text-primary" aria-hidden="true" />} title="Service History"><p className="font-medium">5 previous visits</p><p className="mt-1 text-xs text-muted-foreground">Last visit: 18 Feb 2026 · Preventive maintenance</p></DetailSection>
          </ERPDetailPanel>
        </div>
      </div>
    </div>
  )
}
