import { Fragment } from "react"
import type { KeyboardEvent, ReactNode } from "react"
import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Clock3,
  FileQuestion,
  Info,
  RotateCcw,
  X,
} from "lucide-react"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

type StatusTone = "success" | "warning" | "critical" | "info" | "neutral"

const statusToneClasses: Record<StatusTone, string> = {
  success: "border-status-success/30 bg-status-success/10 text-status-success",
  warning: "border-status-warning/35 bg-status-warning/10 text-status-warning-foreground",
  critical: "border-status-critical/30 bg-status-critical/10 text-status-critical",
  info: "border-status-info/30 bg-status-info/10 text-status-info",
  neutral: "border-border bg-muted text-muted-foreground",
}

function getStatusTone(status: string): StatusTone {
  const value = status.toLowerCase()
  if (/critical|blocked|overdue|hold|failed/.test(value)) return "critical"
  if (/pending|awaiting|not started|short|scheduled|review|quote|rfq|partial/.test(value)) return "warning"
  if (/complete|ready|approved|healthy|closed|received|acknowledged/.test(value)) return "success"
  if (/progress|production|engineering|procurement|transit|site|created/.test(value)) return "info"
  return "neutral"
}

const statusIcons: Record<StatusTone, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: Clock3,
  critical: AlertTriangle,
  info: Info,
  neutral: CircleDot,
}

export function ERPStatusBadge({ status, tone }: { status: string; tone?: StatusTone }) {
  const resolvedTone = tone ?? getStatusTone(status)
  const Icon = statusIcons[resolvedTone]
  return (
    <Badge variant="outline" className={cn("h-6 rounded-md px-2 font-semibold", statusToneClasses[resolvedTone])}>
      <Icon data-icon="inline-start" />
      {status}
    </Badge>
  )
}

