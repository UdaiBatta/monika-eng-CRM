import {
  AlertTriangle,
  ArrowRight,
  ClipboardCheck,
  FilePlus2,
  PackageSearch,
  Plus,
  RefreshCw,
  Truck,
  Wrench,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  ERPActivityTimeline,
  ERPApprovalPanel,
  ERPDataTable,
  ERPMetric,
  ERPPageHeader,
  ERPPanel,
  ERPStatusBadge,
} from "@/mockups/axis/erp-components"
import { recentActivity, workItems } from "@/mockups/axis/mock-data"

const approvals = [
  { title: "GA Drawing Rev B", owner: "PRJ-2026-0148 · Engineering", due: "11:30 AM", status: "Approval pending" },
  { title: "Purchase Order PO-260198", owner: "Jindal Stainless · Purchase", due: "1:00 PM", status: "Commercial review" },
  { title: "Dispatch clearance DC-260094", owner: "PRJ-2026-0112 · Dispatch", due: "4:00 PM", status: "QC sign-off pending" },
]

const attentionItems = [
  { title: "3 projects have delivery risk", detail: "Largest delay: PRJ-2026-0129 · 8 days", status: "Critical" },
  { title: "8 material shortages affect production", detail: "4 items required within 72 hours", status: "Material shortage" },
  { title: "5 QC activities are overdue", detail: "2 require customer witness", status: "Overdue" },
]

const quickActions = [
  { label: "Create Sales Order", icon: Plus },
  { label: "Raise Purchase Requisition", icon: FilePlus2 },
  { label: "Record Production Progress", icon: RefreshCw },
  { label: "Create Inspection Request", icon: ClipboardCheck },
  { label: "Plan Dispatch", icon: Truck },
  { label: "Log Service Visit", icon: Wrench },
]

