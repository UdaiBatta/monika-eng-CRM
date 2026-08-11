import type { ReactNode } from "react";
import { AlertTriangle, Inbox, LockKeyhole } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function ERPPageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col justify-between gap-4 border-b pb-5 md:flex-row md:items-end">
      <div>
        {eyebrow ? (
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
          {description}
        </p>
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>
      ) : null}
    </header>
  );
}

const successStatus =
  "border-status-success/40 bg-status-success/10 text-status-success";
const warningStatus =
  "border-status-warning/40 bg-status-warning/10 text-status-warning";
const infoStatus = "border-status-info/40 bg-status-info/10 text-status-info";
const criticalStatus =
  "border-status-critical/40 bg-status-critical/10 text-status-critical";
const neutralStatus =
  "border-muted-foreground/30 bg-muted text-muted-foreground";

const statusVariants: Record<string, string> = {
  ACTIVE: successStatus,
  APPROVED: successStatus,
  FEASIBLE: successStatus,
  SUCCESS: successStatus,
  WON: successStatus,
  COMPLETED: successStatus,
  IN_PROGRESS: infoStatus,
  IN_PREPARATION: infoStatus,
  IN_REVIEW: infoStatus,
  RECEIVED: infoStatus,
  NEW: infoStatus,
  UNDER_REVIEW: infoStatus,
  NEEDS_REVIEW: infoStatus,
  POSSIBLE_DUPLICATE: warningStatus,
  SUSPICIOUS: warningStatus,
  LIKELY_VALID: successStatus,
  CLEAN: successStatus,
  ACCEPTED: successStatus,
  CONVERTED: successStatus,
  ENGINEERING_REVIEW: warningStatus,
  CLARIFICATION_REQUIRED: warningStatus,
  OPEN: warningStatus,
  PENDING: warningStatus,
  PENDING_APPROVAL: warningStatus,
  READY_FOR_REVIEW: warningStatus,
  ACTION_REQUIRED: warningStatus,
  WARNING: warningStatus,
  HIGH: warningStatus,
  URGENT: criticalStatus,
  REJECTED: criticalStatus,
  BLOCKED: criticalStatus,
  LOST: criticalStatus,
  NOT_FEASIBLE: criticalStatus,
  CRITICAL: criticalStatus,
  SPAM: criticalStatus,
  ARCHIVED: neutralStatus,
  DRAFT: neutralStatus,
  SUPERSEDED: neutralStatus,
  OPTIONAL: neutralStatus,
  CANCELLED: neutralStatus,
  INACTIVE: neutralStatus,
  PROSPECT: "border-primary/40 bg-primary/10 text-primary",
  RETURNED_FOR_CHANGES: "border-primary/40 bg-primary/10 text-primary",
};

export function ERPStatusBadge({
  value,
  label,
}: {
  value: string;
  label?: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn("font-medium", statusVariants[value])}
    >
      {label ??
        value
          .replaceAll("_", " ")
          .toLowerCase()
          .replace(/^./, (letter) => letter.toUpperCase())}
    </Badge>
  );
}

export function ERPLoadingState({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-label="Loading" className="flex flex-col gap-3">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function ERPErrorState({
  title = "Could not load this information",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <Alert variant="destructive">
      <AlertTriangle aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function ERPEmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Inbox />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      {action ? <EmptyContent>{action}</EmptyContent> : null}
    </Empty>
  );
}

export function ERPPermissionState() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <LockKeyhole />
        </EmptyMedia>
        <EmptyTitle>Access restricted</EmptyTitle>
        <EmptyDescription>
          You do not have permission to view this information. Contact your
          administrator if you believe you need access.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" onClick={() => history.back()}>
          Go back
        </Button>
      </EmptyContent>
    </Empty>
  );
}

export function formatDateTime(value?: string | null) {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

export function formatBytes(bytes?: number | null) {
  if (!bytes) return "0 KB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