export function ERPPageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  meta,
}: {
  title: string
  description?: string
  breadcrumbs: string[]
  actions?: ReactNode
  meta?: ReactNode
}) {
  return (
    <header className="flex flex-col gap-3 border-b border-border bg-background px-4 py-4 lg:px-6">
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs.map((item, index) => (
            <Fragment key={item}>
              <BreadcrumbItem>
                {index === breadcrumbs.length - 1 ? (
                  <BreadcrumbPage>{item}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href="#" onClick={(event) => event.preventDefault()}>{item}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {index < breadcrumbs.length - 1 ? <BreadcrumbSeparator /> : null}
            </Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
          {description ? <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {meta}
    </header>
  )
}

export function ERPPanel({
  title,
  description,
  icon,
  action,
  children,
  className,
}: {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn("min-w-0 overflow-hidden rounded-xl border border-border bg-card", className)}>
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-card-foreground">
            {icon}
            {title}
          </h2>
          {description ? <p className="mt-0.5 text-xs text-muted-foreground">{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function ERPMetric({ label, value, detail, status }: { label: string; value: string; detail: string; status?: string }) {
  return (
    <div className="flex min-h-24 flex-col justify-between border-r border-border px-4 py-3 last:border-r-0">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <p className="text-2xl font-semibold tracking-tight text-foreground">{value}</p>
        {status ? <ERPStatusBadge status={status} /> : null}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}

export function ERPFilterBar({
  children,
  activeCount,
  onReset,
}: {
  children: ReactNode
  activeCount?: number
  onReset?: () => void
}) {
  return (
    <section aria-label="Filters" className="rounded-xl border border-border bg-card p-3">
      <div className="flex flex-wrap items-end gap-3">{children}</div>
      {activeCount ? (
        <div className="mt-3 flex items-center gap-3 border-t border-border pt-3 text-sm">
          <span className="font-medium text-status-info">{activeCount} filters active</span>
          {onReset ? (
            <Button variant="ghost" size="sm" onClick={onReset}>
              <RotateCcw data-icon="inline-start" />
              Clear filters
            </Button>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

export type ERPTableColumn<T> = {
  key: string
  label: string
  className?: string
  render: (row: T) => ReactNode
}

export function ERPDataTable<T>({
  caption,
  columns,
  rows,
  getRowId,
  selectedId,
  onSelect,
  emptyMessage = "No records match the current filters.",
}: {
  caption: string
  columns: ERPTableColumn<T>[]
  rows: T[]
  getRowId: (row: T) => string
  selectedId?: string
  onSelect?: (row: T) => void
  emptyMessage?: string
}) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!onSelect || (event.key !== "Enter" && event.key !== " ")) return
    event.preventDefault()
    onSelect(row)
  }

  return (
    <Table>
      <caption className="sr-only">{caption}</caption>
      <TableHeader>
        <TableRow className="bg-muted/55 hover:bg-muted/55">
          {columns.map((column) => (
            <TableHead key={column.key} className={cn("h-11 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground", column.className)}>
              {column.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.length ? rows.map((row) => {
          const rowId = getRowId(row)
          const selected = rowId === selectedId
          return (
            <TableRow
              key={rowId}
              data-state={selected ? "selected" : undefined}
              aria-selected={selected}
              tabIndex={onSelect ? 0 : undefined}
              className={cn("h-12 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring", onSelect && "cursor-pointer")}
              onClick={() => onSelect?.(row)}
              onKeyDown={(event) => handleKeyDown(event, row)}
            >
              {columns.map((column) => <TableCell key={column.key} className={cn("px-3 text-sm", column.className)}>{column.render(row)}</TableCell>)}
            </TableRow>
          )
        }) : (
          <TableRow>
            <TableCell colSpan={columns.length} className="h-32 text-center text-muted-foreground">{emptyMessage}</TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}

export function ERPProcessStepper({
  steps,
  current,
}: {
  steps: string[]
  current: number
}) {
  return (
    <ol aria-label="Process progress" className="flex min-w-max items-start px-2 py-4">
      {steps.map((step, index) => {
        const completed = index < current
        const active = index === current
        return (
          <li key={step} className="flex min-w-28 flex-1 items-start" aria-current={active ? "step" : undefined}>
            <div className="flex w-full items-start">
              <div className="flex min-w-20 flex-col items-center gap-1.5 text-center">
                <span className={cn(
                  "flex size-8 items-center justify-center rounded-full border-2 bg-background",
                  completed && "border-status-success bg-status-success text-white",
                  active && "border-primary bg-primary text-primary-foreground",
                  !completed && !active && "border-border text-muted-foreground",
                )}>
                  {completed ? <CheckCircle2 aria-hidden="true" /> : <span className="text-xs font-bold">{index + 1}</span>}
                </span>
                <span className={cn("text-xs font-medium", active ? "text-primary" : completed ? "text-status-success" : "text-muted-foreground")}>{step}</span>
              </div>
              {index < steps.length - 1 ? <span aria-hidden="true" className={cn("mt-4 h-0.5 min-w-8 flex-1", index < current ? "bg-status-success" : "bg-border")} /> : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export function ERPActivityTimeline({ items }: { items: Array<{ time: string; title: string; meta: string; tone: string }> }) {
  return (
    <ol className="flex flex-col px-4 py-2">
      {items.map((item) => {
        const tone = item.tone as StatusTone
        const Icon = statusIcons[tone] ?? CircleDot
        return (
          <li key={`${item.time}-${item.title}`} className="grid grid-cols-[1.25rem_1fr] gap-3 border-b border-border py-3 last:border-b-0">
            <Icon className={cn("mt-0.5", tone === "success" && "text-status-success", tone === "warning" && "text-status-warning", tone === "info" && "text-status-info")} aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">{item.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.time} · {item.meta}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export function ERPDetailPanel({ title, subtitle, status, onClose, children, actions }: { title: string; subtitle?: string; status?: string; onClose?: () => void; children: ReactNode; actions?: ReactNode }) {
  return (
    <aside aria-label={`${title} details`} className="min-w-0 overflow-hidden rounded-xl border border-border bg-card lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-4">
        <div>
          <h2 className="text-lg font-semibold text-card-foreground">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
          {status ? <div className="mt-2"><ERPStatusBadge status={status} /></div> : null}
        </div>
        {onClose ? <Button aria-label="Close detail panel" variant="ghost" size="icon" onClick={onClose}><X /></Button> : null}
      </div>
      <div className="p-4">{children}</div>
      {actions ? <div className="flex flex-col gap-2 border-t border-border p-4">{actions}</div> : null}
    </aside>
  )
}

export function ERPDocumentPanel({ documents }: { documents: Array<{ number: string; title: string; revision: string; type: string; owner: string }> }) {
  return (
    <ERPPanel title={`Documents (${documents.length})`}>
      <ERPDataTable
        caption="Project documents"
        rows={documents}
        getRowId={(document) => document.number}
        columns={[
          { key: "number", label: "Document", render: (document) => <span className="font-medium text-primary">{document.number}</span> },
          { key: "title", label: "Title", render: (document) => document.title },
          { key: "revision", label: "Rev.", render: (document) => document.revision },
          { key: "type", label: "Type", render: (document) => document.type },
          { key: "owner", label: "Owner", render: (document) => document.owner },
        ]}
      />
    </ERPPanel>
  )
}

export function ERPApprovalPanel({ approvals }: { approvals: Array<{ title: string; owner: string; due: string; status: string }> }) {
  return (
    <ERPPanel title={`Pending Approvals (${approvals.length})`}>
      <ul className="divide-y divide-border">
        {approvals.map((approval) => (
          <li key={approval.title} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">{approval.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{approval.owner} · Due {approval.due}</p>
            </div>
            <ERPStatusBadge status={approval.status} />
          </li>
        ))}
      </ul>
    </ERPPanel>
  )
}

export function ERPEmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 px-6 text-center">
      <FileQuestion className="text-muted-foreground" aria-hidden="true" />
      <div>
        <h3 className="font-semibold text-foreground">{title}</h3>
        <p className="mt-1 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

export function ERPProgress({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-foreground">{label}</span>
        <span className="font-semibold text-foreground">{value}%</span>
      </div>
      <Progress value={value} aria-label={`${label}: ${value}%`} className="h-2" />
    </div>
  )
}
