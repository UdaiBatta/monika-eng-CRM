import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Contact,
  FileText,
  Files,
  Gauge,
  Globe2,
  LogOut,
  Menu,
  Settings2,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-switch";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import ERPNotificationBell from "@/production/components/notification-center";
import { apiPost } from "@/production/lib/api";
import {
  currentUserQueryKey,
  hasPermission,
  useCurrentUser,
} from "@/production/lib/auth";
import { getPageTitle } from "@/production/lib/page-title";
import { RealtimeProvider, useRealtime } from "@/production/lib/realtime";

type NavItem = {
  label: string;
  to: string;
  icon: typeof Gauge;
  permission?: string;
};

const navigation: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Daily work",
    items: [
      { label: "Home", to: "/app", icon: Gauge },
      {
        label: "New enquiries",
        to: "/app/crm/incoming-enquiries",
        icon: Globe2,
        permission: "crm.external_enquiry.view",
      },
      {
        label: "Active enquiries",
        to: "/app/crm/enquiries",
        icon: ClipboardList,
        permission: "enquiry.enquiry.view",
      },
      {
        label: "Customers",
        to: "/app/crm/customers",
        icon: Contact,
        permission: "crm.customer.view",
      },
      {
        label: "Quotations",
        to: "/app/crm/quotations",
        icon: FileText,
        permission: "crm.quotation.view",
      },
      {
        label: "Follow-ups",
        to: "/app/crm/activities",
        icon: Activity,
        permission: "crm.activity.view",
      },
    ],
  },
  {
    label: "Shared",
    items: [
      {
        label: "Documents",
        to: "/app/documents",
        icon: Files,
        permission: "documents.document.view",
      },
      {
        label: "Approvals",
        to: "/app/approvals",
        icon: ClipboardCheck,
        permission: "approvals.request.view",
      },
      {
        label: "Employees",
        to: "/app/employees",
        icon: Users,
        permission: "organization.employee.view",
      },
    ],
  },
];

const toolPermissions = [
  "engineering.feasibility.view",
  "estimation.estimate.view",
  "organization.company.view",
  "organization.branch.view",
  "organization.department.view",
  "organization.warehouse.view",
  "rbac.role.view",
  "rbac.permission.view",
  "rbac.assignment.view",
  "configuration.settings.view",
  "numbering.sequence.view",
  "masters.view",
  "documents.category.view",
  "approvals.workflow.view",
  "notifications.notification.manage_preferences",
  "audit.event.view",
];

function ProductMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-9 items-center justify-center border border-white/30 bg-white/5 font-black">
        M
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold tracking-wide">
          MONIKA ENGINEERS
        </p>
        <p className="text-[10px] tracking-[0.2em] text-white/50">
          INTEGRATED ERP
        </p>
      </div>
    </div>
  );
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const { data: user } = useCurrentUser();
  const canOpenTools = toolPermissions.some((permission) =>
    hasPermission(user, permission),
  );

  const renderLink = (item: NavItem) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.to}
        to={item.to}
        end={item.to === "/app"}
        onClick={onNavigate}
        className={({ isActive }) =>
          cn(
            "flex items-center gap-3 rounded-md border-l-2 border-transparent px-3 py-2 text-sm text-white/65 transition-colors hover:bg-white/10 hover:text-white",
            isActive && "border-primary bg-primary/12 text-primary",
          )
        }
      >
        <Icon aria-hidden="true" />
        <span className="flex-1">{item.label}</span>
        <ChevronRight aria-hidden="true" className="opacity-40" />
      </NavLink>
    );
  };

  return (
    <nav
      aria-label="Application navigation"
      className="flex flex-1 flex-col gap-5 overflow-y-auto py-5"
    >
      {navigation.map((section) => {
        const visible = section.items.filter(
          (item) => !item.permission || hasPermission(user, item.permission),
        );
        if (!visible.length) return null;
        return (
          <div key={section.label} className="flex flex-col gap-1">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
              {section.label}
            </p>
            {visible.map(renderLink)}
          </div>
        );
      })}
      {canOpenTools ? (
        <div className="flex flex-col gap-1">
          <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
            More
          </p>
          {renderLink({
            label: "Tools & settings",
            to: "/app/settings",
            icon: Settings2,
          })}
        </div>
      ) : null}
    </nav>
  );
}

function UserFooter() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useMutation({
    mutationFn: () => apiPost<void>("/auth/logout/"),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: currentUserQueryKey });
      navigate("/login", { replace: true });
    },
  });
  const initials =
    `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}` ||
    user?.email?.[0]?.toUpperCase() ||
    "U";
  return (
    <div className="flex items-center gap-3 border-t border-white/10 pt-4">
      <Avatar>
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">
          {user?.employee?.display_name || user?.email}
        </p>
        <p className="truncate text-xs text-white/45">
          {user?.employee?.employee_code || "System account"}
        </p>
      </div>
      <Button
        aria-label="Sign out"
        variant="ghost"
        size="icon"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        <LogOut />
      </Button>
    </div>
  );
}

function Sidebar() {
  return (
    <aside className="axis-erp-sidebar hidden min-h-svh w-56 flex-col bg-erp-sidebar p-3 text-white lg:fixed lg:inset-y-0 lg:flex">
      <ProductMark />
      <Navigation />
      <UserFooter />
    </aside>
  );
}

function MobileNavigation() {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          aria-label="Open navigation"
          variant="outline"
          size="icon"
          className="lg:hidden"
        >
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="axis-erp-sidebar flex bg-erp-sidebar p-4 text-white"
      >
        <SheetHeader>
          <SheetTitle className="sr-only">Application navigation</SheetTitle>
        </SheetHeader>
        <ProductMark />
        <Navigation onNavigate={() => setOpen(false)} />
        <UserFooter />
      </SheetContent>
    </Sheet>
  );
}

function Header() {
  const location = useLocation();
  const { data: user } = useCurrentUser();
  const pathLabel = getPageTitle(location.pathname);
  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <MobileNavigation />
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">
            Monika Engineers / Integrated ERP
          </p>
          <h1 className="truncate text-base font-semibold capitalize">
            {pathLabel}
          </h1>
        </div>
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium">
            {user?.employee?.display_name || user?.email}
          </p>
          <p className="text-xs text-muted-foreground">Secure session</p>
        </div>
        <RealtimeIndicator />
        <ThemeToggle />
        <ERPNotificationBell />
      </div>
    </header>
  );
}

function RealtimeIndicator() {
  const { status } = useRealtime();
  const live = status === "live";
  const Icon = live ? Wifi : WifiOff;
  return (
    <div
      className="hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs sm:flex"
      title={live ? "Live updates connected" : "Changes remain safe; refresh if needed"}
    >
      <span className={`size-2 rounded-full ${live ? "bg-status-success" : "bg-status-warning"}`} />
      <Icon className="size-3.5" />
      {live ? "Live" : status === "offline" ? "Offline" : "Reconnecting"}
    </div>
  );
}

function AppShellContent() {
  return (
    <div className="axis-erp min-h-svh bg-background text-foreground">
      <Sidebar />
      <div className="min-h-svh lg:pl-56">
        <Header />
        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
        <Separator />
        <footer className="px-6 py-4 text-xs text-muted-foreground">
          Monika Engineers Integrated ERP · Phase 2 Commercial CRM · Production
          foundation active
        </footer>
      </div>
    </div>
  );
}

export default function AppShell() {
  return (
    <RealtimeProvider>
      <AppShellContent />
    </RealtimeProvider>
  );
}
