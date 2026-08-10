import { ClipboardList, PackageCheck, PackageSearch, Plus, Search, ShoppingCart, Warehouse } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  ERPDataTable,
  ERPFilterBar,
  ERPMetric,
  ERPPageHeader,
  ERPPanel,
  ERPStatusBadge,
} from "@/mockups/axis/erp-components"
import { inventoryStock, purchaseOrders, purchaseRequisitions } from "@/mockups/axis/mock-data"

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex min-w-40 flex-1 flex-col gap-1.5"><Label className="text-xs font-semibold text-muted-foreground">{label}</Label>{children}</div>
}

export default function PurchaseInventoryWorkspace() {
  return (
    <div>
      <ERPPageHeader
        breadcrumbs={["Purchase & Stores", "Operational Workspace"]}
        title="Purchase & Inventory"
        description="Coordinate requisitions, vendor commitments, receipts and stock shortages without losing project context."
        actions={<><Button variant="outline"><ClipboardList data-icon="inline-start" />Create RFQ</Button><Button><Plus data-icon="inline-start" />New Requisition</Button></>}
      />

      <div className="flex flex-col gap-4 p-4 lg:p-6">
        <section aria-label="Purchase and inventory summary" className="grid overflow-hidden rounded-xl border border-border bg-card sm:grid-cols-2 xl:grid-cols-5">
          <ERPMetric label="Purchase Requisitions" value="18" detail="7 require action today" status="5 RFQ pending" />
          <ERPMetric label="Open RFQs" value="11" detail="28 vendor responses received" status="4 due today" />
          <ERPMetric label="Open Purchase Orders" value="36" detail="₹1.84 Cr committed value" status="3 overdue" />
          <ERPMetric label="GRNs Today" value="9" detail="2 awaiting inspection" status="7 posted" />
          <ERPMetric label="Inventory Shortages" value="14" detail="Across 6 active projects" status="4 critical" />
        </section>

        <ERPFilterBar activeCount={2}>
          <FilterField label="Search"><div className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input aria-label="Search purchase and inventory" placeholder="PR, PO, item, vendor or project" className="pl-9" /></div></FilterField>
          <FilterField label="Project"><Select defaultValue="active"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="active">All active projects</SelectItem><SelectItem value="0148">PRJ-2026-0148</SelectItem><SelectItem value="0137">PRJ-2026-0137</SelectItem><SelectItem value="0129">PRJ-2026-0129</SelectItem></SelectGroup></SelectContent></Select></FilterField>
          <FilterField label="Buyer"><Select defaultValue="all"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All buyers</SelectItem><SelectItem value="pooja">Pooja Nair</SelectItem><SelectItem value="amit">Amit Desai</SelectItem></SelectGroup></SelectContent></Select></FilterField>
          <FilterField label="Required Before"><Input aria-label="Required before date" type="date" defaultValue="2026-08-31" /></FilterField>
          <FilterField label="Status"><Select defaultValue="attention"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="attention">Requiring attention</SelectItem><SelectItem value="all">All statuses</SelectItem><SelectItem value="overdue">Overdue</SelectItem></SelectGroup></SelectContent></Select></FilterField>
        </ERPFilterBar>

        <div className="grid min-w-0 gap-4 2xl:grid-cols-2">
          <ERPPanel title="Purchase Requisitions" description="Approved demand waiting for commercial action" icon={<ClipboardList className="size-4 text-primary" aria-hidden="true" />} action={<Button variant="ghost" size="sm">View all 18</Button>}>
            <ERPDataTable caption="Purchase requisitions" rows={purchaseRequisitions} getRowId={(row) => row.id} columns={[
              { key: "id", label: "PR No.", render: (row) => <span className="font-semibold text-primary">{row.id}</span> },
              { key: "project", label: "Project", render: (row) => row.project },
              { key: "item", label: "Item", render: (row) => row.item },
              { key: "qty", label: "Qty", render: (row) => row.qty },
              { key: "required", label: "Required", render: (row) => row.required },
              { key: "buyer", label: "Buyer", render: (row) => row.buyer },
              { key: "status", label: "Status", render: (row) => <ERPStatusBadge status={row.status} /> },
            ]} />
          </ERPPanel>

          <ERPPanel title="Purchase Orders" description="Vendor commitments and expected deliveries" icon={<ShoppingCart className="size-4 text-primary" aria-hidden="true" />} action={<Button variant="ghost" size="sm">View all 36</Button>}>
            <ERPDataTable caption="Purchase orders" rows={purchaseOrders} getRowId={(row) => row.id} columns={[
              { key: "id", label: "PO No.", render: (row) => <span className="font-semibold text-primary">{row.id}</span> },
              { key: "vendor", label: "Vendor", render: (row) => row.vendor },
              { key: "project", label: "Project", render: (row) => row.project },
              { key: "amount", label: "Amount", className: "text-right", render: (row) => row.amount },
              { key: "due", label: "Due", render: (row) => row.due },
              { key: "status", label: "Status", render: (row) => <ERPStatusBadge status={row.status} /> },
            ]} />
          </ERPPanel>

          <ERPPanel title="Inventory Shortages & Stock" description="Available, reserved and reorder position" icon={<Warehouse className="size-4 text-status-warning" aria-hidden="true" />} action={<Button variant="ghost" size="sm">Open stock ledger</Button>}>
            <ERPDataTable caption="Inventory shortages and stock" rows={inventoryStock} getRowId={(row) => row.code} columns={[
              { key: "code", label: "Item Code", render: (row) => <span className="font-semibold text-primary">{row.code}</span> },
              { key: "item", label: "Description", render: (row) => row.item },
              { key: "location", label: "Location", render: (row) => row.location },
              { key: "available", label: "Available", render: (row) => row.available },
              { key: "reserved", label: "Reserved", render: (row) => row.reserved },
              { key: "reorder", label: "Reorder", render: (row) => row.reorder },
              { key: "status", label: "Status", render: (row) => <ERPStatusBadge status={row.status} /> },
            ]} />
          </ERPPanel>

          <div className="grid gap-4 sm:grid-cols-2">
            <ERPPanel title="RFQ Response Queue" icon={<PackageSearch className="size-4 text-primary" aria-hidden="true" />}>
              <ul className="divide-y divide-border">
                <li className="px-4 py-3"><div className="flex justify-between gap-3"><div><p className="text-sm font-medium">RFQ-260188 · SS Plate</p><p className="mt-1 text-xs text-muted-foreground">3 of 5 quotes received</p></div><ERPStatusBadge status="Due today" /></div></li>
                <li className="px-4 py-3"><div className="flex justify-between gap-3"><div><p className="text-sm font-medium">RFQ-260184 · Butterfly Valve</p><p className="mt-1 text-xs text-muted-foreground">2 of 4 quotes received</p></div><ERPStatusBadge status="Quote Review" /></div></li>
                <li className="px-4 py-3"><div className="flex justify-between gap-3"><div><p className="text-sm font-medium">RFQ-260179 · PLC Panel</p><p className="mt-1 text-xs text-muted-foreground">Commercial comparison ready</p></div><ERPStatusBadge status="Approved" /></div></li>
              </ul>
            </ERPPanel>
            <ERPPanel title="Incoming GRNs" icon={<PackageCheck className="size-4 text-status-success" aria-hidden="true" />}>
              <ul className="divide-y divide-border">
                <li className="px-4 py-3"><p className="text-sm font-medium">GRN-260554 · Jindal Stainless</p><p className="mt-1 text-xs text-muted-foreground">Received 9:20 AM · Inspection pending</p></li>
                <li className="px-4 py-3"><p className="text-sm font-medium">GRN-260553 · Flowserve India</p><p className="mt-1 text-xs text-muted-foreground">Received 8:45 AM · Posted</p></li>
                <li className="px-4 py-3"><p className="text-sm font-medium">GRN-260552 · Siemens Ltd.</p><p className="mt-1 text-xs text-muted-foreground">Expected today · Gate entry created</p></li>
              </ul>
            </ERPPanel>
          </div>
        </div>
      </div>
    </div>
  )
}
