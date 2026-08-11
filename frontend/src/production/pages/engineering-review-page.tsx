import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileText,
  MessageSquareText,
  Play,
  Plus,
  RefreshCcw,
  Send,
  UserRoundCog,
  XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  AssignEngineerForm,
  ClarificationForm,
  ClarificationResponseForm,
  EngineeringAssessmentForm,
  ReviewDecisionForm,
} from "@/production/components/engineering-forms";
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
  EngineeringClarification,
  EngineeringReview,
  EngineeringWorkspace,
} from "@/production/lib/crm-types";

type Panel =
  | { kind: "assign" }
  | { kind: "clarify" }
  | { kind: "respond"; clarification: EngineeringClarification }
  | { kind: "complete" }
  | { kind: "not-feasible" }
  | null;

function InfoBlock({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-1 text-sm leading-6">{value || "—"}</div>
    </div>
  );
}

function ReadyGate({ review }: { review: EngineeringReview }) {
  const checks = [
    {
      label: "Engineering result",
      pass: review.status === "FEASIBLE",
      detail: review.result || "Not completed",
    },
    {
      label: "Clarifications closed",
      pass: review.open_clarifications === 0,
      detail: `${review.open_clarifications} unresolved`,
    },
    {
      label: "Approval",
      pass:
        review.approval.status === "NOT_REQUIRED" ||
        review.approval.status === "APPROVED",
      detail: review.approval.status.replaceAll("_", " "),
    },
  ];
  return (
    <Card
      className={
        review.ready_for_estimation
          ? "border-status-success/40"
          : "border-primary/25"
      }
    >
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>Ready for Estimation gate</CardTitle>
            <CardDescription>
              Final Phase 2 milestone; no Estimate is created here.
            </CardDescription>
          </div>
          <ERPStatusBadge
            value={review.ready_for_estimation ? "SUCCESS" : "PENDING"}
            label={
              review.ready_for_estimation ? "READY FOR ESTIMATION" : "GATED"
            }
          />
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        {checks.map((check) => (
          <div
            key={check.label}
            className="flex gap-3 rounded-md border bg-muted/20 p-3"
          >
            {check.pass ? (
              <CheckCircle2 className="text-status-success" />
            ) : (
              <Clock3 className="text-status-warning" />
            )}
            <div>
              <p className="font-medium">{check.label}</p>
              <p className="text-xs text-muted-foreground">{check.detail}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function EngineeringReviewPage() {
  const { reviewId = "" } = useParams();
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [panel, setPanel] = useState<Panel>(null);
  const [showReassess, setShowReassess] = useState(false);
  const [reassessReason, setReassessReason] = useState("");
  const query = useQuery({
    queryKey: ["engineering-workspace", reviewId],
    queryFn: () =>
      apiGet<EngineeringWorkspace>(
        `/engineering-reviews/${reviewId}/workspace/`,
      ),
  });
  const revisions = useQuery({
    queryKey: ["engineering-revisions", reviewId],
    queryFn: () =>
      apiGet<EngineeringReview[]>(
        `/engineering-reviews/${reviewId}/revisions/`,
      ),
    enabled: Boolean(query.data),
  });
  const refresh = () => {
    queryClient.invalidateQueries({
      queryKey: ["engineering-workspace", reviewId],
    });
    queryClient.invalidateQueries({ queryKey: ["engineering-reviews"] });
    queryClient.invalidateQueries({
      queryKey: ["engineering-revisions", reviewId],
    });
  };
  const command = useMutation({
    mutationFn: ({
      path,
      payload = {},
    }: {
      path: string;
      payload?: Record<string, unknown>;
    }) => apiPost<EngineeringReview>(path, payload),
    onSuccess: (review, variables) => {
      refresh();
      toast.success(
        variables.path.endsWith("/start/")
          ? "Engineering review started."
          : "Review updated.",
      );
      if (review.id && review.id !== reviewId)
        navigate(`/app/crm/engineering/${review.id}`, { replace: true });
    },
  });
  const closeClarification = useMutation({
    mutationFn: (id: string) =>
      apiPost(`/engineering-clarifications/${id}/close/`, {
        closure_comment: "Response accepted by engineering.",
      }),
    onSuccess: () => {
      refresh();
      toast.success("Clarification closed.");
    },
  });
  if (!hasPermission(user, "engineering.feasibility.view"))
    return (
      <ERPEmptyState
        title="Access restricted"
        description="You do not have permission to view this engineering review."
      />
    );
  if (query.isPending) return <ERPLoadingState rows={11} />;
  if (query.isError)
    return (
      <ERPErrorState
        title="Engineering review could not be opened"
        message={query.error.message}
      />
    );
  const workspace = query.data;
  const review = workspace.review;
  const enquiry = workspace.enquiry;
  const active = ["IN_REVIEW", "CLARIFICATION_REQUIRED"].includes(
    review.status,
  );
  const completed = [
    "FEASIBLE",
    "NOT_FEASIBLE",
    "SUPERSEDED",
    "CANCELLED",
  ].includes(review.status);
  const canEdit = hasPermission(user, "engineering.feasibility.edit") && active;
  const panelTitle =
    panel?.kind === "assign"
      ? "Assign engineering review"
      : panel?.kind === "clarify"
        ? "Request clarification"
        : panel?.kind === "respond"
          ? "Respond to clarification"
          : panel?.kind === "not-feasible"
            ? "Record not feasible decision"
            : "Complete engineering feasibility";
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <Button
        variant="ghost"
        className="w-fit"
        onClick={() => navigate("/app/crm/engineering")}
      >
        <ArrowLeft data-icon="inline-start" />
        Engineering queue
      </Button>
      <ERPPageHeader
        eyebrow={`Engineering feasibility · Revision ${review.revision_number}`}
        title={review.enquiry_subject}
        description={`${review.enquiry_number} · ${review.customer_name} · Current controlled technical review`}
        actions={
          <>
            <ERPStatusBadge
              value={review.status}
              label={review.result || undefined}
            />
            {hasPermission(user, "engineering.feasibility.assign") &&
            !completed ? (
              <Button
                variant="outline"
                onClick={() => setPanel({ kind: "assign" })}
              >
                <UserRoundCog data-icon="inline-start" />
                Assign
              </Button>
            ) : null}
            {review.status === "PENDING" &&
            hasPermission(user, "engineering.feasibility.start") ? (
              <Button
                disabled={!review.assigned_engineer || command.isPending}
                onClick={() =>
                  command.mutate({
                    path: `/engineering-reviews/${review.id}/start/`,
                  })
                }
              >
                <Play data-icon="inline-start" />
                Start review
              </Button>
            ) : null}
          </>
        }
      />
      {command.error ? (
        <ERPErrorState
          title="Review command failed"
          message={command.error.message}
        />
      ) : null}
      <Card>
        <CardContent className="grid gap-5 p-5 sm:grid-cols-2 xl:grid-cols-6">
          <InfoBlock
            label="Customer"
            value={
              <Link
                to={`/app/crm/customers/${review.customer_id}`}
                className="font-medium hover:text-primary"
              >
                {review.customer_name}
                <span className="block text-xs text-muted-foreground">
                  {review.customer_code}
                </span>
              </Link>
            }
          />
          <InfoBlock
            label="Enquiry"
            value={
              <Link
                to={`/app/crm/enquiries/${review.enquiry}`}
                className="font-medium hover:text-primary"
              >
                {review.enquiry_number}
              </Link>
            }
          />
          <InfoBlock
            label="Engineer"
            value={review.assigned_engineer_name || "Unassigned"}
          />
          <InfoBlock label="Sales owner" value={review.sales_owner_name} />
          <InfoBlock
            label="Priority / due"
            value={
              <>
                <ERPStatusBadge value={review.priority} />
                <span className="ml-2">{review.due_date || "No due date"}</span>
              </>
            }
          />
          <InfoBlock
            label="Review timing"
            value={
              review.completed_at
                ? `Completed ${formatDateTime(review.completed_at)}`
                : review.started_at
                  ? `Started ${formatDateTime(review.started_at)}`
                  : "Not started"
            }
          />
        </CardContent>
      </Card>
      <ReadyGate review={review} />
      <div className="flex flex-wrap gap-2">
        {active &&
        hasPermission(user, "engineering.feasibility.request_clarification") ? (
          <Button
            variant="outline"
            onClick={() => setPanel({ kind: "clarify" })}
          >
            <MessageSquareText data-icon="inline-start" />
            Request clarification
          </Button>
        ) : null}
        {review.status === "IN_REVIEW" &&
        hasPermission(user, "engineering.feasibility.complete") ? (
          <Button onClick={() => setPanel({ kind: "complete" })}>
            <CheckCircle2 data-icon="inline-start" />
            Complete feasible
          </Button>
        ) : null}
        {review.status === "IN_REVIEW" &&
        hasPermission(user, "engineering.feasibility.mark_not_feasible") ? (
          <Button
            variant="destructive"
            onClick={() => setPanel({ kind: "not-feasible" })}
          >
            <XCircle data-icon="inline-start" />
            Not feasible
          </Button>
        ) : null}
        {["FEASIBLE", "NOT_FEASIBLE"].includes(review.status) &&
        review.is_current &&
        hasPermission(user, "engineering.feasibility.reassess") ? (
          <Button variant="outline" onClick={() => setShowReassess(true)}>
            <RefreshCcw data-icon="inline-start" />
            Reassess
          </Button>
        ) : null}
        {review.approval.request_id ? (
          <Button
            variant="outline"
            onClick={() =>
              navigate(`/app/approvals/${review.approval.request_id}`)
            }
          >
            <Send data-icon="inline-start" />
            Open approval
          </Button>
        ) : null}
      </div>
      <Tabs defaultValue="assessment">
        <div className="overflow-x-auto pb-1">
          <TabsList className="h-auto min-w-max justify-start">
            <TabsTrigger value="assessment">Assessment</TabsTrigger>
            <TabsTrigger value="clarifications">
              Clarifications{" "}
              <Badge variant="outline">{review.open_clarifications}</Badge>
            </TabsTrigger>
            <TabsTrigger value="scope">Customer scope</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="approvals">Approvals</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="revisions">Revisions</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="assessment" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Engineering assessment</CardTitle>
              <CardDescription>
                {canEdit
                  ? "Record the technical basis, make/buy/test considerations, and preliminary effort."
                  : "Controlled read-only conclusion for this revision."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {canEdit ? (
                <EngineeringAssessmentForm review={review} onSaved={refresh} />
              ) : (
                <div className="grid gap-5 md:grid-cols-2">
                  <InfoBlock
                    label="Technical summary"
                    value={review.technical_summary}
                  />
                  <InfoBlock
                    label="Feasibility notes"
                    value={review.feasibility_notes}
                  />
                  <InfoBlock label="Assumptions" value={review.assumptions} />
                  <InfoBlock label="Exclusions" value={review.exclusions} />
                  <InfoBlock label="Constraints" value={review.constraints} />
                  <InfoBlock label="Risks" value={review.risks} />
                  <InfoBlock
                    label="Special materials"
                    value={review.special_materials}
                  />
                  <InfoBlock
                    label="Outsourced processes"
                    value={review.outsourced_processes}
                  />
                  <InfoBlock
                    label="Tooling / testing"
                    value={[
                      review.tooling_requirements,
                      review.testing_requirements,
                    ]
                      .filter(Boolean)
                      .join(" / ")}
                  />
                  <InfoBlock
                    label="Drawing / BOM / routing"
                    value={[
                      review.preliminary_drawing_notes,
                      review.preliminary_bom_notes,
                      review.preliminary_routing_notes,
                    ]
                      .filter(Boolean)
                      .join(" / ")}
                  />
                  <InfoBlock
                    label="Indicative effort"
                    value={`${review.engineering_hours ?? "—"} engineering h · ${review.manufacturing_hours ?? "—"} manufacturing h · ${review.lead_time_days ?? "—"} days`}
                  />
                  <InfoBlock
                    label="Completion comment"
                    value={review.completion_comment}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="clarifications" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Structured clarifications</CardTitle>
                <CardDescription>
                  Questions remain open until a response is explicitly accepted
                  and closed.
                </CardDescription>
              </div>
              {active &&
              hasPermission(
                user,
                "engineering.feasibility.request_clarification",
              ) ? (
                <Button size="sm" onClick={() => setPanel({ kind: "clarify" })}>
                  <Plus data-icon="inline-start" />
                  New clarification
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {review.clarifications.length ? (
                <div className="flex flex-col gap-3">
                  {review.clarifications.map((clarification) => (
                    <div
                      key={clarification.id}
                      className={`rounded-lg border p-4 ${clarification.is_overdue ? "border-destructive/50" : "bg-muted/20"}`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <ERPStatusBadge value={clarification.status} />
                            {clarification.is_overdue ? (
                              <Badge variant="destructive">Overdue</Badge>
                            ) : null}
                          </div>
                          <p className="mt-3 font-medium">
                            {clarification.subject}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {clarification.question}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {clarification.status === "OPEN" &&
                          hasPermission(
                            user,
                            "engineering.feasibility.respond_clarification",
                          ) ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                setPanel({ kind: "respond", clarification })
                              }
                            >
                              Respond
                            </Button>
                          ) : null}
                          {clarification.status === "RESPONDED" &&
                          hasPermission(
                            user,
                            "engineering.feasibility.edit",
                          ) ? (
                            <Button
                              size="sm"
                              onClick={() =>
                                closeClarification.mutate(clarification.id)
                              }
                            >
                              Accept & close
                            </Button>
                          ) : null}
                        </div>
                      </div>
                      <div className="mt-4 grid gap-3 border-t pt-3 sm:grid-cols-3">
                        <InfoBlock
                          label="Assigned to"
                          value={clarification.assigned_to_name}
                        />
                        <InfoBlock
                          label="Due"
                          value={formatDateTime(clarification.due_at)}
                        />
                        <InfoBlock
                          label="Requested by"
                          value={`${clarification.requested_by_name} · ${formatDateTime(clarification.requested_at)}`}
                        />
                      </div>
                      {clarification.response ? (
                        <div className="mt-3 rounded-md border bg-background p-3">
                          <p className="text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
                            Response by {clarification.responded_by_name}
                          </p>
                          <p className="mt-2 text-sm">
                            {clarification.response}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No clarifications"
                  description="The review has no structured clarification requests."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="scope" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Requirements</CardTitle>
                <CardDescription>
                  Commercial scope passed into engineering.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {enquiry.requirements.length ? (
                  <div className="flex flex-col gap-3">
                    {enquiry.requirements.map((requirement) => (
                      <div
                        key={requirement.id}
                        className="rounded-md border p-3"
                      >
                        <div className="flex gap-2">
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
                        <p className="mt-2 font-medium">{requirement.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {requirement.description}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <ERPEmptyState
                    title="No requirements"
                    description="No structured requirements were supplied."
                  />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>RFQ item lines</CardTitle>
                <CardDescription>
                  Assemblies and deliverables under review.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {enquiry.items.length ? (
                  <div className="flex flex-col gap-3">
                    {enquiry.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex gap-3 rounded-md border p-3"
                      >
                        <span className="font-mono text-primary">
                          {String(item.line_number).padStart(2, "0")}
                        </span>
                        <div>
                          <p className="font-medium">{item.description}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.quantity} {item.uom_code} ·{" "}
                            {item.technical_specification ||
                              "No detailed specification"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <ERPEmptyState
                    title="No item lines"
                    description="No structured RFQ item lines were supplied."
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Engineering documents</CardTitle>
              <CardDescription>
                Enquiry and review documents from the shared version-controlled
                service.
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
                    </Link>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No linked documents"
                  description="Link RFQs, drawings, specifications, or calculations through the shared Documents workspace."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="approvals" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Approval gate</CardTitle>
              <CardDescription>
                The generic approval engine is used only when an active matching
                workflow is configured.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {review.approval.required ? (
                workspace.approvals.length ? (
                  <div className="flex flex-col gap-3">
                    {workspace.approvals.map((approval) => (
                      <button
                        key={approval.id}
                        type="button"
                        className="flex items-center justify-between gap-3 rounded-md border p-4 text-left hover:border-primary/50"
                        onClick={() =>
                          navigate(`/app/approvals/${approval.id}`)
                        }
                      >
                        <div>
                          <p className="font-medium">
                            {approval.workflow_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {approval.current_step_name || "Workflow complete"}{" "}
                            · Requested {formatDateTime(approval.requested_at)}
                          </p>
                        </div>
                        <ERPStatusBadge
                          value={approval.status}
                          label={approval.status_label}
                        />
                      </button>
                    ))}
                  </div>
                ) : (
                  <ERPErrorState
                    title="Approval not submitted"
                    message="A matching approval workflow exists, but no approval request has been created."
                  />
                )
              ) : (
                <ERPEmptyState
                  title="No approval required"
                  description="No active approval workflow matches this engineering review."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Engineering audit history</CardTitle>
              <CardDescription>
                Immutable business events for this review and its
                clarifications.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {workspace.timeline.length ? (
                <ol className="relative ml-3 border-l">
                  {workspace.timeline.map((event) => (
                    <li key={event.id} className="ml-6 pb-6 last:pb-0">
                      <span className="absolute -left-2 mt-1.5 size-3 rounded-full border-2 border-background bg-primary" />
                      <p className="font-medium">{event.summary}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(event.occurred_at)} · {event.actor_name}
                      </p>
                    </li>
                  ))}
                </ol>
              ) : (
                <ERPEmptyState
                  title="No engineering history"
                  description="Review commands will create immutable audit events here."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="revisions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Revision history</CardTitle>
              <CardDescription>
                Completed reviews are preserved; reassessment creates a new
                current revision.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {revisions.isPending ? (
                <ERPLoadingState rows={3} />
              ) : revisions.data?.length ? (
                <div className="flex flex-col gap-3">
                  {revisions.data.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() =>
                        navigate(`/app/crm/engineering/${item.id}`)
                      }
                      className={`flex items-center justify-between gap-3 rounded-md border p-4 text-left ${item.id === review.id ? "border-primary bg-primary/10" : "hover:border-primary/40"}`}
                    >
                      <div>
                        <p className="font-medium">
                          Revision {item.revision_number}{" "}
                          {item.is_current ? "· Current" : ""}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {item.completed_at
                            ? `Completed ${formatDateTime(item.completed_at)} by ${item.completed_by_name}`
                            : `Created ${formatDateTime(item.created_at)}`}
                        </p>
                      </div>
                      <ERPStatusBadge
                        value={item.status}
                        label={item.result || undefined}
                      />
                    </button>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No revision history"
                  description="This is the first engineering review revision."
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
              Commands are permission checked, transaction safe, and audit
              recorded.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {panel?.kind === "assign" ? (
              <AssignEngineerForm
                review={review}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "clarify" ? (
              <ClarificationForm
                review={review}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "respond" ? (
              <ClarificationResponseForm
                clarification={panel.clarification}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "complete" ? (
              <ReviewDecisionForm
                review={review}
                onSaved={() => setPanel(null)}
              />
            ) : panel?.kind === "not-feasible" ? (
              <ReviewDecisionForm
                review={review}
                notFeasible
                onSaved={() => setPanel(null)}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
      <Dialog open={showReassess} onOpenChange={setShowReassess}>
        <DialogContent className="axis-erp">
          <DialogHeader>
            <DialogTitle>Create a new engineering revision?</DialogTitle>
            <DialogDescription>
              The current completed review will be preserved and marked
              superseded. A new pending revision becomes current.
            </DialogDescription>
          </DialogHeader>
          <Field>
            <FieldLabel htmlFor="reassess-reason">
              Reason for reassessment
            </FieldLabel>
            <Textarea
              id="reassess-reason"
              value={reassessReason}
              onChange={(event) => setReassessReason(event.target.value)}
            />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReassess(false)}>
              Cancel
            </Button>
            <Button
              disabled={!reassessReason.trim() || command.isPending}
              onClick={() =>
                command.mutate({
                  path: `/engineering-reviews/${review.id}/reassess/`,
                  payload: { reason: reassessReason },
                })
              }
            >
              <RefreshCcw data-icon="inline-start" />
              Create revision {review.revision_number + 1}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
