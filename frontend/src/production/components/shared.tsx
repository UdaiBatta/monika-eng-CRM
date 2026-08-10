import type { ReactNode } from "react"
import { AlertTriangle, Inbox, LockKeyhole } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export function ERPPageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-col justify-between gap-4 border-b pb-5 md:flex-row md:items-end">
      <div>
        {eyebrow ? <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-primary">{eyebrow}</p> : null}
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  )
}

const statusVariants: Record<string, string> = {
  ACTIVE: "border-emerald-700/20 bg-emerald-600/10 text-emerald-800",
  APPROVED: "border-emerald-700/20 bg-emerald-600/10 text-emerald-800",
  SUCCESS: "border-emerald-700/20 bg-emerald-600/10 text-emerald-800",
  IN_PROGRESS: "border-blue-700/20 bg-blue-600/10 text-blue-800",
  OPEN: "border-amber-700/20 bg-amber-500/10 text-amber-900",
  PENDING: "border-amber-700/20 bg-amber-500/10 text-amber-900",
  ACTION_REQUIRED: "border-amber-700/20 bg-amber-500/10 text-amber-900",
  WARNING: "border-amber-700/20 bg-amber-500/10 text-amber-900",
  ARCHIVED: "border-slate-500/20 bg-slate-500/10 text-slate-700",
  CANCELLED: "border-slate-500/20 bg-slate-500/10 text-slate-700",
  REJECTED: "border-red-700/20 bg-red-600/10 text-red-800",
  CRITICAL: "border-red-700/20 bg-red-600/10 text-red-800",
  RETURNED_FOR_CHANGES: "border-orange-700/20 bg-orange-600/10 text-orange-800",
}

export function ERPStatusBadge({ value, label }: { value: string; label?: string }) {
  return (
    <Badge variant="outline" className={cn("font-medium", statusVariants[value])}>
      {label ?? value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase())}
    </Badge>
  )
}

export function ERPLoadingState({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-label="Loading" className="flex flex-col gap-3">
      {Array.from({ length: rows }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)}
    </div>
  )
}

export function ERPErrorState({ title = "Could not load this information", message }: { title?: string; message: string }) {
  return (
    <Alert variant="destructive">
      <AlertTriangle aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  )
}

export function ERPEmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon"><Inbox /></EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      {action ? <EmptyContent>{action}</EmptyContent> : null}
    </Empty>
  )
}

export function ERPPermissionState() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon"><LockKeyhole /></EmptyMedia>
        <EmptyTitle>Access restricted</EmptyTitle>
        <EmptyDescription>
          You do not have permission to view this information. Contact your administrator if you believe you need access.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent><Button variant="outline" onClick={() => history.back()}>Go back</Button></EmptyContent>
    </Empty>
  )
}

export function formatDateTime(value?: string | null) {
  if (!value) return "Not yet"
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

export function formatBytes(bytes?: number | null) {
  if (!bytes) return "0 KB"
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
