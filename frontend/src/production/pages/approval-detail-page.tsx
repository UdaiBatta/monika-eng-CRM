import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Download,
  FileText,
  RotateCcw,
  Send,
  UserRoundCog,
  X,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiDownload, apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  ApprovalAssignment,
  ApprovalRequest,
  ERPDocument,
  FoundationRecord,
  Paginated,
} from "@/production/lib/types";
import { cn } from "@/lib/utils";
import {
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPPermissionState,
  ERPStatusBadge,
  formatBytes,
  formatDateTime,
} from "@/production/components/shared";

type Decision = "approve" | "reject" | "return" | "cancel";

const decisionCopy: Record<
  Decision,
  { title: string; description: string; action: string }
> = {
  approve: {
    title: "Approve this request?",
    description:
      "Your decision is recorded permanently and may complete or advance the workflow.",
    action: "Approve",
  },
  reject: {
    title: "Reject this request?",
    description: "Explain why this record cannot be approved.",
    action: "Reject",
  },
  return: {
    title: "Return this request for changes?",
    description:
      "Explain what the requester should change before resubmission.",
    action: "Return for changes",
  },
  cancel: {
    title: "Cancel this approval request?",
    description: "The current approval assignments will be closed.",
    action: "Cancel request",
  },
};

type ReassignmentEmployee = FoundationRecord & {
  user: string | null;
  display_name: string;
  employee_code: string;
  employment_status: string;
};

