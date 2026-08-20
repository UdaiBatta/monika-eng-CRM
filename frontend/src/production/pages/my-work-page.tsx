import { useQueries } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, ClipboardCheck, FileText, FolderKanban, Inbox, MessageSquareText, ShieldCheck, Wrench } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, formatDateTime } from "@/production/components/shared";
import { apiGet } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import { employeeLabel } from "@/production/lib/terminology";
import type { CrmActivity, EngineeringReview, ExternalEnquirySubmission, Quotation } from "@/production/lib/crm-types";
import type { Project, SalesOrder } from "@/production/lib/sales-types";
import type { Paginated } from "@/production/lib/types";

type WorkTask = {
  id: string;
  title: string;
  context: string;
  reason: string;
  status: string;
  statusLabel?: string;
  href: string;
  action: string;
  attention: boolean;
  icon: typeof Inbox;
};

type WorkSource = {
  key: string;
  permission: string;
  load: () => Promise<WorkTask[]>;
};

const sources: WorkSource[] = [
  {
    key: "incoming",
    permission: "crm.external_enquiry.review",
    load: async () => {
      const data = await apiGet<Paginated<ExternalEnquirySubmission>>("/external-enquiries/?queue=mine&page_size=5&ordering=-received_at");
      return data.results.map((item) => ({ id: `incoming-${item.id}`, title: item.subject || "Customer enquiry", context: item.company_name || item.person_name, reason: `${item.channel_label || item.channel} enquiry received`, status: item.review_status, href: `/app/crm/incoming-enquiries/${item.id}`, action: "Review enquiry", attention: item.priority === "URGENT" || item.priority === "HIGH", icon: Inbox }));
    },
  },
  {
    key: "follow-ups",
    permission: "crm.activity.view",
    load: async () => {
      const data = await apiGet<Paginated<CrmActivity>>("/crm-activities/?mine=true&status=OPEN&page_size=5");
      return data.results.map((item) => ({ id: `activity-${item.id}`, title: item.subject, context: item.customer_name, reason: item.is_overdue ? "Follow-up is overdue" : item.next_follow_up_at ? `Follow up ${formatDateTime(item.next_follow_up_at)}` : "Open customer follow-up", status: item.is_overdue ? "ACTION_REQUIRED" : item.status, href: "/app/crm/activities", action: "Record follow-up", attention: item.is_overdue, icon: MessageSquareText }));
    },
  },
  {
    key: "quotations",
    permission: "crm.quotation.view",
    load: async () => {
      const data = await apiGet<Paginated<Quotation>>("/quotations/?queue=mine&page_size=5&ordering=-updated_at");
      return data.results.map((item) => ({ id: `quotation-${item.id}`, title: item.quotation_number, context: item.customer_name, reason: item.status === "DRAFT" ? "Quotation needs preparation" : item.status === "FINALIZED" ? "Quotation is ready to share" : "Customer decision is still open", status: item.status, statusLabel: item.status_label, href: `/app/crm/quotations/${item.id}`, action: "Continue quotation", attention: Boolean(item.current_revision.valid_until && new Date(item.current_revision.valid_until) <= new Date(Date.now() + 86_400_000)), icon: FileText }));
    },
  },
  {
    key: "sales-orders",
    permission: "sales.sales_order.view",
    load: async () => {
      const data = await apiGet<Paginated<SalesOrder>>("/sales/orders/?queue=mine&page_size=5&ordering=-updated_at");
      return data.results.filter((item) => !["CANCELLED", "SUPERSEDED"].includes(item.status)).map((item) => ({ id: `sales-order-${item.id}`, title: item.sales_order_number, context: item.customer_name, reason: item.status === "DRAFT" ? "Sales Order needs preparation" : item.status === "APPROVED" ? "Sales Order is ready to release" : "Sales Order needs attention", status: item.status, statusLabel: item.status_label, href: `/app/sales/orders/${item.id}`, action: "Continue Sales Order", attention: item.status === "APPROVED" || item.po_pending, icon: ClipboardCheck }));
    },
  },
  {
    key: "workshop-review",
    permission: "engineering.feasibility.view",
    load: async () => {
      const data = await apiGet<Paginated<EngineeringReview>>("/engineering-reviews/?queue=mine&page_size=5");
      return data.results.map((item) => ({ id: `workshop-${item.id}`, title: item.enquiry_subject, context: `${item.customer_name} · ${item.enquiry_number}`, reason: item.open_clarifications ? `${item.open_clarifications} clarification${item.open_clarifications === 1 ? "" : "s"} need attention` : "Workshop Review assigned to you", status: item.status, statusLabel: item.result || undefined, href: `/app/workshop/reviews/${item.id}`, action: "Open Workshop Review", attention: item.open_clarifications > 0, icon: Wrench }));
    },
  },
  {
    key: "projects",
    permission: "projects.handoff.take_ownership",
    load: async () => {
      const data = await apiGet<Paginated<Project>>("/projects/?queue=mine&page_size=5&ordering=-updated_at");
      return data.results.map((item) => ({ id: `project-${item.id}`, title: item.project_number, context: `${item.customer_name} · ${item.project_name}`, reason: employeeLabel(item.next_action), status: item.status, statusLabel: item.status_label, href: `/app/projects/${item.id}`, action: "Open project", attention: item.open_clarification_count > 0 || item.commercial_change_pending, icon: FolderKanban }));
    },
  },
];

