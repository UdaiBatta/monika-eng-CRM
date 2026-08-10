import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Activity, BadgeCheck, Bell, Building2, ChevronRight, ClipboardCheck, Database,
  FileKey2, Files, Gauge, GitBranch, Layers3, LogOut, Menu, Network, Settings2,
  ShieldCheck, Users, Warehouse,
} from "lucide-react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import ERPNotificationBell from "@/production/components/notification-center"
import { apiPost } from "@/production/lib/api"
import { currentUserQueryKey, hasPermission, useCurrentUser } from "@/production/lib/auth"

type NavItem = {
  label: string
  to: string
  icon: typeof Gauge
  permission?: string
}

const navigation: Array<{ label: string; items: NavItem[] }> = [
  { label: "Workspace", items: [
    { label: "Workspace overview", to: "/app", icon: Gauge },
    { label: "Employees", to: "/app/employees", icon: Users, permission: "organization.employee.view" },
    { label: "Documents", to: "/app/documents", icon: Files, permission: "documents.document.view" },
    { label: "My approvals", to: "/app/approvals", icon: ClipboardCheck, permission: "approvals.request.view" },
    { label: "Activity history", to: "/app/activity-history", icon: Activity, permission: "audit.event.view" },
  ] },
  { label: "Organization", items: [
    { label: "Companies", to: "/app/organization/companies", icon: Building2, permission: "organization.company.view" },
    { label: "Branches", to: "/app/organization/branches", icon: Network, permission: "organization.branch.view" },
    { label: "Departments", to: "/app/organization/departments", icon: Layers3, permission: "organization.department.view" },
    { label: "Warehouses", to: "/app/organization/warehouses", icon: Warehouse, permission: "organization.warehouse.view" },
  ] },
  { label: "Access control", items: [
    { label: "Roles", to: "/app/access/roles", icon: ShieldCheck, permission: "rbac.role.view" },
    { label: "Permissions", to: "/app/access/permissions", icon: FileKey2, permission: "rbac.permission.view" },
    { label: "Assignments", to: "/app/access/assignments", icon: BadgeCheck, permission: "rbac.assignment.view" },
  ] },
  { label: "Configuration", items: [
    { label: "Company settings", to: "/app/settings/company", icon: Settings2, permission: "configuration.settings.view" },
    { label: "Numbering", to: "/app/settings/numbering", icon: Database, permission: "numbering.sequence.view" },
    { label: "Foundation masters", to: "/app/settings/masters", icon: Layers3, permission: "masters.view" },
    { label: "Document categories", to: "/app/settings/document-categories", icon: Files, permission: "documents.category.view" },
    { label: "Approval workflows", to: "/app/settings/approval-workflows", icon: GitBranch, permission: "approvals.workflow.view" },
    { label: "Notifications", to: "/app/settings/notifications", icon: Bell, permission: "notifications.notification.manage_preferences" },
  ] },
]

function ProductMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-9 items-center justify-center border border-white/30 bg-white/5 font-black">M</div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold tracking-wide">MONIKA ENGINEERS</p>
        <p className="text-[10px] tracking-[0.2em] text-white/50">INTEGRATED ERP</p>
      </div>
    </div>
  )
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const { data: user } = useCurrentUser()
  return (
    <nav aria-label="Application navigation" className="flex flex-1 flex-col gap-5 overflow-y-auto py-5">
      {navigation.map((section) => {
        const visible = section.items.filter((item) => !item.permission || hasPermission(user, item.permission))
        if (!visible.length) return null
        return (
          <div key={section.label} className="flex flex-col gap-1">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">{section.label}</p>
            {visible.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/app"}
                  onClick={onNavigate}
                  className={({ isActive }) => cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-white/65 transition-colors hover:bg-white/10 hover:text-white",
                    isActive && "bg-white/12 text-white",
                  )}
                >
                  <Icon aria-hidden="true" />
                  <span className="flex-1">{item.label}</span>
                  <ChevronRight aria-hidden="true" className="opacity-40" />
                </NavLink>
              )
            })}
          </div>
        )
      })}
    </nav>
  )
}

function UserFooter() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logout = useMutation({
    mutationFn: () => apiPost<void>("/auth/logout/"),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: currentUserQueryKey })
      navigate("/login", { replace: true })
    },
  })
  const initials = `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}` || user?.email?.[0]?.toUpperCase() || "U"
  return (
    <div className="flex items-center gap-3 border-t border-white/10 pt-4">
      <Avatar><AvatarFallback>{initials}</AvatarFallback></Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">{user?.employee?.display_name || user?.email}</p>
        <p className="truncate text-xs text-white/45">{user?.employee?.employee_code || "System account"}</p>
      </div>
      <Button aria-label="Sign out" variant="ghost" size="icon" onClick={() => logout.mutate()} disabled={logout.isPending}>
        <LogOut />
      </Button>
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="axis-erp-sidebar hidden min-h-svh w-64 flex-col bg-erp-sidebar p-4 text-white lg:fixed lg:inset-y-0 lg:flex">
      <ProductMark />
      <Navigation />
      <UserFooter />
    </aside>
  )
}

function MobileNavigation() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button aria-label="Open navigation" variant="outline" size="icon" className="lg:hidden"><Menu /></Button>
      </SheetTrigger>
      <SheetContent side="left" className="axis-erp-sidebar flex bg-erp-sidebar p-4 text-white">
        <SheetHeader><SheetTitle className="sr-only">Application navigation</SheetTitle></SheetHeader>
        <ProductMark />
        <Navigation />
        <UserFooter />
      </SheetContent>
    </Sheet>
  )
}

function Header() {
  const location = useLocation()
  const { data: user } = useCurrentUser()
  const pathLabel = location.pathname === "/app"
    ? "foundation overview"
    : location.pathname.match(/^\/app\/employees\/[^/]+\/edit$/)
      ? "edit employee"
      : location.pathname.match(/^\/app\/employees\/[^/]+$/)
        ? "employee profile"
        : location.pathname.split("/").filter(Boolean).at(-1)?.replaceAll("-", " ") ?? "overview"
  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <MobileNavigation />
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">Monika Engineers / Integrated ERP</p>
          <h1 className="truncate text-base font-semibold capitalize">{pathLabel}</h1>
        </div>
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium">{user?.employee?.display_name || user?.email}</p>
          <p className="text-xs text-muted-foreground">Secure session</p>
        </div>
        <ERPNotificationBell />
      </div>
    </header>
  )
}

export default function AppShell() {
  return (
    <div className="axis-erp min-h-svh bg-background text-foreground">
      <Sidebar />
      <div className="min-h-svh lg:pl-64">
        <Header />
        <main className="p-4 sm:p-6"><Outlet /></main>
        <Separator />
        <footer className="px-6 py-4 text-xs text-muted-foreground">
          Phase 1A–H · Production foundation and shared enterprise services · CRM and operational modules remain gated
        </footer>
      </div>
    </div>
  )
}
