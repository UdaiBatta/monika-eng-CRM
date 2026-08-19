import {
  Activity,
  DatabaseZap,
  HeartPulse,
  ListChecks,
  Settings2,
  ShieldCheck,
} from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"

const sections = [
  { label: "Overview", to: "/app/owner", icon: ShieldCheck, permission: "system.owner_control.view", end: true },
  { label: "Work assignment", to: "/app/owner/work", icon: ListChecks, permission: "system.owner_control.view" },
  { label: "Access check", to: "/app/owner/access", icon: Activity, permission: "system.access_explanation.view" },
  { label: "Features", to: "/app/owner/features", icon: Settings2, permission: "configuration.feature_flag.view" },
  { label: "Data quality", to: "/app/owner/data-quality", icon: DatabaseZap, permission: "system.data_quality.view" },
  { label: "System health", to: "/app/owner/system-health", icon: HeartPulse, permission: "system.system_health.view" },
]

export default function OwnerControlLayout() {
  const { data: user } = useCurrentUser()
  if (!hasPermission(user, "system.owner_control.view")) {
    return (
      <Alert variant="destructive">
        <ShieldCheck />
        <AlertTitle>Owner Control is restricted</AlertTitle>
        <AlertDescription>
          Your current role does not include business-owner administration. Ask an existing Owner
          to review your access instead of sharing an administrator account.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <div className="rounded-xl border bg-card p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
          Business administration
        </p>
        <div className="mt-2 flex flex-col gap-1">
          <h2 className="text-2xl font-semibold">Owner Control Centre</h2>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Manage people, access, work responsibility, business rules and system readiness without
            opening Django administration or the database.
          </p>
        </div>
        <nav aria-label="Owner Control sections" className="mt-4 flex flex-wrap gap-2">
          {sections
            .filter((section) => hasPermission(user, section.permission))
            .map((section) => {
              const Icon = section.icon
              return (
                <Button
                  key={section.to}
                  variant="outline"
                  size="sm"
                  nativeButton={false}
                  render={
                    <NavLink
                      to={section.to}
                      end={section.end}
                      className={({ isActive }) => cn(isActive && "border-primary bg-primary/10")}
                    />
                  }
                >
                  <Icon data-icon="inline-start" />
                  {section.label}
                </Button>
              )
            })}
        </nav>
      </div>
      <Outlet />
    </div>
  )
}