function TaskList({ tasks }: { tasks: WorkTask[] }) {
  return <div className="divide-y">{tasks.map((task) => { const Icon = task.icon; return <article key={task.id} className="grid gap-4 py-4 first:pt-0 last:pb-0 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center"><span className="grid size-10 place-items-center rounded-md border bg-muted text-primary"><Icon aria-hidden="true" /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{task.title}</h3><ERPStatusBadge value={task.status} label={task.statusLabel} /></div><p className="mt-1 text-sm text-muted-foreground">{task.context}</p><p className={task.attention ? "mt-2 text-sm font-medium text-status-warning" : "mt-2 text-sm"}>{task.reason}</p></div><Button nativeButton={false} render={<Link to={task.href} />}>{task.action}<ArrowRight data-icon="inline-end" /></Button></article>; })}</div>;
}

export default function MyWorkPage() {
  const { data: user } = useCurrentUser();
  const visibleSources = sources.filter((source) => hasPermission(user, source.permission));
  const queries = useQueries({ queries: visibleSources.map((source) => ({ queryKey: ["my-work", source.key], queryFn: source.load, staleTime: 20_000 })) });
  const tasks = queries.flatMap((query) => query.data ?? []).sort((left, right) => Number(right.attention) - Number(left.attention));
  const attention = tasks.filter((task) => task.attention);
  const today = tasks.filter((task) => !task.attention);
  const pending = queries.some((query) => query.isPending);
  const errors = queries.filter((query) => query.isError);
  const displayName = user?.employee?.display_name || user?.first_name || "there";
  const owner = hasPermission(user, "system.owner_control.view");

  return <div className="mx-auto flex max-w-6xl flex-col gap-6">
    <ERPPageHeader eyebrow="Daily work" title={`Good to see you, ${displayName}`} description="Start here. These are real records assigned to you, with the next useful action beside each one." actions={owner ? <Button variant="outline" nativeButton={false} render={<Link to="/app/owner" />}><ShieldCheck data-icon="inline-start" />Owner Centre</Button> : undefined} />
    {errors.length ? <ERPErrorState title="Some work could not be loaded" message="The available queues are still shown. Refresh to retry the missing information." /> : null}
    {attention.length ? <Card className="border-status-warning/40"><CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="text-status-warning" />Needs Attention</CardTitle><CardDescription>Overdue, time-sensitive, or blocked work is brought forward automatically.</CardDescription></CardHeader><CardContent><TaskList tasks={attention.slice(0, 5)} /></CardContent></Card> : null}
    <Card><CardHeader><CardTitle>Your Work Today</CardTitle><CardDescription>Open the record, complete the highlighted step, then return here for the next item.</CardDescription></CardHeader><CardContent>{pending ? <ERPLoadingState rows={5} /> : today.length ? <TaskList tasks={today.slice(0, 10)} /> : <ERPEmptyState title={attention.length ? "Everything open needs attention" : "Your queue is clear"} description={attention.length ? "Use the Needs Attention list above first." : "No open work is currently assigned to you. Team and unassigned queues remain available inside the relevant workspace."} />}</CardContent></Card>
  </div>;
}
