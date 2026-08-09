import { useState } from "react"
import {
  Bell,
  CircleHelp,
  ClipboardCheck,
  Factory,
  FolderKanban,
  Gauge,
  Menu,
  PackageOpen,
  Search,
  ShieldCheck,
  ShoppingCart,
  Truck,
  UserRound,
  Warehouse,
  Wrench,
  X,
} from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import HomeWorkspace from "@/mockups/axis/screens/home-workspace"
import Project360Workspace from "@/mockups/axis/screens/project-360-workspace"
import PurchaseInventoryWorkspace from "@/mockups/axis/screens/purchase-inventory-workspace"
import SalesOrdersWorkspace from "@/mockups/axis/screens/sales-orders-workspace"
import ServiceAmcWorkspace from "@/mockups/axis/screens/service-amc-workspace"

type Workspace = "home" | "sales" | "project" | "purchase" | "service"

const workspaceKeys = new Set<Workspace>(["home", "sales", "project", "purchase", "service"])

const primaryNavigation = [
  { key: "home" as const, label: "My Workspace", icon: Gauge },
  { key: "sales" as const, label: "Sales Orders", icon: ShoppingCart },
  { key: "project" as const, label: "Project 360", icon: FolderKanban },
  { key: "purchase" as const, label: "Purchase & Inventory", icon: Warehouse },
  { key: "service" as const, label: "Service & AMC", icon: Wrench },
]

const departmentNavigation = [
  { key: "project" as const, label: "Engineering", icon: Factory },
  { key: "purchase" as const, label: "Stores", icon: PackageOpen },
  { key: "project" as const, label: "Production", icon: Factory },
  { key: "project" as const, label: "Quality", icon: ShieldCheck },
  { key: "project" as const, label: "Dispatch", icon: Truck },
  { key: "home" as const, label: "Management", icon: ClipboardCheck },
]

function initialWorkspace(): Workspace {
  const requested = new URLSearchParams(window.location.search).get("view") as Workspace | null
  return requested && workspaceKeys.has(requested) ? requested : "home"
}

function WorkspaceContent({ workspace, navigate }: { workspace: Workspace; navigate: (workspace: Workspace) => void }) {
  if (workspace === "sales") return <SalesOrdersWorkspace openProject={() => navigate("project")} />
  if (workspace === "project") return <Project360Workspace />
  if (workspace === "purchase") return <PurchaseInventoryWorkspace />
  if (workspace === "service") return <ServiceAmcWorkspace />
  return <HomeWorkspace />
}

function Navigation({ workspace, navigate, close }: { workspace: Workspace; navigate: (workspace: Workspace) => void; close?: () => void }) {
  const selectWorkspace = (next: Workspace) => {
    navigate(next)
    close?.()
  }

  return (
    <div className="axis-erp-sidebar flex h-full flex-col bg-erp-sidebar text-foreground">
      <div className="flex h-16 items-center gap-3 border-b border-border px-4">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground"><Factory aria-hidden="true" /></span>
        <div className="leading-tight"><p className="text-sm font-bold tracking-wide">MONIKA</p><p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground">ENGINEERS</p></div>
        {close ? <Button aria-label="Close navigation" variant="ghost" size="icon" className="ml-auto lg:hidden" onClick={close}><X /></Button> : null}
      </div>
      <nav aria-label="ERP workspaces" className="flex flex-1 flex-col gap-5 overflow-y-auto p-3">
        <div>
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Workspaces</p>
          <ul className="flex flex-col gap-1">
            {primaryNavigation.map((item) => (
              <li key={item.label}>
                <Button variant={workspace === item.key ? "secondary" : "ghost"} className="w-full justify-start" onClick={() => selectWorkspace(item.key)}>
                  <item.icon data-icon="inline-start" />{item.label}
                </Button>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Departments</p>
          <ul className="flex flex-col gap-1">
            {departmentNavigation.map((item) => (
              <li key={item.label}>
                <Button variant="ghost" className="w-full justify-start" onClick={() => selectWorkspace(item.key)}>
                  <item.icon data-icon="inline-start" />{item.label}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </nav>
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <Avatar><AvatarFallback>NS</AvatarFallback></Avatar>
          <div className="min-w-0"><p className="truncate text-sm font-semibold">Neha Shah</p><p className="truncate text-xs text-muted-foreground">Project Manager</p></div>
        </div>
      </div>
    </div>
  )
}

export default function AxisERPMockup() {
  const [workspace, setWorkspace] = useState<Workspace>(initialWorkspace)
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)

  const navigate = (next: Workspace) => {
    setWorkspace(next)
    const url = new URL(window.location.href)
    url.pathname = "/mockups/axis"
    url.searchParams.set("view", next)
    window.history.replaceState({}, "", url)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="axis-erp min-h-svh bg-background text-foreground">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">Skip to main content</a>
      <div className="grid min-h-svh lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="sticky top-0 hidden h-svh lg:block"><Navigation workspace={workspace} navigate={navigate} /></aside>

        {mobileNavigationOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button aria-label="Close navigation" className="absolute inset-0 bg-foreground/35" onClick={() => setMobileNavigationOpen(false)} />
            <aside className="relative h-full w-[min(20rem,88vw)]"><Navigation workspace={workspace} navigate={navigate} close={() => setMobileNavigationOpen(false)} /></aside>
          </div>
        ) : null}

        <div className="min-w-0">
          <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-border bg-background/95 px-3 backdrop-blur lg:px-5">
            <Button aria-label="Open navigation" variant="outline" size="icon" className="lg:hidden" onClick={() => setMobileNavigationOpen(true)}><Menu /></Button>
            <div className="relative hidden max-w-xl flex-1 md:block">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input aria-label="Search across ERP" placeholder="Search projects, orders, POs, drawings…" className="pl-10" />
            </div>
            <Badge variant="outline" className="hidden h-7 rounded-md md:flex">UI proof of concept</Badge>
            <div className="ml-auto flex items-center gap-1">
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex"><CircleHelp data-icon="inline-start" />Help</Button>
              <Button aria-label="Notifications, 7 unread" variant="ghost" size="icon" className="relative"><Bell /><span className="absolute right-0 top-0 flex size-4 items-center justify-center rounded-full bg-status-critical text-[10px] font-bold text-white">7</span></Button>
              <Button variant="ghost" size="sm"><UserRound data-icon="inline-start" /><span className="hidden sm:inline">Neha Shah</span></Button>
            </div>
          </header>
          <main id="main-content" tabIndex={-1} className={cn("min-w-0", mobileNavigationOpen && "lg:block")}>
            <WorkspaceContent workspace={workspace} navigate={navigate} />
          </main>
        </div>
      </div>
    </div>
  )
}