function ReassignDialog({
  request,
  assignment,
  onClose,
}: {
  request: ApprovalRequest;
  assignment: ApprovalAssignment | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [approverId, setApproverId] = useState("");
  const [reason, setReason] = useState("");
  const employees = useQuery({
    queryKey: ["employees", "approval-reassignment", request.company],
    queryFn: () =>
      apiGet<Paginated<ReassignmentEmployee>>(
        `/employees/?company=${request.company}&employment_status=ACTIVE&page_size=100`,
      ),
    enabled: Boolean(assignment),
  });
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<ApprovalRequest>(`/approvals/requests/${request.id}/reassign/`, {
        assignment_id: assignment?.id,
        approver_id: approverId,
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", request.id] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("Approval reassigned.");
      onClose();
    },
  });
  if (!assignment) return null;
  const choices =
    employees.data?.results.filter(
      (employee) => employee.user && employee.user !== assignment.approver,
    ) ?? [];
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="axis-erp sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Reassign this approval?</DialogTitle>
          <DialogDescription>
            {assignment.approver_name} remains in the permanent history. Choose
            an active, authorized employee to take over.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup className="my-4">
          <Field>
            <FieldLabel htmlFor="replacement-approver">New approver</FieldLabel>
            <NativeSelect
              id="replacement-approver"
              className="w-full"
              value={approverId}
              onChange={(event) => setApproverId(event.target.value)}
            >
              <NativeSelectOption value="">Choose employee</NativeSelectOption>
              {choices.map((employee) => (
                <NativeSelectOption key={employee.id} value={employee.user!}>
                  {employee.display_name} · {employee.employee_code}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="reassignment-reason">Reason</FieldLabel>
            <Textarea
              id="reassignment-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="For example: employee is on leave or has left the company"
              required
            />
          </Field>
          {mutation.isError ? (
            <FieldError>{mutation.error.message}</FieldError>
          ) : null}
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!approverId || !reason.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <UserRoundCog data-icon="inline-start" />
            )}
            Reassign approval
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ApprovalActionDialog({
  request,
  decision,
  onClose,
}: {
  request: ApprovalRequest;
  decision: Decision | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<ApprovalRequest>(
        `/approvals/requests/${request.id}/${decision}/`,
        { comment },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", request.id] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success(
        decision === "approve" ? "Approval recorded." : "Decision recorded.",
      );
      onClose();
    },
  });
  if (!decision) return null;
  const copy = decisionCopy[decision];
  const commentRequired = decision === "reject" || decision === "return";
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="axis-erp">
        <DialogHeader>
          <DialogTitle>{copy.title}</DialogTitle>
          <DialogDescription>{copy.description}</DialogDescription>
        </DialogHeader>
        <div className="rounded-lg border bg-muted/30 p-3">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            You are deciding
          </p>
          <p className="mt-1 font-semibold">{request.entity_reference}</p>
          <p className="text-sm text-muted-foreground">
            {request.workflow_name}
          </p>
        </div>
        <Field>
          <FieldLabel htmlFor="decision-comment">
            {commentRequired ? "Comment" : "Optional comment"}
          </FieldLabel>
          <Textarea
            id="decision-comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder={
              decision === "approve"
                ? "Add a short note if helpful"
                : "Explain your decision"
            }
            required={commentRequired}
          />
        </Field>
        {mutation.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Decision not recorded</AlertTitle>
            <AlertDescription>{mutation.error.message}</AlertDescription>
          </Alert>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Keep open
          </Button>
          <Button
            variant={
              decision === "reject" || decision === "cancel"
                ? "destructive"
                : "default"
            }
            disabled={
              mutation.isPending || (commentRequired && !comment.trim())
            }
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : decision === "approve" ? (
              <Check data-icon="inline-start" />
            ) : decision === "return" ? (
              <RotateCcw data-icon="inline-start" />
            ) : (
              <X data-icon="inline-start" />
            )}
            {copy.action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ApprovalDetailPage() {
  const { approvalId = "" } = useParams();
  const { data: user } = useCurrentUser();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [reassigning, setReassigning] = useState<ApprovalAssignment | null>(
    null,
  );
  const canView = hasPermission(user, "approvals.request.view");
  const query = useQuery({
    queryKey: ["approval", approvalId],
    queryFn: () =>
      apiGet<ApprovalRequest>(`/approvals/requests/${approvalId}/`),
    enabled: canView,
  });
  const documents = useQuery({
    queryKey: ["approval-documents", approvalId],
    queryFn: () =>
      apiGet<ERPDocument[]>(
        `/approvals/requests/${approvalId}/supporting-documents/`,
      ),
    enabled: canView,
  });
  const download = useMutation({
    mutationFn: (document: ERPDocument) =>
      apiDownload(
        `/documents/${document.id}/download/`,
        document.current_version?.safe_display_filename ?? document.title,
      ),
    onError: (error) => toast.error(error.message),
  });
  if (!canView) return <ERPPermissionState />;
  if (query.isPending) return <ERPLoadingState rows={8} />;
  if (query.isError)
    return query.error instanceof ApiError && query.error.status === 403 ? (
      <ERPPermissionState />
    ) : (
      <ERPErrorState message={query.error.message} />
    );
  const request = query.data;
  const currentStep = request.steps.find(
    (step) => step.step_name === request.current_step_name,
  );
  const assignedToMe = currentStep?.assignments.some(
    (assignment) =>
      assignment.approver === user?.id && assignment.status === "PENDING",
  );
  const canApprove =
    assignedToMe && hasPermission(user, "approvals.request.approve");
  const canReject =
    assignedToMe && hasPermission(user, "approvals.request.reject");
  const canReturn =
    assignedToMe && hasPermission(user, "approvals.request.return");
  const canCancel =
    request.requested_by === user?.id &&
    ["PENDING", "IN_PROGRESS"].includes(request.status) &&
    hasPermission(user, "approvals.request.cancel");
  const canReassign = hasPermission(user, "approvals.workflow.manage");
  const nextStep = currentStep
    ? request.steps.find((step) => step.sequence > currentStep.sequence)
    : undefined;
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <Button
        variant="ghost"
        className="w-fit"
        render={<Link to="/app/approvals" />}
        nativeButton={false}
      >
        <ArrowLeft data-icon="inline-start" />
        Back to my approvals
      </Button>
      <ERPPageHeader
        eyebrow={`${request.entity_type.replaceAll("_", " ")} approval · Workflow version ${request.workflow_version_number}`}
        title={request.entity_reference}
        description={
          request.submission_comment || "No submission comment was provided."
        }
        actions={
          <ERPStatusBadge value={request.status} label={request.status_label} />
        }
      />
      {assignedToMe ? (
        <Alert className="border-amber-500/30 bg-amber-500/5">
          <Send />
          <AlertTitle>Needs your approval</AlertTitle>
          <AlertDescription>
            Review the request and supporting documents before recording a
            decision.
          </AlertDescription>
        </Alert>
      ) : null}
      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>Approval context</CardTitle>
            <CardDescription>What you are approving and why</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Record
              </p>
              <p className="mt-1 font-semibold">{request.entity_reference}</p>
              <p className="text-sm capitalize text-muted-foreground">
                {request.entity_type.replaceAll("_", " ")}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Submitted by
              </p>
              <p className="mt-1 font-semibold">{request.requested_by_name}</p>
              <p className="text-sm text-muted-foreground">
                {formatDateTime(request.requested_at)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Current step
              </p>
              <p className="mt-1 font-semibold">
                {request.current_step_name || "Workflow complete"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                What happens next
              </p>
              <p className="mt-1 font-semibold">
                {nextStep
                  ? nextStep.step_name
                  : currentStep
                    ? "This is the final step"
                    : "No further action"}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Supporting documents</CardTitle>
            <CardDescription>
              Files linked through the shared document service
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {documents.isPending ? (
              <ERPLoadingState rows={2} />
            ) : documents.data?.length ? (
              documents.data.map((document) => (
                <div
                  key={document.id}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <span className="grid size-9 place-items-center rounded-md bg-primary/10 text-primary">
                    <FileText />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{document.title}</p>
                    <p className="text-xs text-muted-foreground">
                      Version {document.current_version?.version_number} ·{" "}
                      {formatBytes(document.current_version?.size_bytes)}
                    </p>
                  </div>
                  {hasPermission(user, "documents.document.download") ? (
                    <Button
                      aria-label={`Download ${document.title}`}
                      size="icon-sm"
                      variant="ghost"
                      onClick={() => download.mutate(document)}
                    >
                      <Download />
                    </Button>
                  ) : null}
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">
                No supporting documents are linked to this request.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
      <Card>
        <CardHeader>
          <CardTitle>Approval history</CardTitle>
          <CardDescription>
            Permanent workflow and decision record
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="relative ml-3 border-l">
            {request.steps.map((step) => (
              <li key={step.id} className="relative pb-7 pl-7 last:pb-0">
                <span
                  className={cn(
                    "absolute -left-3 grid size-6 place-items-center rounded-full border bg-background",
                    step.status === "APPROVED" &&
                      "border-emerald-600 bg-emerald-50 text-emerald-700",
                  )}
                >
                  {step.status === "APPROVED" ? (
                    <CheckCircle2 className="size-4" />
                  ) : (
                    step.sequence
                  )}
                </span>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{step.step_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {step.opened_at
                        ? `Opened ${formatDateTime(step.opened_at)}`
                        : "Waiting for earlier steps"}
                    </p>
                  </div>
                  <ERPStatusBadge value={step.status} />
                </div>
                <div className="mt-3 space-y-2">
                  {step.assignments.map((assignment) => {
                    const recorded = step.decisions.find(
                      (item) => item.assignment === assignment.id,
                    );
                    return (
                      <div
                        key={assignment.id}
                        className="rounded-md bg-muted/40 p-3 text-sm"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span>{assignment.approver_name}</span>
                          <span className="ml-auto text-muted-foreground">
                            {assignment.status.replaceAll("_", " ")}
                          </span>
                          {canReassign &&
                          step.id === currentStep?.id &&
                          assignment.status === "PENDING" ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setReassigning(assignment)}
                            >
                              <UserRoundCog data-icon="inline-start" />
                              Reassign
                            </Button>
                          ) : null}
                        </div>
                        {recorded ? (
                          <div className="mt-2 border-t pt-2 text-muted-foreground">
                            <p>{recorded.comment || "No comment"}</p>
                            <p className="mt-1 text-xs">
                              {formatDateTime(recorded.decided_at)}
                            </p>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
      {canApprove || canReject || canReturn || canCancel ? (
        <div className="sticky bottom-3 z-10 flex flex-wrap items-center justify-end gap-2 rounded-xl border bg-background/95 p-3 shadow-lg backdrop-blur">
          <span className="mr-auto hidden text-sm text-muted-foreground sm:block">
            Record a clear, deliberate decision
          </span>
          {canCancel ? (
            <Button variant="ghost" onClick={() => setDecision("cancel")}>
              Cancel request
            </Button>
          ) : null}
          {canReturn ? (
            <Button variant="outline" onClick={() => setDecision("return")}>
              <RotateCcw data-icon="inline-start" />
              Return for changes
            </Button>
          ) : null}
          {canReject ? (
            <Button variant="destructive" onClick={() => setDecision("reject")}>
              <X data-icon="inline-start" />
              Reject
            </Button>
          ) : null}
          {canApprove ? (
            <Button onClick={() => setDecision("approve")}>
              <Check data-icon="inline-start" />
              Approve
            </Button>
          ) : null}
        </div>
      ) : null}
      <ApprovalActionDialog
        request={request}
        decision={decision}
        onClose={() => setDecision(null)}
      />
      <ReassignDialog
        request={request}
        assignment={reassigning}
        onClose={() => setReassigning(null)}
      />
    </div>
  );
}
