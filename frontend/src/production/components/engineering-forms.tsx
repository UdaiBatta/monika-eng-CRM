import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPatch, apiPost } from "@/production/lib/api";
import type {
  EngineeringClarification,
  EngineeringReview,
  RelationOption,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

type AssessmentValues = Pick<
  EngineeringReview,
  | "technical_summary"
  | "feasibility_notes"
  | "assumptions"
  | "exclusions"
  | "constraints"
  | "risks"
  | "special_materials"
  | "outsourced_processes"
  | "tooling_requirements"
  | "testing_requirements"
  | "customer_clarification_summary"
  | "preliminary_drawing_notes"
  | "preliminary_bom_notes"
  | "preliminary_routing_notes"
> & {
  engineering_hours: string;
  manufacturing_hours: string;
  lead_time_days: string;
};
type ClarificationValues = {
  subject: string;
  question: string;
  context: string;
  assigned_to_id: string;
  due_at: string;
};

function FormError({ error }: { error: unknown }) {
  return error instanceof Error ? (
    <Alert variant="destructive">
      <AlertTitle>Could not save</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  ) : null;
}

export function EngineeringAssessmentForm({
  review,
  onSaved,
}: {
  review: EngineeringReview;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm<AssessmentValues>({
    defaultValues: {
      technical_summary: review.technical_summary,
      feasibility_notes: review.feasibility_notes,
      assumptions: review.assumptions,
      exclusions: review.exclusions,
      constraints: review.constraints,
      risks: review.risks,
      special_materials: review.special_materials,
      outsourced_processes: review.outsourced_processes,
      tooling_requirements: review.tooling_requirements,
      testing_requirements: review.testing_requirements,
      customer_clarification_summary: review.customer_clarification_summary,
      preliminary_drawing_notes: review.preliminary_drawing_notes,
      preliminary_bom_notes: review.preliminary_bom_notes,
      preliminary_routing_notes: review.preliminary_routing_notes,
      engineering_hours: review.engineering_hours ?? "",
      manufacturing_hours: review.manufacturing_hours ?? "",
      lead_time_days: review.lead_time_days?.toString() ?? "",
    },
  });
  const mutation = useMutation({
    mutationFn: (values: AssessmentValues) =>
      apiPatch(`/engineering-reviews/${review.id}/assessment/`, {
        ...values,
        engineering_hours: values.engineering_hours || null,
        manufacturing_hours: values.manufacturing_hours || null,
        lead_time_days: values.lead_time_days
          ? Number(values.lead_time_days)
          : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["engineering-workspace", review.id],
      });
      toast.success("Workshop assessment saved.");
      onSaved();
    },
  });
  const text = (name: keyof AssessmentValues, label: string, rows = 4) => (
    <Field>
      <FieldLabel htmlFor={`assessment-${name}`}>{label}</FieldLabel>
      <Textarea
        id={`assessment-${name}`}
        rows={rows}
        {...form.register(name)}
      />
    </Field>
  );
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <FieldSet>
          <FieldLegend>Workshop conclusion</FieldLegend>
          <FieldGroup>
            {text("technical_summary", "Technical summary", 5)}
            {text("feasibility_notes", "Workshop decision notes")}
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Design basis</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            {text("assumptions", "Assumptions")}
            {text("exclusions", "Exclusions")}
            {text("constraints", "Constraints")}
            {text("risks", "Risks")}
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Make / buy / test considerations</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            {text("special_materials", "Special materials")}
            {text("outsourced_processes", "Outsourced processes")}
            {text("tooling_requirements", "Tooling requirements")}
            {text("testing_requirements", "Testing requirements")}
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Optional technical details</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            {text("preliminary_drawing_notes", "Drawing notes")}
            {text("preliminary_bom_notes", "BOM notes")}
            {text("preliminary_routing_notes", "Routing notes")}
            {text(
              "customer_clarification_summary",
              "Customer clarification summary",
            )}
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Indicative effort and lead time</FieldLegend>
          <FieldGroup className="grid gap-4 sm:grid-cols-3">
            <Field>
              <FieldLabel htmlFor="engineering-hours">
                Workshop / technical hours
              </FieldLabel>
              <Input
                id="engineering-hours"
                type="number"
                min="0"
                max="999999.99"
                step="0.01"
                {...form.register("engineering_hours")}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="manufacturing-hours">
                Manufacturing hours
              </FieldLabel>
              <Input
                id="manufacturing-hours"
                type="number"
                min="0"
                max="999999.99"
                step="0.01"
                {...form.register("manufacturing_hours")}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="lead-time-days">Lead time (days)</FieldLabel>
              <Input
                id="lead-time-days"
                type="number"
                min="0"
                step="1"
                {...form.register("lead_time_days")}
              />
            </Field>
          </FieldGroup>
        </FieldSet>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving assessment…" : "Save assessment"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export function AssignEngineerForm({
  review,
  onSaved,
}: {
  review: EngineeringReview;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const employees = useQuery({
    queryKey: ["engineering-options", "employees"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/employees/?employment_status=ACTIVE&page_size=100",
      ),
    staleTime: 60_000,
  });
  const form = useForm({
    defaultValues: { engineer_id: review.assigned_engineer ?? "" },
  });
  const mutation = useMutation({
    mutationFn: (values: { engineer_id: string }) =>
      apiPost(`/engineering-reviews/${review.id}/assign/`, values),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["engineering-workspace", review.id],
      });
      queryClient.invalidateQueries({ queryKey: ["engineering-reviews"] });
      toast.success("Workshop Review assigned.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <Field>
          <FieldLabel htmlFor="review-engineer">Engineer</FieldLabel>
          <NativeSelect
            id="review-engineer"
            className="w-full"
            {...form.register("engineer_id", {
              required: "Engineer is required.",
            })}
          >
            <NativeSelectOption value="">Select engineer</NativeSelectOption>
            {employees.data?.results.map((employee) => (
              <NativeSelectOption key={employee.id} value={employee.id}>
                {employee.employee_code} · {employee.display_name}
              </NativeSelectOption>
            ))}
          </NativeSelect>
          <FieldError>{form.formState.errors.engineer_id?.message}</FieldError>
        </Field>
        <Button type="submit" disabled={mutation.isPending}>
          Assign review
        </Button>
      </FieldGroup>
    </form>
  );
}

export function ClarificationForm({
  review,
  onSaved,
}: {
  review: EngineeringReview;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const employees = useQuery({
    queryKey: ["engineering-options", "employees"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/employees/?employment_status=ACTIVE&page_size=100",
      ),
    staleTime: 60_000,
  });
  const form = useForm<ClarificationValues>({
    defaultValues: {
      subject: "",
      question: "",
      context: "",
      assigned_to_id: "",
      due_at: "",
    },
  });
  const mutation = useMutation({
    mutationFn: (values: ClarificationValues) =>
      apiPost(`/engineering-reviews/${review.id}/request-clarification/`, {
        ...values,
        due_at: values.due_at || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["engineering-workspace", review.id],
      });
      queryClient.invalidateQueries({ queryKey: ["engineering-reviews"] });
      toast.success("Clarification requested.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <Field>
          <FieldLabel htmlFor="clarification-subject">Subject</FieldLabel>
          <Input
            id="clarification-subject"
            autoFocus
            {...form.register("subject", { required: "Subject is required." })}
          />
          <FieldError>{form.formState.errors.subject?.message}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="clarification-question">Question</FieldLabel>
          <Textarea
            id="clarification-question"
            rows={5}
            {...form.register("question", {
              required: "Question is required.",
            })}
          />
          <FieldError>{form.formState.errors.question?.message}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="clarification-context">
            Workshop context
          </FieldLabel>
          <Textarea id="clarification-context" {...form.register("context")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="clarification-recipient">
              Assigned recipient
            </FieldLabel>
            <NativeSelect
              id="clarification-recipient"
              className="w-full"
              {...form.register("assigned_to_id", {
                required: "Recipient is required.",
              })}
            >
              <NativeSelectOption value="">Select recipient</NativeSelectOption>
              {employees.data?.results.map((employee) => (
                <NativeSelectOption key={employee.id} value={employee.id}>
                  {employee.employee_code} · {employee.display_name}
                </NativeSelectOption>
              ))}
            </NativeSelect>
            <FieldError>
              {form.formState.errors.assigned_to_id?.message}
            </FieldError>
          </Field>
          <Field>
            <FieldLabel htmlFor="clarification-due">Due at</FieldLabel>
            <Input
              id="clarification-due"
              type="datetime-local"
              {...form.register("due_at")}
            />
          </Field>
        </div>
        <Button type="submit" disabled={mutation.isPending}>
          Send clarification request
        </Button>
      </FieldGroup>
    </form>
  );
}

export function ClarificationResponseForm({
  clarification,
  onSaved,
}: {
  clarification: EngineeringClarification;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm({ defaultValues: { response: clarification.response } });
  const mutation = useMutation({
    mutationFn: (values: { response: string }) =>
      apiPost(
        `/engineering-clarifications/${clarification.id}/respond/`,
        values,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["engineering-workspace", clarification.review],
      });
      toast.success("Clarification response recorded.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <div className="rounded-md border bg-muted/20 p-4">
          <p className="font-medium">{clarification.subject}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {clarification.question}
          </p>
        </div>
        <Field>
          <FieldLabel htmlFor="clarification-response">Response</FieldLabel>
          <Textarea
            id="clarification-response"
            rows={6}
            autoFocus
            {...form.register("response", {
              required: "Response is required.",
            })}
          />
          <FieldError>{form.formState.errors.response?.message}</FieldError>
        </Field>
        <Button type="submit" disabled={mutation.isPending}>
          Submit response
        </Button>
      </FieldGroup>
    </form>
  );
}

export function ReviewDecisionForm({
  review,
  notFeasible = false,
  onSaved,
}: {
  review: EngineeringReview;
  notFeasible?: boolean;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm({
    defaultValues: { result: "FEASIBLE", completion_comment: "" },
  });
  const mutation = useMutation({
    mutationFn: (values: { result: string; completion_comment: string }) =>
      apiPost(
        `/engineering-reviews/${review.id}/${notFeasible ? "mark-not-feasible" : "complete"}/`,
        notFeasible
          ? { completion_comment: values.completion_comment }
          : values,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["engineering-workspace", review.id],
      });
      queryClient.invalidateQueries({ queryKey: ["engineering-reviews"] });
      toast.success(
        notFeasible
          ? "Review marked not feasible."
          : "Workshop Review completed.",
      );
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        {notFeasible ? (
          <Alert variant="destructive">
            <AlertTitle>This does not mark the enquiry lost</AlertTitle>
            <AlertDescription>
              Commercial still owns the enquiry outcome. Workshop records only
              whether the requirement can be built as currently specified.
            </AlertDescription>
          </Alert>
        ) : (
          <Field>
            <FieldLabel htmlFor="review-result">Workshop result</FieldLabel>
            <NativeSelect
              id="review-result"
              className="w-full"
              {...form.register("result")}
            >
              <NativeSelectOption value="FEASIBLE">Workshop Approved</NativeSelectOption>
              <NativeSelectOption value="FEASIBLE_WITH_CONDITIONS">
                Workshop Approved with conditions
              </NativeSelectOption>
            </NativeSelect>
          </Field>
        )}
        <Field>
          <FieldLabel htmlFor="completion-comment">
            Completion comment
          </FieldLabel>
          <Textarea
            id="completion-comment"
            rows={5}
            {...form.register("completion_comment", {
              required: "Completion comment is required.",
            })}
          />
          <FieldError>
            {form.formState.errors.completion_comment?.message}
          </FieldError>
        </Field>
        <Button
          type="submit"
          variant={notFeasible ? "destructive" : "default"}
          disabled={mutation.isPending}
        >
          {notFeasible ? "Confirm not feasible" : "Complete review"}
        </Button>
      </FieldGroup>
    </form>
  );
}
