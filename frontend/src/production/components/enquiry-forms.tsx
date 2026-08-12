import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { useCurrentUser } from "@/production/lib/auth";
import type {
  Customer,
  Enquiry,
  EnquiryItem,
  EnquiryRequirement,
  RelationOption,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

type EnquiryValues = {
  customer: string;
  customer_contact: string;
  customer_site: string;
  source: string;
  received_date: string;
  due_date: string;
  customer_reference: string;
  subject: string;
  description: string;
  priority: string;
  responsible_salesperson: string;
  estimated_value: string;
  currency: string;
};
type RequirementValues = {
  requirement_type: string;
  title: string;
  description: string;
  is_mandatory: boolean;
  customer_specification_reference: string;
  notes: string;
};
type ItemValues = {
  description: string;
  customer_reference: string;
  quantity: string;
  uom: string;
  technical_specification: string;
  requested_delivery: string;
  notes: string;
};

function FormError({ error }: { error: unknown }) {
  return error instanceof Error ? (
    <Alert variant="destructive">
      <AlertTitle>Could not save</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  ) : null;
}

export function EnquiryForm({
  enquiry,
  initialCustomerId = "",
  onSaved,
}: {
  enquiry?: Enquiry;
  initialCustomerId?: string;
  onSaved: (saved: Enquiry) => void;
}) {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const customers = useQuery({
    queryKey: ["enquiry-options", "customers"],
    queryFn: () => apiGet<Paginated<Customer>>("/customers/?page_size=100"),
  });
  const employees = useQuery({
    queryKey: ["enquiry-options", "employees"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/employees/?employment_status=ACTIVE&page_size=100",
      ),
    staleTime: 60_000,
  });
  const currencies = useQuery({
    queryKey: ["enquiry-options", "currencies"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/currencies/?is_active=true&page_size=100",
      ),
    staleTime: 60_000,
  });
  const form = useForm<EnquiryValues>({
    defaultValues: {
      customer: enquiry?.customer ?? initialCustomerId,
      customer_contact: enquiry?.customer_contact ?? "",
      customer_site: enquiry?.customer_site ?? "",
      source: enquiry?.source ?? "",
      received_date:
        enquiry?.received_date ?? new Date().toISOString().slice(0, 10),
      due_date: enquiry?.due_date ?? "",
      customer_reference: enquiry?.customer_reference ?? "",
      subject: enquiry?.subject ?? "",
      description: enquiry?.description ?? "",
      priority: enquiry?.priority ?? "NORMAL",
      responsible_salesperson:
        enquiry?.responsible_salesperson ?? user?.employee?.id ?? "",
      estimated_value: enquiry?.estimated_value ?? "",
      currency: enquiry?.currency ?? "",
    },
  });
  const customerId = form.watch("customer");
  const selectedCustomer =
    customers.data?.results.find((item) => item.id === customerId) ??
    (enquiry
      ? { ...({} as Customer), id: enquiry.customer, contacts: [], sites: [] }
      : undefined);
  const mutation = useMutation({
    mutationFn: (values: EnquiryValues) => {
      const payload: Record<string, unknown> = {
        ...values,
        company: user?.employee?.company_id,
        customer_contact: values.customer_contact || null,
        customer_site: values.customer_site || null,
        due_date: values.due_date || null,
        estimated_value: values.estimated_value || null,
        currency: values.currency || null,
      };
      if (enquiry) {
        delete payload.company;
        delete payload.customer;
        delete payload.responsible_salesperson;
      }
      return enquiry
        ? apiPatch<Enquiry>(`/enquiries/${enquiry.id}/`, payload)
        : apiPost<Enquiry>("/enquiries/", payload);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["enquiries"] });
      toast.success(
        enquiry ? "Enquiry updated." : `${saved.enquiry_number} created.`,
      );
      onSaved(saved);
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <FieldSet>
          <FieldLegend>Customer and RFQ reference</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field data-invalid={Boolean(form.formState.errors.customer)}>
              <FieldLabel htmlFor="enquiry-customer">Customer</FieldLabel>
              <NativeSelect
                id="enquiry-customer"
                className="w-full"
                disabled={Boolean(enquiry)}
                {...form.register("customer", {
                  required: "Customer is required.",
                })}
              >
                <NativeSelectOption value="">
                  Select customer
                </NativeSelectOption>
                {customers.data?.results.map((customer) => (
                  <NativeSelectOption key={customer.id} value={customer.id}>
                    {customer.customer_code} · {customer.legal_name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              <FieldError>{form.formState.errors.customer?.message}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-contact">
                Customer contact
              </FieldLabel>
              <NativeSelect
                id="enquiry-contact"
                className="w-full"
                {...form.register("customer_contact")}
              >
                <NativeSelectOption value="">
                  No contact selected
                </NativeSelectOption>
                {selectedCustomer?.contacts
                  ?.filter((item) => item.is_active)
                  .map((contact) => (
                    <NativeSelectOption key={contact.id} value={contact.id}>
                      {contact.display_name}
                    </NativeSelectOption>
                  ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-site">Customer site</FieldLabel>
              <NativeSelect
                id="enquiry-site"
                className="w-full"
                {...form.register("customer_site")}
              >
                <NativeSelectOption value="">
                  No site selected
                </NativeSelectOption>
                {selectedCustomer?.sites
                  ?.filter((item) => item.is_active)
                  .map((site) => (
                    <NativeSelectOption key={site.id} value={site.id}>
                      {site.label} · {site.city}
                    </NativeSelectOption>
                  ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="customer-rfq-reference">
                Customer RFQ / reference
              </FieldLabel>
              <Input
                id="customer-rfq-reference"
                {...form.register("customer_reference")}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-source">Source</FieldLabel>
              <Input
                id="enquiry-source"
                placeholder="Email, portal, referral…"
                {...form.register("source")}
              />
            </Field>
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Requirement summary</FieldLegend>
          <FieldGroup>
            <Field data-invalid={Boolean(form.formState.errors.subject)}>
              <FieldLabel htmlFor="enquiry-subject">Subject</FieldLabel>
              <Input
                id="enquiry-subject"
                autoFocus
                {...form.register("subject", {
                  required: "Subject is required.",
                })}
              />
              <FieldError>{form.formState.errors.subject?.message}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-description">Description</FieldLabel>
              <Textarea
                id="enquiry-description"
                rows={5}
                {...form.register("description")}
              />
            </Field>
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Ownership and dates</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="received-date">Received date</FieldLabel>
              <Input
                id="received-date"
                type="date"
                {...form.register("received_date", { required: true })}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="due-date">Response due date</FieldLabel>
              <Input id="due-date" type="date" {...form.register("due_date")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-priority">Priority</FieldLabel>
              <NativeSelect
                id="enquiry-priority"
                className="w-full"
                {...form.register("priority")}
              >
                <NativeSelectOption value="LOW">Low</NativeSelectOption>
                <NativeSelectOption value="NORMAL">Normal</NativeSelectOption>
                <NativeSelectOption value="HIGH">High</NativeSelectOption>
                <NativeSelectOption value="URGENT">Urgent</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="sales-owner">
                Responsible salesperson
              </FieldLabel>
              <NativeSelect
                id="sales-owner"
                className="w-full"
                disabled={Boolean(enquiry)}
                {...form.register("responsible_salesperson", {
                  required: "Sales owner is required.",
                })}
              >
                <NativeSelectOption value="">Select owner</NativeSelectOption>
                {employees.data?.results.map((employee) => (
                  <NativeSelectOption key={employee.id} value={employee.id}>
                    {employee.employee_code} · {employee.display_name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Commercial indication</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="estimated-value">Estimated value</FieldLabel>
              <Input
                id="estimated-value"
                type="number"
                min="0"
                step="0.01"
                {...form.register("estimated_value")}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-currency">Currency</FieldLabel>
              <NativeSelect
                id="enquiry-currency"
                className="w-full"
                {...form.register("currency")}
              >
                <NativeSelectOption value="">
                  Use customer default
                </NativeSelectOption>
                {currencies.data?.results.map((currency) => (
                  <NativeSelectOption key={currency.id} value={currency.id}>
                    {currency.code} · {currency.name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
          </FieldGroup>
        </FieldSet>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending
            ? "Saving…"
            : enquiry
              ? "Save enquiry"
              : "Create draft enquiry"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export function RequirementForm({
  enquiryId,
  requirement,
  onSaved,
}: {
  enquiryId: string;
  requirement?: EnquiryRequirement;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm<RequirementValues>({
    defaultValues: {
      requirement_type: requirement?.requirement_type ?? "TECHNICAL",
      title: requirement?.title ?? "",
      description: requirement?.description ?? "",
      is_mandatory: requirement?.is_mandatory ?? true,
      customer_specification_reference:
        requirement?.customer_specification_reference ?? "",
      notes: requirement?.notes ?? "",
    },
  });
  const mutation = useMutation({
    mutationFn: (values: RequirementValues) =>
      requirement
        ? apiPatch(`/enquiry-requirements/${requirement.id}/`, values)
        : apiPost("/enquiry-requirements/", { ...values, enquiry: enquiryId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["enquiry-workspace", enquiryId],
      });
      toast.success("Requirement saved.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <Field>
          <FieldLabel htmlFor="requirement-type">Requirement type</FieldLabel>
          <NativeSelect
            id="requirement-type"
            className="w-full"
            {...form.register("requirement_type")}
          >
            <NativeSelectOption value="TECHNICAL">Technical</NativeSelectOption>
            <NativeSelectOption value="COMMERCIAL">
              Commercial
            </NativeSelectOption>
            <NativeSelectOption value="DELIVERY">Delivery</NativeSelectOption>
            <NativeSelectOption value="COMPLIANCE">
              Compliance
            </NativeSelectOption>
            <NativeSelectOption value="OTHER">Other</NativeSelectOption>
          </NativeSelect>
        </Field>
        <Field>
          <FieldLabel htmlFor="requirement-title">Title</FieldLabel>
          <Input
            id="requirement-title"
            autoFocus
            {...form.register("title", { required: "Title is required." })}
          />
          <FieldError>{form.formState.errors.title?.message}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="requirement-description">Requirement</FieldLabel>
          <Textarea
            id="requirement-description"
            rows={5}
            {...form.register("description", {
              required: "Description is required.",
            })}
          />
          <FieldError>{form.formState.errors.description?.message}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="specification-reference">
            Customer specification reference
          </FieldLabel>
          <Input
            id="specification-reference"
            {...form.register("customer_specification_reference")}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="requirement-notes">Internal notes</FieldLabel>
          <Textarea id="requirement-notes" {...form.register("notes")} />
        </Field>
        <Field orientation="horizontal">
          <Checkbox
            id="requirement-mandatory"
            checked={form.watch("is_mandatory")}
            onCheckedChange={(value) =>
              form.setValue("is_mandatory", value === true)
            }
          />
          <FieldLabel htmlFor="requirement-mandatory">
            Mandatory requirement
          </FieldLabel>
        </Field>
        <Button type="submit" disabled={mutation.isPending}>
          Save requirement
        </Button>
      </FieldGroup>
    </form>
  );
}

export function ItemForm({
  enquiryId,
  item,
  onSaved,
}: {
  enquiryId: string;
  item?: EnquiryItem;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const uoms = useQuery({
    queryKey: ["enquiry-options", "uom"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/units-of-measure/?is_active=true&page_size=100",
      ),
    staleTime: 60_000,
  });
  const form = useForm<ItemValues>({
    defaultValues: {
      description: item?.description ?? "",
      customer_reference: item?.customer_reference ?? "",
      quantity: item?.quantity ?? "1",
      uom: item?.uom ?? "",
      technical_specification: item?.technical_specification ?? "",
      requested_delivery: item?.requested_delivery ?? "",
      notes: item?.notes ?? "",
    },
  });
  const mutation = useMutation({
    mutationFn: (values: ItemValues) => {
      const payload = {
        ...values,
        requested_delivery: values.requested_delivery || null,
      };
      return item
        ? apiPatch(`/enquiry-items/${item.id}/`, payload)
        : apiPost("/enquiry-items/", { ...payload, enquiry: enquiryId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["enquiry-workspace", enquiryId],
      });
      toast.success("Line item saved.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <FormError error={mutation.error} />
        <Field>
          <FieldLabel htmlFor="item-description">Item description</FieldLabel>
          <Input
            id="item-description"
            autoFocus
            {...form.register("description", {
              required: "Description is required.",
            })}
          />
          <FieldError>{form.formState.errors.description?.message}</FieldError>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="item-reference">
              Customer item reference
            </FieldLabel>
            <Input
              id="item-reference"
              {...form.register("customer_reference")}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="item-delivery">Requested delivery</FieldLabel>
            <Input
              id="item-delivery"
              type="date"
              {...form.register("requested_delivery")}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="item-quantity">Quantity</FieldLabel>
            <Input
              id="item-quantity"
              type="number"
              min="0.0001"
              step="0.0001"
              {...form.register("quantity", { required: true })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="item-uom">Unit of measure</FieldLabel>
            <NativeSelect
              id="item-uom"
              className="w-full"
              {...form.register("uom", { required: "Unit is required." })}
            >
              <NativeSelectOption value="">Select unit</NativeSelectOption>
              {uoms.data?.results.map((uom) => (
                <NativeSelectOption key={uom.id} value={uom.id}>
                  {uom.code} · {uom.name}
                </NativeSelectOption>
              ))}
            </NativeSelect>
            <FieldError>{form.formState.errors.uom?.message}</FieldError>
          </Field>
        </div>
        <Field>
          <FieldLabel htmlFor="technical-specification">
            Technical specification
          </FieldLabel>
          <Textarea
            id="technical-specification"
            rows={5}
            {...form.register("technical_specification")}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="item-notes">Notes</FieldLabel>
          <Textarea id="item-notes" {...form.register("notes")} />
        </Field>
        <Button type="submit" disabled={mutation.isPending}>
          Save line item
        </Button>
      </FieldGroup>
    </form>
  );
}
