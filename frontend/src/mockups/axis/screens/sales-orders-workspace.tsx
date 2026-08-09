import { useState } from "react"
import { FileText, Filter, FolderOpen, Pencil, Plus, Search, SlidersHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  ERPActivityTimeline,
  ERPDataTable,
  ERPDetailPanel,
  ERPFilterBar,
  ERPPageHeader,
  ERPStatusBadge,
} from "@/mockups/axis/erp-components"
import { recentActivity, salesOrders, type SalesOrder } from "@/mockups/axis/mock-data"

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex min-w-36 flex-1 flex-col gap-1.5"><Label className="text-xs font-semibold text-muted-foreground">{label}</Label>{children}</div>
}

export default function SalesOrdersWorkspace({ openProject }: { openProject: () => void }) {
  const [search, setSearch] = useState("")
  const [customer, setCustomer] = useState("all")
  const [status, setStatus] = useState("all")
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [selected, setSelected] = useState<SalesOrder>(salesOrders[0])

  const normalizedSearch = search.trim().toLowerCase()
  const filteredOrders = salesOrders.filter((order) => {
    const matchesSearch = !normalizedSearch || [order.id, order.customer, order.customerPo, order.project].some((value) => value.toLowerCase().includes(normalizedSearch))
    const matchesCustomer = customer === "all" || order.customer === customer
    const matchesStatus = status === "all" || order.status === status
    return matchesSearch && matchesCustomer && matchesStatus
  })
  const activeCount = Number(Boolean(search)) + Number(customer !== "all") + Number(status !== "all")

  const resetFilters = () => {
    setSearch("")
    setCustomer("all")
    setStatus("all")
  }

  return (
    <div>
      <ERPPageHeader
        breadcrumbs={["Sales", "Sales Orders"]}
        title="Sales Orders"
        description="Track customer orders, delivery commitments and project status."
        actions={<Button><Plus data-icon="inline-start" />Create Sales Order</Button>}
      />

      <div className="flex flex-col gap-4 p-4 lg:p-6">
        <ERPFilterBar activeCount={activeCount} onReset={resetFilters}>
          <FilterField label="Search">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input aria-label="Search sales orders" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Order, customer, PO or project" className="pl-9" />
            </div>
          </FilterField>
          <FilterField label="Date From"><Input aria-label="Sales order date from" type="date" defaultValue="2026-06-01" /></FilterField>
          <FilterField label="Date To"><Input aria-label="Sales order date to" type="date" defaultValue="2026-08-09" /></FilterField>
          <FilterField label="Customer">
            <Select value={customer} onValueChange={setCustomer}>
              <SelectTrigger className="w-full" aria-label="Filter by customer"><SelectValue placeholder="All customers" /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem value="all">All customers</SelectItem>
                {[...new Set(salesOrders.map((order) => order.customer))].map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}
              </SelectGroup></SelectContent>
            </Select>
          </FilterField>
          <FilterField label="Status">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-full" aria-label="Filter by status"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent><SelectGroup>
                <SelectItem value="all">All statuses</SelectItem>
                {[...new Set(salesOrders.map((order) => order.status))].map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
              </SelectGroup></SelectContent>
            </Select>
          </FilterField>
          <FilterField label="Project"><Select defaultValue="all"><SelectTrigger className="w-full" aria-label="Filter by project"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All projects</SelectItem><SelectItem value="active">Active projects</SelectItem><SelectItem value="delivery-risk">Delivery risk</SelectItem></SelectGroup></SelectContent></Select></FilterField>
          <Button variant="outline" onClick={() => setAdvancedOpen((open) => !open)} aria-expanded={advancedOpen}>
            <SlidersHorizontal data-icon="inline-start" />Advanced Filters
          </Button>
        </ERPFilterBar>

        {advancedOpen ? (
          <section aria-label="Advanced filters" className="grid gap-3 rounded-xl border border-border bg-muted/35 p-3 sm:grid-cols-2 lg:grid-cols-4">
            <FilterField label="Delivery Risk"><Select defaultValue="all"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All delivery states</SelectItem><SelectItem value="at-risk">At risk</SelectItem><SelectItem value="overdue">Overdue</SelectItem></SelectGroup></SelectContent></Select></FilterField>
            <FilterField label="Salesperson"><Select defaultValue="all"><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">All salespeople</SelectItem><SelectItem value="neha">Neha Shah</SelectItem><SelectItem value="arjun">Arjun Mehta</SelectItem><SelectItem value="vikram">Vikram Iyer</SelectItem></SelectGroup></SelectContent></Select></FilterField>
            <FilterField label="Minimum Amount"><Input inputMode="numeric" placeholder="₹ 0" /></FilterField>
            <FilterField label="Customer PO"><Input placeholder="Enter PO number" /></FilterField>
          </section>
        ) : null}

        <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_22rem]">
          <section className="min-w-0 overflow-hidden rounded-xl border border-border bg-card">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
              <div><h2 className="text-sm font-semibold">Sales order register</h2><p className="mt-0.5 text-xs text-muted-foreground">{filteredOrders.length} of {salesOrders.length} orders shown</p></div>
              <div className="flex items-center gap-2"><Button variant="outline" size="sm"><Filter data-icon="inline-start" />Columns</Button><Button variant="outline" size="sm">Export</Button></div>
            </div>
            <ERPDataTable
              caption="Sales orders"
              rows={filteredOrders}
              getRowId={(order) => order.id}
              selectedId={selected.id}
              onSelect={setSelected}
              columns={[
                { key: "id", label: "Sales Order", render: (order) => <span className="font-semibold text-primary">{order.id}</span> },
                { key: "date", label: "Date", render: (order) => order.date },
                { key: "customer", label: "Customer", render: (order) => order.customer },
                { key: "po", label: "Customer PO", render: (order) => order.customerPo },
                { key: "project", label: "Project", render: (order) => order.project },
                { key: "amount", label: "Amount", className: "text-right", render: (order) => order.amount },
                { key: "delivery", label: "Delivery Date", render: (order) => order.deliveryDate },
                { key: "salesperson", label: "Salesperson", render: (order) => order.salesperson },
                { key: "status", label: "Status", render: (order) => <ERPStatusBadge status={order.status} /> },
              ]}
            />
            <div className="flex flex-col gap-3 border-t border-border px-4 py-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <span>Showing {filteredOrders.length} records</span>
              <div className="flex items-center gap-2"><Button variant="outline" size="sm" disabled>Previous</Button><span className="rounded-md bg-primary px-3 py-1.5 font-semibold text-primary-foreground">1</span><Button variant="outline" size="sm" disabled>Next</Button></div>
            </div>
          </section>

          <ERPDetailPanel
            title={selected.id}
            subtitle={selected.customer}
            status={selected.status}
            actions={<><Button onClick={openProject}><FolderOpen data-icon="inline-start" />Open Project 360</Button><Button variant="outline"><FileText data-icon="inline-start" />View Documents</Button><Button variant="outline"><Pencil data-icon="inline-start" />Edit Order</Button></>}
          >
            <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
              <div className="col-span-2"><dt className="text-xs text-muted-foreground">Project</dt><dd className="mt-1 font-semibold text-primary">{selected.project}</dd></div>
              <div className="col-span-2"><dt className="text-xs text-muted-foreground">Customer PO</dt><dd className="mt-1 font-medium">{selected.customerPo}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Amount</dt><dd className="mt-1 font-semibold">{selected.amount}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Delivery Date</dt><dd className="mt-1 font-semibold">{selected.deliveryDate}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Salesperson</dt><dd className="mt-1 font-medium">{selected.salesperson}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Current Stage</dt><dd className="mt-1 font-medium">{selected.stage}</dd></div>
            </dl>
            <div className="my-5 border-t border-border" />
            <div><div className="mb-2 flex items-center justify-between text-sm"><span className="font-medium">Project progress</span><strong>{selected.progress}%</strong></div><Progress value={selected.progress} className="h-2" /></div>
            <div className="my-5 border-t border-border" />
            <h3 className="text-sm font-semibold">Recent activity</h3>
            <ERPActivityTimeline items={recentActivity.slice(0, 3)} />
          </ERPDetailPanel>
        </div>
      </div>
    </div>
  )
}