export default function HomeWorkspace() {
  return (
    <div>
      <ERPPageHeader
        breadcrumbs={["ERP", "My Workspace"]}
        title="Good morning, Neha"
        description="What requires your attention today? Priorities are ordered by delivery and operational impact."
        actions={<Button><Plus data-icon="inline-start" />Create Task</Button>}
      />

      <div className="flex flex-col gap-4 p-4 lg:p-6">
        <section aria-label="Today at a glance" className="grid overflow-hidden rounded-xl border border-border bg-card sm:grid-cols-2 xl:grid-cols-4">
          <ERPMetric label="My Work Today" value="12" detail="5 due before 2:00 PM" status="3 urgent" />
          <ERPMetric label="Pending Approvals" value="7" detail="Oldest waiting for 2 days" status="Approval pending" />
          <ERPMetric label="Material Shortages" value="8" detail="Affecting 4 active projects" status="Critical" />
          <ERPMetric label="Upcoming Dispatches" value="5" detail="Next 7 calendar days" status="2 ready" />
        </section>

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.7fr)_minmax(21rem,0.8fr)]">
          <div className="flex min-w-0 flex-col gap-4">
            <ERPPanel
              title="My Work Today"
              description="Assigned tasks and time-sensitive follow-ups"
              icon={<ClipboardCheck className="size-4 text-primary" aria-hidden="true" />}
              action={<Button variant="ghost" size="sm">View all work<ArrowRight data-icon="inline-end" /></Button>}
            >
              <ERPDataTable
                caption="My work today"
                rows={workItems}
                getRowId={(item) => item.id}
                columns={[
                  { key: "task", label: "Task", render: (item) => <div><p className="font-medium text-foreground">{item.task}</p><p className="mt-0.5 text-xs text-muted-foreground">{item.context}</p></div> },
                  { key: "due", label: "Due", render: (item) => item.due },
                  { key: "priority", label: "Priority", render: (item) => <ERPStatusBadge status={item.priority} /> },
                  { key: "status", label: "Status", render: (item) => <ERPStatusBadge status={item.status} /> },
                ]}
              />
            </ERPPanel>

            <ERPApprovalPanel approvals={approvals} />

            <div className="grid gap-4 xl:grid-cols-2">
              <ERPPanel title="Project Delays" icon={<AlertTriangle className="size-4 text-status-critical" aria-hidden="true" />}>
                <ul className="divide-y divide-border">
                  {[
                    ["PRJ-2026-0129", "Cooling Tower Package", "8 days behind", "Critical"],
                    ["PRJ-2026-0137", "PLC Control Panel", "3 days behind", "High"],
                    ["PRJ-2026-0141", "Gas Filtration Skid", "1 day behind", "Medium"],
                  ].map(([id, name, delay, status]) => (
                    <li key={id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div><p className="text-sm font-medium text-primary">{id}</p><p className="mt-0.5 text-xs text-muted-foreground">{name}</p></div>
                      <div className="text-right"><p className="text-sm font-medium text-foreground">{delay}</p><ERPStatusBadge status={status} /></div>
                    </li>
                  ))}
                </ul>
              </ERPPanel>
              <ERPPanel title="Upcoming Dispatches" icon={<Truck className="size-4 text-primary" aria-hidden="true" />}>
                <ul className="divide-y divide-border">
                  {[
                    ["DC-260094", "Apex Process Systems", "12 Aug", "Ready to Dispatch"],
                    ["DC-260097", "Thermax Limited", "14 Aug", "Packing pending"],
                    ["DC-260101", "GAIL (India) Limited", "16 Aug", "QC sign-off pending"],
                  ].map(([id, customer, date, status]) => (
                    <li key={id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div><p className="text-sm font-medium text-primary">{id}</p><p className="mt-0.5 text-xs text-muted-foreground">{customer} · {date}</p></div>
                      <ERPStatusBadge status={status} />
                    </li>
                  ))}
                </ul>
              </ERPPanel>
            </div>
          </div>

          <div className="flex min-w-0 flex-col gap-4">
            <ERPPanel title="Items Requiring Attention" icon={<AlertTriangle className="size-4 text-status-warning" aria-hidden="true" />}>
              <ul className="divide-y divide-border">
                {attentionItems.map((item) => (
                  <li key={item.title} className="px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div><p className="text-sm font-medium text-foreground">{item.title}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p></div>
                      <ERPStatusBadge status={item.status} />
                    </div>
                  </li>
                ))}
              </ul>
            </ERPPanel>

            <ERPPanel title="Quick Actions" description="Common tasks across your workspaces">
              <div className="grid gap-2 p-3 sm:grid-cols-2 2xl:grid-cols-1">
                {quickActions.map((action) => (
                  <Button key={action.label} variant="outline" className="h-10 justify-start">
                    <action.icon data-icon="inline-start" />
                    {action.label}
                  </Button>
                ))}
              </div>
            </ERPPanel>

            <ERPPanel title="Material Shortages" icon={<PackageSearch className="size-4 text-status-critical" aria-hidden="true" />}>
              <ul className="divide-y divide-border">
                <li className="px-4 py-3"><p className="text-sm font-medium">SS 316L Plate 10 mm · 12 Nos</p><p className="mt-1 text-xs text-muted-foreground">PRJ-2026-0148 · Required 12 Aug</p></li>
                <li className="px-4 py-3"><p className="text-sm font-medium">Butterfly Valve 6 in · 3 Nos</p><p className="mt-1 text-xs text-muted-foreground">PRJ-2026-0148 · Required 18 Aug</p></li>
                <li className="px-4 py-3"><p className="text-sm font-medium">Instrumentation Cable · 170 m</p><p className="mt-1 text-xs text-muted-foreground">PRJ-2026-0137 · Required 20 Aug</p></li>
              </ul>
            </ERPPanel>

            <ERPPanel title="Service Visits" icon={<Wrench className="size-4 text-primary" aria-hidden="true" />}>
              <div className="p-4"><p className="text-sm font-medium text-foreground">2 visits scheduled today</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Rohan Patil · Apex Plant 1 at 10:30 AM<br />Kiran Jadhav · Dahej Site at 2:00 PM</p></div>
            </ERPPanel>

            <ERPPanel title="Recent Activity"><ERPActivityTimeline items={recentActivity.slice(0, 3)} /></ERPPanel>
          </div>
        </div>
      </div>
    </div>
  )
}
