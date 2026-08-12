import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  CalendarClock,
  Check,
  CircleDot,
  ClipboardCheck,
  FileText,
  Pencil,
  Plus,
  Send,
  UserRoundCog,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ActivityForm } from "@/production/components/crm-forms";
import {
  EnquiryForm,
  ItemForm,
  RequirementForm,
} from "@/production/components/enquiry-forms";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatBytes,
  formatDateTime,
} from "@/production/components/shared";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  Customer,
  EnquiryItem,
  EnquiryRequirement,
  EnquiryWorkspace,
  Quotation,
  RelationOption,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

type Panel =
  | { kind: "edit" }
  | { kind: "requirement"; record?: EnquiryRequirement }
  | { kind: "item"; record?: EnquiryItem }
  | { kind: "activity" }
  | { kind: "assign" }
  | null;
const activeStages = [
  "DRAFT",
  "RECEIVED",
  "UNDER_REVIEW",
  "ENGINEERING_REVIEW",
  "READY_FOR_ESTIMATION",
  "ESTIMATION",
  "ESTIMATION_COMPLETE",
];

function money(amount: string | null, code: string) {
  return amount
    ? `${code || "₹"} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(amount))}`
    : "Not recorded";
}

function StageTracker({ workspace }: { workspace: EnquiryWorkspace }) {
  const status = ["ESTIMATION", "ESTIMATION_COMPLETE"].includes(
    workspace.enquiry.status,
  )
    ? workspace.enquiry.status
    : workspace.engineering_review?.ready_for_estimation
      ? "READY_FOR_ESTIMATION"
      : workspace.enquiry.status;
  const current = Math.max(0, activeStages.indexOf(status));
  const stages = [
    ["DRAFT", "Draft"],
    ["RECEIVED", "Received"],
    ["UNDER_REVIEW", "Commercial review"],
    ["ENGINEERING_REVIEW", "Engineering feasibility"],
    ["READY_FOR_ESTIMATION", "Ready for estimation"],
    ["ESTIMATION", "Commercial estimation"],
    ["ESTIMATION_COMPLETE", "Ready for quotation"],
  ];
  return (
    <Card className="border-primary/25">
      <CardContent className="p-4">
        <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-7">
          {stages.map(([key, label], index) => {
            const complete = index < current;
            const selected = key === status;
            return (
              <div
                key={key}
                className={`relative flex items-center gap-3 rounded-md border p-3 ${selected ? "border-primary bg-primary/10" : complete ? "border-status-success/30 bg-status-success/5" : "bg-muted/20"}`}
              >
                <span
                  className={`grid size-7 shrink-0 place-items-center rounded-full border ${selected ? "border-primary text-primary" : complete ? "border-status-success bg-status-success text-primary-foreground" : "text-muted-foreground"}`}
                >
                  {complete ? <Check /> : index + 1}
                </span>
                <div>
                  <p
                    className={`text-sm font-medium ${selected ? "text-primary" : ""}`}
                  >
                    {label}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {selected
                      ? "Current stage"
                      : complete
                        ? "Complete"
                        : "Pending"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3 text-xs text-muted-foreground">
          <span>
            {status === "ESTIMATION_COMPLETE"
              ? "Milestone handoff:"
              : "Controlled flow:"}
          </span>
          <Badge variant="outline">
            {status === "ESTIMATION_COMPLETE"
              ? "Estimation approved"
              : "Estimation"}
          </Badge>
          <ArrowRight />
          <Badge
            variant={status === "ESTIMATION_COMPLETE" ? "default" : "outline"}
          >
            {status === "ESTIMATION_COMPLETE"
              ? "Ready for quotation"
              : "Quotation · not built"}
          </Badge>
          {status === "ESTIMATION_COMPLETE" ? (
            <span>Quotation is intentionally not implemented.</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export default function EnquiryPage() {
  const { enquiryId = "" } = useParams();
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [panel, setPanel] = useState<Panel>(null);
  const [closeAction, setCloseAction] = useState<"mark-lost" | "cancel" | null>(
    null,
  );
  const [reason, setReason] = useState("");
  const [competitor, setCompetitor] = useState("");
  const [feedback, setFeedback] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const query = useQuery({
    queryKey: ["enquiry-workspace", enquiryId],
    queryFn: () =>
      apiGet<EnquiryWorkspace>(`/enquiries/${enquiryId}/workspace/`),
  });
  const quotations = useQuery({
    queryKey: ["enquiry-quotations", enquiryId],
    queryFn: () => apiGet<Paginated<Quotation>>(`/quotations/?enquiry=${enquiryId}&page_size=100`),
    enabled: Boolean(enquiryId) && hasPermission(user, "crm.quotation.view"),
  });
  const customerQuery = useQuery({
    queryKey: ["customer", query.data?.enquiry.customer],
    queryFn: () =>
      apiGet<Customer>(`/customers/${query.data?.enquiry.customer}/`),
    enabled: Boolean(
      query.data?.enquiry.customer && panel?.kind === "activity",
    ),
  });
  const employees = useQuery({
    queryKey: ["enquiry-options", "employees"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/employees/?employment_status=ACTIVE&page_size=100",
      ),
    enabled: panel?.kind === "assign",
    staleTime: 60_000,
  });
  const refresh = () => {
    queryClient.invalidateQueries({
      queryKey: ["enquiry-workspace", enquiryId],
    });
    queryClient.invalidateQueries({ queryKey: ["enquiries"] });
  };
  const command = useMutation({
    mutationFn: ({
      action,
      payload = {},
    }: {
      action: string;
      payload?: Record<string, unknown>;
    }) => apiPost(`/enquiries/${enquiryId}/${action}/`, payload),
    onSuccess: (_, variables) => {
      refresh();
      toast.success(
        variables.action === "send-to-engineering"
          ? "Engineering feasibility requested."
          : "Enquiry stage updated.",
      );
    },
  });
  const assign = useMutation({
    mutationFn: () =>
      apiPost(`/enquiries/${enquiryId}/assign/`, {
        salesperson_id: assignedTo,
      }),
    onSuccess: () => {
      refresh();
      toast.success("Enquiry reassigned.");
      setPanel(null);
    },
  });
  if (query.isPending) return <ERPLoadingState rows={10} />;
  if (query.isError)
    return (
      <ERPErrorState
        title="Enquiry could not be opened"
        message={query.error.message}
      />
    );
  const workspace = query.data;
  const enquiry = workspace.enquiry;
  const closed = ["WON", "LOST", "CANCELLED"].includes(enquiry.status);
  const canEdit = hasPermission(user, "enquiry.enquiry.edit") && !closed;
  const canAssign = hasPermission(user, "enquiry.enquiry.assign") && !closed;
  const canSubmitEngineering = hasPermission(
    user,
    "enquiry.enquiry.submit_engineering",
  );
  const panelTitle =
    panel?.kind === "edit"
      ? "Edit enquiry"
      : panel?.kind === "requirement"
        ? panel.record
          ? "Edit requirement"
          : "Add requirement"
        : panel?.kind === "item"
          ? panel.record
            ? "Edit item line"
            : "Add item line"
          : panel?.kind === "activity"
            ? "Record enquiry activity"
            : "Reassign enquiry";
  const runClose = () =>
    command.mutate(
      {
        action: closeAction ?? "cancel",
        payload: { reason, competitor, customer_feedback: feedback },
      },
      {
        onSuccess: () => {
          setCloseAction(null);
          setReason("");
          setCompetitor("");
          setFeedback("");
        },
      },
    );
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Enquiry 360"
        title={enquiry.subject}
        description={`${enquiry.enquiry_number} · ${enquiry.customer_name} · ${enquiry.customer_reference || "No customer RFQ reference"}`}
        actions={
          <>
            <ERPStatusBadge value={enquiry.status} />
            {canAssign ? (
              <Button
                variant="outline"
                onClick={() => {
                  setAssignedTo(enquiry.responsible_salesperson);
                  setPanel({ kind: "assign" });
                }}
              >
                <UserRoundCog data-icon="inline-start" />
                Assign
              </Button>
            ) : null}
            {canEdit ? (
              <Button
                variant="outline"
                onClick={() => setPanel({ kind: "edit" })}
              >
                <Pencil data-icon="inline-start" />
                Edit
              </Button>
            ) : null}
          </>
        }
      />
      <StageTracker workspace={workspace} />
      {command.error ? (
        <Alert variant="destructive">
          <AlertTitle>Stage could not be changed</AlertTitle>
          <AlertDescription>{command.error.message}</AlertDescription>
        </Alert>
      ) : null}
      <Card>
        <CardContent className="grid gap-5 p-5 sm:grid-cols-2 xl:grid-cols-6">
          <div>
            <p className="text-xs text-muted-foreground">Customer</p>
            <Link
              className="font-medium hover:text-primary"
              to={`/app/crm/customers/${enquiry.customer}`}
            >
              {enquiry.customer_name}
            </Link>
            <p className="text-xs text-muted-foreground">
              {enquiry.customer_code}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Sales owner</p>
            <p className="font-medium">
              {enquiry.responsible_salesperson_name}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Priority</p>
            <ERPStatusBadge value={enquiry.priority} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Received</p>
            <p className="font-medium">{enquiry.received_date}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Response due</p>
            <p
              className={
                enquiry.is_overdue
                  ? "font-medium text-destructive"
                  : "font-medium"
              }
            >
              {enquiry.due_date || "Not set"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Indicative value</p>
            <p className="font-medium">
              {money(enquiry.estimated_value, enquiry.currency_code)}
            </p>
          </div>
        </CardContent>
      </Card>
      <div className="flex flex-wrap gap-2">
        {enquiry.status === "DRAFT" && canEdit ? (
          <Button onClick={() => command.mutate({ action: "receive" })}>
            <Check data-icon="inline-start" />
            Mark received
          </Button>
        ) : null}
        {enquiry.status === "RECEIVED" && canEdit ? (
          <Button onClick={() => command.mutate({ action: "start-review" })}>
            <ClipboardCheck data-icon="inline-start" />
            Start commercial review
          </Button>
        ) : null}
        {["RECEIVED", "UNDER_REVIEW"].includes(enquiry.status) &&
        canSubmitEngineering ? (
          <Button
            onClick={() => command.mutate({ action: "send-to-engineering" })}
          >
            <Send data-icon="inline-start" />
            Send to engineering
          </Button>
        ) : null}
        {!closed && hasPermission(user, "enquiry.enquiry.mark_lost") ? (
          <Button variant="outline" onClick={() => setCloseAction("mark-lost")}>
            Mark lost
          </Button>
        ) : null}
        {!closed && hasPermission(user, "enquiry.enquiry.cancel") ? (
          <Button variant="ghost" onClick={() => setCloseAction("cancel")}>
            Cancel enquiry
          </Button>
        ) : null}
      </div>
      <Tabs defaultValue="overview">
        <div className="overflow-x-auto pb-1">
          <TabsList className="h-auto min-w-max justify-start">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="requirements">
              Requirements{" "}
              <Badge variant="outline">{enquiry.requirements.length}</Badge>
            </TabsTrigger>
            <TabsTrigger value="items">
              Items <Badge variant="outline">{enquiry.items.length}</Badge>
            </TabsTrigger>
            <TabsTrigger value="engineering">Engineering</TabsTrigger>
            {hasPermission(user, "crm.quotation.view") ? <TabsTrigger value="quotations">Quotations <Badge variant="outline">{quotations.data?.pagination.count ?? 0}</Badge></TabsTrigger> : null}
            <TabsTrigger value="activities">Activities</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
            <Card>
              <CardHeader>
                <CardTitle>RFQ summary</CardTitle>
                <CardDescription>
                  Customer need and commercial framing passed into
                  qualification.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <p className="text-xs text-muted-foreground">Description</p>
                  <p className="mt-1 whitespace-pre-wrap leading-6">
                    {enquiry.description || "No description recorded."}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    Customer contact
                  </p>
                  <p>{enquiry.customer_contact_name || "Not selected"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Customer site</p>
                  <p>{enquiry.customer_site_name || "Not selected"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Source</p>
                  <p>{enquiry.source || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    Customer reference
                  </p>
                  <p>{enquiry.customer_reference || "—"}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Next action</CardTitle>
                <CardDescription>
                  Immediate commercial commitment for this RFQ.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {workspace.next_follow_up ? (
                  <div className="flex gap-3 rounded-lg border bg-muted/20 p-4">
                    <CalendarClock
                      className={
                        workspace.next_follow_up.is_overdue
                          ? "text-destructive"
                          : "text-primary"
                      }
                    />
                    <div>
                      <p className="font-medium">
                        {workspace.next_follow_up.subject}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(
                          workspace.next_follow_up.next_follow_up_at,
                        )}{" "}
                        · {workspace.next_follow_up.follow_up_owner_name}
                      </p>
                    </div>
                  </div>
                ) : (
                  <ERPEmptyState
                    title="No follow-up scheduled"
                    description="Record an enquiry activity and choose Follow-up to assign the next action."
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="requirements" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Requirements</CardTitle>
                <CardDescription>
                  Technical, commercial, delivery, and compliance needs.
                </CardDescription>
              </div>
              {canEdit ? (
                <Button
                  size="sm"
                  onClick={() => setPanel({ kind: "requirement" })}
                >
                  <Plus data-icon="inline-start" />
                  Add requirement
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {enquiry.requirements.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {enquiry.requirements.map((requirement) => (
                    <div
                      key={requirement.id}
                      className="rounded-lg border bg-muted/20 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <ERPStatusBadge
                              value={requirement.requirement_type}
                            />
                            <Badge
                              variant={
                                requirement.is_mandatory ? "default" : "outline"
                              }
                            >
                              {requirement.is_mandatory
                                ? "Mandatory"
                                : "Optional"}
                            </Badge>
                          </div>
                          <p className="mt-3 font-medium">
                            {requirement.title}
                          </p>
                        </div>
                        {canEdit ? (
                          <Button
                            aria-label={`Edit ${requirement.title}`}
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setPanel({
                                kind: "requirement",
                                record: requirement,
                              })
                            }
                          >
                            <Pencil />
                          </Button>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {requirement.description}
                      </p>
                      {requirement.customer_specification_reference ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Spec: {requirement.customer_specification_reference}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No requirements captured"
                  description="Add the customer scope before requesting engineering feasibility."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="items" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>RFQ item lines</CardTitle>
                <CardDescription>
                  Requested products, assemblies, quantities, and delivery
                  dates.
                </CardDescription>
              </div>
              {canEdit ? (
                <Button size="sm" onClick={() => setPanel({ kind: "item" })}>
                  <Plus data-icon="inline-start" />
                  Add item
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {enquiry.items.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="p-3">Line</th>
                        <th className="p-3">Description / specification</th>
                        <th className="p-3">Customer ref.</th>
                        <th className="p-3">Quantity</th>
                        <th className="p-3">Requested delivery</th>
                        <th className="p-3"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {enquiry.items.map((item) => (
                        <tr key={item.id} className="border-b last:border-0">
                          <td className="p-3 font-mono text-primary">
                            {String(item.line_number).padStart(2, "0")}
                          </td>
                          <td className="p-3">
                            <p className="font-medium">{item.description}</p>
                            <p className="max-w-xl text-xs text-muted-foreground">
                              {item.technical_specification ||
                                "No specification added"}
                            </p>
                          </td>
                          <td className="p-3">
                            {item.customer_reference || "—"}
                          </td>
                          <td className="p-3 whitespace-nowrap">
                            {item.quantity} {item.uom_code}
                          </td>
                          <td className="p-3 whitespace-nowrap">
                            {item.requested_delivery || "—"}
                          </td>
                          <td className="p-3">
                            {canEdit ? (
                              <Button
                                aria-label={`Edit line ${item.line_number}`}
                                variant="ghost"
                                size="icon"
                                onClick={() =>
                                  setPanel({ kind: "item", record: item })
                                }
                              >
                                <Pencil />
                              </Button>
                            ) : null}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ERPEmptyState
                  title="No item lines captured"
                  description="Add each requested assembly or deliverable as a separate item line."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="engineering" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Engineering feasibility</CardTitle>
              <CardDescription>
                The current controlled review and its decision gate.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {workspace.engineering_review ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Revision</p>
                    <p className="font-medium">
                      Rev {workspace.engineering_review.revision_number}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Engineer</p>
                    <p className="font-medium">
                      {workspace.engineering_review.assigned_engineer_name ||
                        "Unassigned"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Status / decision
                    </p>
                    <ERPStatusBadge
                      value={workspace.engineering_review.status}
                      label={workspace.engineering_review.result || undefined}
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Clarifications
                    </p>
                    <p className="font-medium">
                      {workspace.engineering_review.open_clarifications} open
                    </p>
                  </div>
                  <div className="sm:col-span-2 lg:col-span-4">
                    <Button
                      onClick={() =>
                        navigate(
                          `/app/crm/engineering/${workspace.engineering_review?.id}`,
                        )
                      }
                    >
                      Open engineering review
                    </Button>
                  </div>
                </div>
              ) : enquiry.status === "ENGINEERING_REVIEW" ? (
                <ERPEmptyState
                  title="Engineering review is being created"
                  description="Refresh the workspace. The controlled feasibility review will appear here once initialized."
                />
              ) : (
                <ERPEmptyState
                  title="Not sent to engineering"
                  description="Complete the customer scope, requirements, and item lines, then use Send to engineering."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        {hasPermission(user, "crm.quotation.view") ? <TabsContent value="quotations" className="mt-4"><Card><CardHeader className="flex-row items-start justify-between"><div><CardTitle>Quotation trail</CardTitle><CardDescription>Commercial offers connected to this enquiry and its approved estimate.</CardDescription></div><Link to="/app/crm/quotations"><Button size="sm" variant="outline">Quotation register</Button></Link></CardHeader><CardContent>{quotations.isPending ? <ERPLoadingState rows={4} /> : !quotations.data?.results.length ? <ERPEmptyState title="No quotation yet" description="Create a standard quotation after the current commercial estimate is approved." /> : <div className="divide-y">{quotations.data.results.map((quotation) => <Link key={quotation.id} to={`/app/crm/quotations/${quotation.id}`} className="flex items-center gap-3 py-3 first:pt-0 hover:text-primary"><FileText /><div className="min-w-0 flex-1"><p className="font-medium">{quotation.quotation_number} · Rev {quotation.current_revision.revision_number}</p><p className="text-xs text-muted-foreground">{quotation.current_revision.currency_code} {Number(quotation.current_revision.grand_total).toLocaleString("en-IN")} · {quotation.path_label}</p></div><ERPStatusBadge value={quotation.status} /></Link>)}</div>}</CardContent></Card></TabsContent> : null}
        <TabsContent value="activities" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Activities</CardTitle>
                <CardDescription>
                  RFQ-specific conversations and follow-up commitments.
                </CardDescription>
              </div>
              {hasPermission(user, "crm.activity.create") ? (
                <Button
                  size="sm"
                  onClick={() => setPanel({ kind: "activity" })}
                >
                  <Plus data-icon="inline-start" />
                  Record activity
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {workspace.activities.length ? (
                <div className="divide-y">
                  {workspace.activities.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex items-start gap-3 py-3 first:pt-0"
                    >
                      <Activity className="text-primary" />
                      <div className="min-w-0 flex-1">
                        <p className="font-medium">{activity.subject}</p>
                        <p className="text-xs text-muted-foreground">
                          {activity.activity_type.replaceAll("_", " ")} ·{" "}
                          {formatDateTime(activity.activity_date)} ·{" "}
                          {activity.created_by_name}
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {activity.description}
                        </p>
                      </div>
                      <ERPStatusBadge value={activity.status} />
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No activities recorded"
                  description="Log calls, meetings, clarifications, and next actions against this enquiry."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Linked documents</CardTitle>
              <CardDescription>
                Customer RFQs, specifications, drawings, and supporting evidence
                from the shared document service.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {workspace.documents.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {workspace.documents.map((document) => (
                    <Link
                      key={document.id}
                      to={`/app/documents/${document.id}`}
                      className="flex items-center gap-3 rounded-lg border p-4 hover:border-primary/50"
                    >
                      <FileText className="text-primary" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{document.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {document.document_number} · Version{" "}
                          {document.current_version?.version_number ?? "—"} ·{" "}
                          {formatBytes(document.current_version?.size_bytes)}
                        </p>
                      </div>
                      <ERPStatusBadge value={document.status} />
                    </Link>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No linked documents"
                  description="Use the shared Documents workspace to upload and link the customer RFQ or specification to this enquiry."
                  action={
                    hasPermission(user, "documents.document.upload") ? (
                      <Button
                        variant="outline"
                        onClick={() => navigate("/app/documents")}
                      >
                        <FileText data-icon="inline-start" />
                        Open documents
                      </Button>
                    ) : undefined
                  }
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Enquiry history</CardTitle>
              <CardDescription>
                Audit-backed stage changes and commercial interactions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {workspace.timeline.length ? (
                <ol className="relative ml-3 border-l">
                  {workspace.timeline.map((item, index) => (
                    <li
                      key={`${item.occurred_at}-${index}`}
                      className="ml-6 pb-6 last:pb-0"
                    >
                      <CircleDot className="absolute -left-2.5 mt-0.5 rounded-full bg-background text-primary" />
                      <p className="font-medium">{item.summary}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(item.occurred_at)}
                        {item.actor_name ? ` · ${item.actor_name}` : ""}
                      </p>
                    </li>
                  ))}
                </ol>
              ) : (
                <ERPEmptyState
                  title="No history yet"
                  description="Business changes and RFQ activities will appear here."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      <Sheet
        open={Boolean(panel)}
        onOpenChange={(open) => {
          if (!open) setPanel(null);
        }}
      >
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>{panelTitle}</SheetTitle>
            <SheetDescription>
              All changes are validated against the enquiry scope and recorded
              in its audit history.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {panel?.kind === "edit" ? (
              <EnquiryForm
                enquiry={enquiry}
                onSaved={() => {
                  refresh();
                  setPanel(null);
                }}
              />
            ) : panel?.kind === "requirement" ? (
              <RequirementForm
                enquiryId={enquiry.id}
                requirement={panel.record}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "item" ? (
              <ItemForm
                enquiryId={enquiry.id}
                item={panel.record}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "activity" ? (
              customerQuery.data ? (
                <ActivityForm
                  customer={customerQuery.data}
                  initialEnquiryId={enquiry.id}
                  onSaved={() => setPanel(null)}
                />
              ) : (
                <ERPLoadingState rows={5} />
              )
            ) : panel?.kind === "assign" ? (
              <div className="flex flex-col gap-4">
                <Field>
                  <FieldLabel htmlFor="assign-salesperson">
                    Responsible salesperson
                  </FieldLabel>
                  <NativeSelect
                    id="assign-salesperson"
                    className="w-full"
                    value={assignedTo}
                    onChange={(event) => setAssignedTo(event.target.value)}
                  >
                    <NativeSelectOption value="">
                      Select owner
                    </NativeSelectOption>
                    {employees.data?.results.map((employee) => (
                      <NativeSelectOption key={employee.id} value={employee.id}>
                        {employee.employee_code} · {employee.display_name}
                      </NativeSelectOption>
                    ))}
                  </NativeSelect>
                </Field>
                {assign.error ? (
                  <Alert variant="destructive">
                    <AlertTitle>Could not reassign</AlertTitle>
                    <AlertDescription>{assign.error.message}</AlertDescription>
                  </Alert>
                ) : null}
                <Button
                  disabled={!assignedTo || assign.isPending}
                  onClick={() => assign.mutate()}
                >
                  Assign enquiry
                </Button>
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
      <Dialog
        open={Boolean(closeAction)}
        onOpenChange={(open) => {
          if (!open) setCloseAction(null);
        }}
      >
        <DialogContent className="axis-erp">
          <DialogHeader>
            <DialogTitle>
              {closeAction === "mark-lost"
                ? "Mark this enquiry as lost?"
                : "Cancel this enquiry?"}
            </DialogTitle>
            <DialogDescription>
              This explicit lifecycle action closes the enquiry and is
              permanently audit recorded.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <Field>
              <FieldLabel htmlFor="close-reason">Reason</FieldLabel>
              <Textarea
                id="close-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </Field>
            {closeAction === "mark-lost" ? (
              <>
                <Field>
                  <FieldLabel htmlFor="competitor">Competitor</FieldLabel>
                  <Textarea
                    id="competitor"
                    value={competitor}
                    onChange={(event) => setCompetitor(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="customer-feedback">
                    Customer feedback
                  </FieldLabel>
                  <Textarea
                    id="customer-feedback"
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                  />
                </Field>
              </>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseAction(null)}>
              Keep enquiry open
            </Button>
            <Button
              variant="destructive"
              disabled={!reason.trim() || command.isPending}
              onClick={runClose}
            >
              Confirm close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
