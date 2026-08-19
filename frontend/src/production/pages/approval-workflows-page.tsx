import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Copy,
  GitBranch,
  Plus,
  Settings2,
  Users,
} from "lucide-react";
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
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPatch, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { FoundationRecord, Paginated } from "@/production/lib/types";
import { cn } from "@/lib/utils";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPPermissionState,
  ERPStatusBadge,
} from "@/production/components/shared";

type WorkflowStep = {
  id: string;
  sequence: number;
  name: string;
  approval_mode: "SINGLE" | "PARALLEL";
  resolver_type: "PERMISSION" | "SPECIFIC_USERS";
  required_permission_code: string;
  specific_users: string[];
  minimum_approvals: number;
  allow_reject: boolean;
  allow_return_for_changes: boolean;
  is_active: boolean;
};

type WorkflowCondition = {
  id: string;
  field: string;
  operator: string;
  value: unknown;
};
type WorkflowVersion = {
  id: string;
  version_number: number;
  status: "DRAFT" | "ACTIVE" | "RETIRED";
  allow_self_approval: boolean;
  steps: WorkflowStep[];
  conditions: WorkflowCondition[];
};
type Workflow = {
  id: string;
  company: string;
  company_name: string;
  code: string;
  name: string;
  description: string;
  entity_type: string;
  is_active: boolean;
  current_version: string | null;
  current_version_number: number | null;
  versions: WorkflowVersion[];
};
type EmployeeOption = FoundationRecord & {
  user: string | null;
  display_name: string;
  employee_code: string;
};

function WorkflowDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [company, setCompany] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const companies = useQuery({
    queryKey: ["workflow-companies"],
    queryFn: () =>
      apiGet<Paginated<FoundationRecord>>(
        "/companies/?is_active=true&page_size=100",
      ),
    enabled: open,
  });
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<Workflow>("/approval-workflows/", {
        company,
        code,
        name,
        description,
        entity_type: "document",
        is_active: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success("Approval workflow created as Draft version 1.");
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp sm:max-w-lg">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>New approval workflow</DialogTitle>
            <DialogDescription>
              Create the definition first, then add ordered steps and activate
              its version.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="my-5">
            <Field>
              <FieldLabel htmlFor="workflow-company">Company</FieldLabel>
              <NativeSelect
                id="workflow-company"
                className="w-full"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                required
              >
                <NativeSelectOption value="">Choose company</NativeSelectOption>
                {companies.data?.results.map((item) => (
                  <NativeSelectOption
                    key={String(item.id)}
                    value={String(item.id)}
                  >
                    {String(item.name)}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="workflow-code">Code</FieldLabel>
              <Input
                id="workflow-code"
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase())}
                placeholder="DRAWING-REVIEW"
                required
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="workflow-name">Name</FieldLabel>
              <Input
                id="workflow-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Drawing review"
                required
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="workflow-description">
                Description
              </FieldLabel>
              <Textarea
                id="workflow-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel>Record type</FieldLabel>
              <Input value="Document" disabled />
              <FieldDescription>
                Phase 1 exposes the registered Document entity only. Future
                modules plug into the same engine.
              </FieldDescription>
            </Field>
          </FieldGroup>
          {mutation.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Workflow not created</AlertTitle>
              <AlertDescription>{mutation.error.message}</AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!company || !code || !name || mutation.isPending}
            >
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Plus data-icon="inline-start" />
              )}
              Create workflow
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function StepDialog({
  workflow,
  version,
  open,
  onOpenChange,
}: {
  workflow: Workflow;
  version: WorkflowVersion;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"SINGLE" | "PARALLEL">("SINGLE");
  const [resolver, setResolver] = useState<"PERMISSION" | "SPECIFIC_USERS">(
    "SPECIFIC_USERS",
  );
  const [permission, setPermission] = useState("");
  const [users, setUsers] = useState<string[]>([]);
  const [minimum, setMinimum] = useState(1);
  const [allowReject, setAllowReject] = useState(true);
  const [allowReturn, setAllowReturn] = useState(true);
  const employees = useQuery({
    queryKey: ["workflow-employees", workflow.company],
    queryFn: () =>
      apiGet<Paginated<EmployeeOption>>(
        `/employees/?company=${workflow.company}&employment_status=ACTIVE&page_size=100`,
      ),
    enabled: open,
  });
  const permissions = useQuery({
    queryKey: ["workflow-permissions"],
    queryFn: () =>
      apiGet<Paginated<FoundationRecord>>("/permissions/?page_size=200"),
    enabled: open && resolver === "PERMISSION",
  });
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<WorkflowStep>("/approval-step-definitions/", {
        workflow_version: version.id,
        sequence: (version.steps.at(-1)?.sequence ?? 0) + 1,
        name,
        approval_mode: mode,
        resolver_type: resolver,
        required_permission_code: resolver === "PERMISSION" ? permission : "",
        specific_users: resolver === "SPECIFIC_USERS" ? users : [],
        scope_logic: "COMPANY",
        minimum_approvals: mode === "SINGLE" ? 1 : minimum,
        allow_reject: allowReject,
        allow_return_for_changes: allowReturn,
        is_active: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success("Approval step added.");
      onOpenChange(false);
    },
  });
  const employeeOptions =
    employees.data?.results.filter((item) => item.user) ?? [];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp sm:max-w-xl">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Add approval step</DialogTitle>
            <DialogDescription>
              Step {version.steps.length + 1} will run after the existing
              ordered steps.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="my-5">
            <Field>
              <FieldLabel htmlFor="step-name">Step name</FieldLabel>
              <Input
                id="step-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Workshop manager review"
                required
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="approval-mode">Approval mode</FieldLabel>
                <NativeSelect
                  id="approval-mode"
                  className="w-full"
                  value={mode}
                  onChange={(event) =>
                    setMode(event.target.value as typeof mode)
                  }
                >
                  <NativeSelectOption value="SINGLE">
                    Any one approver
                  </NativeSelectOption>
                  <NativeSelectOption value="PARALLEL">
                    Parallel approvals
                  </NativeSelectOption>
                </NativeSelect>
              </Field>
              <Field>
                <FieldLabel htmlFor="resolver-type">Approver source</FieldLabel>
                <NativeSelect
                  id="resolver-type"
                  className="w-full"
                  value={resolver}
                  onChange={(event) =>
                    setResolver(event.target.value as typeof resolver)
                  }
                >
                  <NativeSelectOption value="SPECIFIC_USERS">
                    Specific users
                  </NativeSelectOption>
                  <NativeSelectOption value="PERMISSION">
                    Permission-based
                  </NativeSelectOption>
                </NativeSelect>
              </Field>
            </div>
            {resolver === "PERMISSION" ? (
              <Field>
                <FieldLabel htmlFor="step-permission">
                  Required permission
                </FieldLabel>
                <NativeSelect
                  id="step-permission"
                  className="w-full"
                  value={permission}
                  onChange={(event) => setPermission(event.target.value)}
                  required
                >
                  <NativeSelectOption value="">
                    Choose permission
                  </NativeSelectOption>
                  {permissions.data?.results.map((item) => (
                    <NativeSelectOption
                      key={String(item.id)}
                      value={String(item.code)}
                    >
                      {String(item.code)} · {String(item.name)}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
                <FieldDescription>
                  Active employees with this permission in the record company
                  become approvers.
                </FieldDescription>
              </Field>
            ) : (
              <Field>
                <FieldLabel htmlFor="step-users">
                  Specific test/admin approvers
                </FieldLabel>
                <NativeSelect
                  id="step-users"
                  className="w-full"
                  multiple
                  value={users}
                  onChange={(event) =>
                    setUsers(
                      Array.from(
                        event.currentTarget.selectedOptions,
                        (option) => option.value,
                      ),
                    )
                  }
                  required
                >
                  {employeeOptions.map((item) => (
                    <NativeSelectOption key={item.id} value={String(item.user)}>
                      {item.employee_code} · {item.display_name}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
                <FieldDescription>
                  No employee is selected automatically. Hold Ctrl to select
                  multiple approvers.
                </FieldDescription>
              </Field>
            )}
            {mode === "PARALLEL" ? (
              <Field>
                <FieldLabel htmlFor="minimum-approvals">
                  Minimum approvals
                </FieldLabel>
                <Input
                  id="minimum-approvals"
                  type="number"
                  min={1}
                  value={minimum}
                  onChange={(event) => setMinimum(Number(event.target.value))}
                />
              </Field>
            ) : null}
            <Field orientation="horizontal">
              <div className="flex-1">
                <FieldLabel htmlFor="allow-reject">Allow rejection</FieldLabel>
                <FieldDescription>
                  Approvers may close the request as rejected.
                </FieldDescription>
              </div>
              <Switch
                id="allow-reject"
                checked={allowReject}
                onCheckedChange={setAllowReject}
              />
            </Field>
            <Field orientation="horizontal">
              <div className="flex-1">
                <FieldLabel htmlFor="allow-return">
                  Allow return for changes
                </FieldLabel>
                <FieldDescription>
                  Approvers may send the record back with a required comment.
                </FieldDescription>
              </div>
              <Switch
                id="allow-return"
                checked={allowReturn}
                onCheckedChange={setAllowReturn}
              />
            </Field>
          </FieldGroup>
          {mutation.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Step not added</AlertTitle>
              <AlertDescription>{mutation.error.message}</AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={
                !name ||
                mutation.isPending ||
                (resolver === "SPECIFIC_USERS" ? users.length < 1 : !permission)
              }
            >
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Plus data-icon="inline-start" />
              )}
              Add step
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ConditionDialog({
  version,
  open,
  onOpenChange,
}: {
  version: WorkflowVersion;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [field, setField] = useState("status");
  const [operator, setOperator] = useState("EQ");
  const [value, setValue] = useState("ACTIVE");
  const mutation = useMutation({
    mutationFn: () =>
      apiPost("/approval-conditions/", {
        workflow_version: version.id,
        field,
        operator,
        value:
          operator === "IN"
            ? value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean)
            : field === "is_confidential"
              ? value === "true"
              : value,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success("Workflow condition added.");
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp">
        <DialogHeader>
          <DialogTitle>Add workflow condition</DialogTitle>
          <DialogDescription>
            Use an approved business field and a safe comparison. No executable
            expressions are accepted.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="condition-field">Business field</FieldLabel>
            <NativeSelect
              id="condition-field"
              className="w-full"
              value={field}
              onChange={(event) => {
                setField(event.target.value);
                setValue(
                  event.target.value === "is_confidential"
                    ? "false"
                    : event.target.value === "status"
                      ? "ACTIVE"
                      : "",
                );
              }}
            >
              <NativeSelectOption value="status">
                Document status
              </NativeSelectOption>
              <NativeSelectOption value="category_id">
                Document category ID
              </NativeSelectOption>
              <NativeSelectOption value="is_confidential">
                Confidential
              </NativeSelectOption>
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="condition-operator">Comparison</FieldLabel>
            <NativeSelect
              id="condition-operator"
              className="w-full"
              value={operator}
              onChange={(event) => setOperator(event.target.value)}
            >
              {["EQ", "NE", "IN"].map((item) => (
                <NativeSelectOption key={item} value={item}>
                  {item === "EQ"
                    ? "Equals"
                    : item === "NE"
                      ? "Does not equal"
                      : "Is one of"}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="condition-value">Value</FieldLabel>
            {field === "is_confidential" ? (
              <NativeSelect
                id="condition-value"
                className="w-full"
                value={value}
                onChange={(event) => setValue(event.target.value)}
              >
                <NativeSelectOption value="true">Yes</NativeSelectOption>
                <NativeSelectOption value="false">No</NativeSelectOption>
              </NativeSelect>
            ) : (
              <Input
                id="condition-value"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder={
                  operator === "IN"
                    ? "Comma-separated values"
                    : "Comparison value"
                }
              />
            )}
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!value || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            <Plus data-icon="inline-start" />
            Add condition
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ApprovalWorkflowsPage() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const canView = hasPermission(user, "approvals.workflow.view");
  const canManage = hasPermission(user, "approvals.workflow.manage");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const [stepVersion, setStepVersion] = useState<WorkflowVersion | null>(null);
  const [conditionVersion, setConditionVersion] =
    useState<WorkflowVersion | null>(null);
  const query = useQuery({
    queryKey: ["approval-workflows"],
    queryFn: () =>
      apiGet<Paginated<Workflow>>("/approval-workflows/?page_size=100"),
    enabled: canView,
  });
  const selected = useMemo(
    () =>
      query.data?.results.find((item) => item.id === selectedId) ??
      query.data?.results[0],
    [query.data, selectedId],
  );
  const clone = useMutation({
    mutationFn: (workflow: Workflow) =>
      apiPost(`/approval-workflows/${workflow.id}/versions/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success(
        "New draft version created from the current configuration.",
      );
    },
  });
  const activate = useMutation({
    mutationFn: (version: WorkflowVersion) =>
      apiPost(`/approval-workflow-versions/${version.id}/activate/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success("Workflow version activated.");
    },
  });
  const updateSelfApproval = useMutation({
    mutationFn: ({
      version,
      allowed,
    }: {
      version: WorkflowVersion;
      allowed: boolean;
    }) =>
      apiPatch(`/approval-workflow-versions/${version.id}/`, {
        allow_self_approval: allowed,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-workflows"] });
      toast.success("Self-approval policy updated.");
    },
  });
  if (!canView) return <ERPPermissionState />;
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Administration"
        title="Approval workflows"
        description="Configure versioned approval routes using explicit steps, safe conditions, and company-scoped approver resolution."
        actions={
          canManage ? (
            <Button onClick={() => setWorkflowOpen(true)}>
              <Plus data-icon="inline-start" />
              New workflow
            </Button>
          ) : undefined
        }
      />
      {query.isPending ? (
        <ERPLoadingState />
      ) : query.isError ? (
        <ERPErrorState message={query.error.message} />
      ) : !query.data.results.length ? (
        <ERPEmptyState
          title="No approval workflows"
          description="Create the first workflow definition without assuming any real approver."
          action={
            canManage ? (
              <Button onClick={() => setWorkflowOpen(true)}>
                <Plus data-icon="inline-start" />
                New workflow
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[330px_1fr]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle>Workflows</CardTitle>
              <CardDescription>
                {query.data.pagination.count} configured
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {query.data.results.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={cn(
                    "w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted/40",
                    selected?.id === item.id && "border-primary bg-primary/5",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold">{item.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.code} · {item.company_name}
                      </p>
                    </div>
                    <ERPStatusBadge
                      value={item.current_version ? "ACTIVE" : "DRAFT"}
                    />
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
          {selected ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>{selected.name}</CardTitle>
                      <CardDescription>
                        {selected.description || "Document approval workflow"} ·{" "}
                        {selected.company_name}
                      </CardDescription>
                    </div>
                    {canManage && selected.current_version ? (
                      <Button
                        variant="outline"
                        onClick={() => clone.mutate(selected)}
                      >
                        <Copy data-icon="inline-start" />
                        Create new version
                      </Button>
                    ) : null}
                  </div>
                </CardHeader>
              </Card>
              {[...selected.versions]
                .sort((a, b) => b.version_number - a.version_number)
                .map((version) => (
                  <Card key={version.id}>
                    <CardHeader>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                            <GitBranch />
                          </span>
                          <div>
                            <CardTitle>
                              Version {version.version_number}
                            </CardTitle>
                            <CardDescription>
                              {version.steps.length} steps ·{" "}
                              {version.conditions.length} conditions ·
                              Self-approval{" "}
                              {version.allow_self_approval
                                ? "allowed"
                                : "blocked"}
                            </CardDescription>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <ERPStatusBadge value={version.status} />
                          {canManage && version.status === "DRAFT" ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setConditionVersion(version)}
                              >
                                <Settings2 data-icon="inline-start" />
                                Condition
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setStepVersion(version)}
                              >
                                <Plus data-icon="inline-start" />
                                Step
                              </Button>
                              <Button
                                size="sm"
                                disabled={
                                  !version.steps.length || activate.isPending
                                }
                                onClick={() => activate.mutate(version)}
                              >
                                <CheckCircle2 data-icon="inline-start" />
                                Activate
                              </Button>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {canManage && version.status === "DRAFT" ? (
                        <Field orientation="horizontal" className="rounded-lg border p-3">
                          <div className="flex-1">
                            <FieldLabel htmlFor={`self-approval-${version.id}`}>
                              Allow requesters to approve their own submission
                            </FieldLabel>
                            <FieldDescription>
                              Keep this off unless the company explicitly approves self-approval for this workflow.
                            </FieldDescription>
                          </div>
                          <Switch
                            id={`self-approval-${version.id}`}
                            checked={version.allow_self_approval}
                            disabled={updateSelfApproval.isPending}
                            onCheckedChange={(allowed) =>
                              updateSelfApproval.mutate({ version, allowed })
                            }
                          />
                        </Field>
                      ) : null}
                      {version.conditions.length ? (
                        <div>
                          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            Applies when
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {version.conditions.map((condition) => (
                              <Badge key={condition.id} variant="outline">
                                {condition.field.replaceAll("_", " ")}{" "}
                                {condition.operator}{" "}
                                {Array.isArray(condition.value)
                                  ? condition.value.join(", ")
                                  : String(condition.value)}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <div>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Ordered steps
                        </p>
                        {version.steps.length ? (
                          <div className="space-y-2">
                            {version.steps.map((step) => (
                              <div
                                key={step.id}
                                className="flex items-center gap-3 rounded-lg border p-3"
                              >
                                <span className="grid size-8 place-items-center rounded-full border bg-muted font-semibold">
                                  {step.sequence}
                                </span>
                                <div className="min-w-0 flex-1">
                                  <p className="font-semibold">{step.name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {step.resolver_type === "PERMISSION"
                                      ? `Permission: ${step.required_permission_code}`
                                      : `${step.specific_users.length} specific approver${step.specific_users.length === 1 ? "" : "s"}`}{" "}
                                    ·{" "}
                                    {step.approval_mode === "PARALLEL"
                                      ? `${step.minimum_approvals} approvals required`
                                      : "Any one approval"}
                                  </p>
                                </div>
                                <Users className="text-primary" />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                            No steps yet. Add at least one safe approver
                            resolution step before activation.
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          ) : null}
        </div>
      )}
      <WorkflowDialog open={workflowOpen} onOpenChange={setWorkflowOpen} />
      {selected && stepVersion ? (
        <StepDialog
          workflow={selected}
          version={stepVersion}
          open
          onOpenChange={(open) => {
            if (!open) setStepVersion(null);
          }}
        />
      ) : null}
      {conditionVersion ? (
        <ConditionDialog
          version={conditionVersion}
          open
          onOpenChange={(open) => {
            if (!open) setConditionVersion(null);
          }}
        />
      ) : null}
    </div>
  );
}
