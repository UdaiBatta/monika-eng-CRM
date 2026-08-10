import {
  AlertTriangle,
  CalendarDays,
  ClipboardCheck,
  FilePlus2,
  FolderOpen,
  PackageSearch,
  Plus,
  Send,
  Truck,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ERPActivityTimeline,
  ERPDataTable,
  ERPDocumentPanel,
  ERPEmptyState,
  ERPPageHeader,
  ERPPanel,
  ERPProcessStepper,
  ERPProgress,
  ERPStatusBadge,
} from "@/mockups/axis/erp-components"
import { documents, pendingQc, projectJobs, projectShortages, recentActivity } from "@/mockups/axis/mock-data"

const lifecycle = ["Enquiry", "Engineering", "BOM", "Procurement", "Production", "Quality", "Dispatch"]
const tabs = ["Overview", "Engineering", "BOM", "Materials", "Purchase", "Inventory", "Production", "Quality", "Dispatch", "Documents", "Costing", "History"]

export default function Project360Workspace() {
  return (
    <div>
      <ERPPageHeader
        breadcrumbs={["Projects", "Project 360", "PRJ-2026-0148"]}
        title="Project 360"
        description="Complete operational context for one customer project, from enquiry through dispatch."
        actions={<><Button variant="outline"><FolderOpen data-icon="inline-start" />Documents</Button><Button><Plus data-icon="inline-start" />Important Action</Button></>}
        meta={
          <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/35 p-3">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <strong className="text-lg text-primary">PRJ-2026-0148</strong><span className="hidden h-5 w-px bg-border sm:block" /><span className="font-semibold">Apex Process Systems</span><span className="hidden h-5 w-px bg-border sm:block" /><span>Solvent Recovery Skid</span><ERPStatusBadge status="In Production" />
            </div>
            <dl className="grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-5">
              <div><dt className="text-xs text-muted-foreground">Project Manager</dt><dd className="mt-1 font-medium">Neha Shah</dd></div>
              <div><dt className="text-xs text-muted-foreground">Sales Order</dt><dd className="mt-1 font-medium text-primary">SO-260184</dd></div>
              <div><dt className="text-xs text-muted-foreground">Customer PO</dt><dd className="mt-1 font-medium">APS/PO/4817</dd></div>
              <div><dt className="text-xs text-muted-foreground">Start Date</dt><dd className="mt-1 font-medium">12 May 2026</dd></div>
              <div><dt className="text-xs text-muted-foreground">Delivery Date</dt><dd className="mt-1 font-semibold text-status-warning-foreground">28 Aug 2026</dd></div>
            </dl>
          </div>
        }
      />

      <div className="border-b border-border bg-card">
        <div className="overflow-x-auto"><ERPProcessStepper steps={lifecycle} current={4} /></div>
      </div>

      <Tabs defaultValue="Overview" className="gap-0">
        <div className="overflow-x-auto border-b border-border bg-background px-4 lg:px-6">
          <TabsList variant="line" className="h-11 min-w-max gap-4">
            {tabs.map((tab) => <TabsTrigger key={tab} value={tab} className="px-2">{tab}</TabsTrigger>)}
          </TabsList>
        </div>
        <TabsContent value="Overview" className="m-0 p-4 lg:p-6">
          <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="flex min-w-0 flex-col gap-4">
              <div className="grid gap-4 xl:grid-cols-2">
                <ERPPanel title="Project Progress" icon={<ClipboardCheck className="size-4 text-primary" aria-hidden="true" />}>
                  <div className="flex flex-col gap-4 p-4">
                    <ERPProgress label="Overall Progress" value={68} />
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ERPProgress label="Engineering" value={100} />
                      <ERPProgress label="Procurement" value={92} />
                      <ERPProgress label="Production" value={62} />
                      <ERPProgress label="Quality" value={20} />
                    </div>
                  </div>
                </ERPPanel>
                <ERPPanel title="Current Stage" icon={<CalendarDays className="size-4 text-primary" aria-hidden="true" />}>
                  <div className="grid gap-4 p-4 sm:grid-cols-2">
                    <div><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Stage</p><p className="mt-2 text-xl font-semibold">Production</p><div className="mt-2"><ERPStatusBadge status="In Progress" /></div></div>
                    <div><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Next gate</p><p className="mt-2 font-semibold">Quality Inspection</p><p className="mt-1 text-sm text-muted-foreground">Planned for 21 Aug 2026</p></div>
                    <div className="sm:col-span-2 rounded-lg bg-muted/50 p-3"><p className="text-sm font-medium">Delivery confidence: At risk</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Four critical materials must arrive by 14 Aug to protect the committed delivery date.</p></div>
                  </div>
                </ERPPanel>
              </div>

              <ERPPanel title={`Material Shortages (${projectShortages.length})`} icon={<PackageSearch className="size-4 text-status-critical" aria-hidden="true" />}>
                <ERPDataTable
                  caption="Project material shortages"
                  rows={projectShortages}
                  getRowId={(row) => row.item}
                  columns={[
                    { key: "item", label: "Item Code", render: (row) => <span className="font-medium text-primary">{row.item}</span> },
                    { key: "description", label: "Description", render: (row) => row.description },
                    { key: "required", label: "Required", render: (row) => row.required },
                    { key: "available", label: "Available", render: (row) => row.available },
                    { key: "date", label: "Required Date", render: (row) => row.requiredDate },
                    { key: "impact", label: "Impact", render: (row) => <ERPStatusBadge status={row.impact} /> },
                  ]}
                />
              </ERPPanel>

              <div className="grid gap-4 xl:grid-cols-2">
                <ERPPanel title={`Open Jobs (${projectJobs.length})`}>
                  <ERPDataTable caption="Open production jobs" rows={projectJobs} getRowId={(row) => row.job} columns={[
                    { key: "job", label: "Job", render: (row) => <span className="font-medium text-primary">{row.job}</span> },
                    { key: "description", label: "Description", render: (row) => row.description },
                    { key: "center", label: "Work Center", render: (row) => row.workCenter },
                    { key: "due", label: "Due", render: (row) => row.due },
                    { key: "status", label: "Status", render: (row) => <ERPStatusBadge status={row.status} /> },
                  ]} />
                </ERPPanel>
                <ERPPanel title={`Pending QC (${pendingQc.length})`}>
                  <ERPDataTable caption="Pending quality checks" rows={pendingQc} getRowId={(row) => row.id} columns={[
                    { key: "id", label: "QC No.", render: (row) => <span className="font-medium text-primary">{row.id}</span> },
                    { key: "item", label: "Item / Activity", render: (row) => row.item },
                    { key: "type", label: "Type", render: (row) => row.type },
                    { key: "raised", label: "Raised", render: (row) => row.raised },
                    { key: "priority", label: "Priority", render: (row) => <ERPStatusBadge status={row.priority} /> },
                  ]} />
                </ERPPanel>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                <ERPDocumentPanel documents={documents} />
                <ERPPanel title="Recent Activity"><ERPActivityTimeline items={recentActivity} /></ERPPanel>
              </div>
            </div>

            <div className="flex min-w-0 flex-col gap-4">
              <ERPPanel title="Important Actions" icon={<AlertTriangle className="size-4 text-status-warning" aria-hidden="true" />}>
                <div className="flex flex-col gap-2 p-3">
                  <Button className="justify-start"><FilePlus2 data-icon="inline-start" />Create Production Job</Button>
                  <Button variant="outline" className="justify-start"><PackageSearch data-icon="inline-start" />Raise Purchase Indent</Button>
                  <Button variant="outline" className="justify-start"><ClipboardCheck data-icon="inline-start" />Create Inspection Plan</Button>
                  <Button variant="outline" className="justify-start"><Send data-icon="inline-start" />Raise NCR</Button>
                  <Button variant="outline" className="justify-start"><Truck data-icon="inline-start" />Schedule Dispatch</Button>
                </div>
              </ERPPanel>
              <ERPPanel title="Key Dates">
                <dl className="grid grid-cols-2 gap-4 p-4 text-sm">
                  <div><dt className="text-xs text-muted-foreground">Start Date</dt><dd className="mt-1 font-medium">12 May 2026</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Delivery Date</dt><dd className="mt-1 font-semibold text-status-warning-foreground">28 Aug 2026</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Days Elapsed</dt><dd className="mt-1 font-medium">89 days</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Days Remaining</dt><dd className="mt-1 font-semibold text-primary">19 days</dd></div>
                </dl>
              </ERPPanel>
              <ERPPanel title="Notes">
                <div className="p-4 text-sm leading-6 text-muted-foreground">Client visit scheduled on 12 Aug 2026. Hydro test for skid assembly planned on 21 Aug 2026. Customer requires pre-dispatch photo set.</div>
              </ERPPanel>
            </div>
          </div>
        </TabsContent>
        {tabs.slice(1).map((tab) => (
          <TabsContent key={tab} value={tab} className="m-0 p-4 lg:p-6">
            <ERPEmptyState title={`${tab} workspace`} description={`This representative state confirms the Project 360 navigation model. Detailed ${tab.toLowerCase()} workflows remain outside this design validation scope.`} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
