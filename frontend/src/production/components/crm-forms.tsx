import { useEffect } from "react";
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
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPatch, apiPost } from "@/production/lib/api";
import type {
  CrmActivity,
  Customer,
  CustomerContact,
  CustomerSite,
  RelationOption,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

type ContactValues = {
  first_name: string;
  last_name: string;
  title: string;
  department: string;
  email: string;
  phone: string;
  alternate_phone: string;
  preferred_contact_method: string;
  notes: string;
  is_primary: boolean;
  is_active: boolean;
};
type SiteValues = {
  address_type: string;
  label: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  district: string;
  state: string;
  country: string;
  postal_code: string;
  gstin: string;
  contact: string;
  phone: string;
  is_default: boolean;
  is_active: boolean;
};
type ActivityValues = {
  customer: string;
  enquiry: string;
  contact: string;
  activity_type: string;
  subject: string;
  description: string;
  activity_date: string;
  next_follow_up_at: string;
  follow_up_owner: string;
  priority: string;
};

function ErrorAlert({ error }: { error: unknown }) {
  return error instanceof Error ? (
    <Alert variant="destructive">
      <AlertTitle>Could not save</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  ) : null;
}

export function ContactForm({
  customerId,
  contact,
  onSaved,
}: {
  customerId: string;
  contact?: CustomerContact;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm<ContactValues>({
    defaultValues: {
      first_name: contact?.first_name ?? "",
      last_name: contact?.last_name ?? "",
      title: contact?.title ?? "",
      department: contact?.department ?? "",
      email: contact?.email ?? "",
      phone: contact?.phone ?? "",
      alternate_phone: contact?.alternate_phone ?? "",
      preferred_contact_method: contact?.preferred_contact_method ?? "",
      notes: contact?.notes ?? "",
      is_primary: contact?.is_primary ?? false,
      is_active: contact?.is_active ?? true,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: ContactValues) =>
      contact
        ? apiPatch(`/customer-contacts/${contact.id}/`, values)
        : apiPost("/customer-contacts/", { ...values, customer: customerId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-360", customerId] });
      toast.success("Contact saved.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <ErrorAlert error={mutation.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field data-invalid={Boolean(form.formState.errors.first_name)}>
            <FieldLabel htmlFor="contact-first-name">First name</FieldLabel>
            <Input
              id="contact-first-name"
              autoFocus
              {...form.register("first_name", {
                required: "First name is required.",
              })}
            />
            <FieldError>{form.formState.errors.first_name?.message}</FieldError>
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-last-name">Last name</FieldLabel>
            <Input id="contact-last-name" {...form.register("last_name")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-title">Job title</FieldLabel>
            <Input id="contact-title" {...form.register("title")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-department">Department</FieldLabel>
            <Input id="contact-department" {...form.register("department")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-email">Email</FieldLabel>
            <Input
              id="contact-email"
              type="email"
              {...form.register("email")}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-phone">Phone</FieldLabel>
            <Input id="contact-phone" {...form.register("phone")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-alt-phone">Alternate phone</FieldLabel>
            <Input
              id="contact-alt-phone"
              {...form.register("alternate_phone")}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="contact-method">
              Preferred contact method
            </FieldLabel>
            <NativeSelect
              id="contact-method"
              className="w-full"
              {...form.register("preferred_contact_method")}
            >
              <NativeSelectOption value="">Not specified</NativeSelectOption>
              <NativeSelectOption value="PHONE">Phone</NativeSelectOption>
              <NativeSelectOption value="EMAIL">Email</NativeSelectOption>
              <NativeSelectOption value="WHATSAPP">WhatsApp</NativeSelectOption>
            </NativeSelect>
          </Field>
        </div>
        <Field>
          <FieldLabel htmlFor="contact-notes">Notes</FieldLabel>
          <Textarea id="contact-notes" {...form.register("notes")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field orientation="horizontal">
            <Checkbox
              id="contact-primary"
              checked={form.watch("is_primary")}
              onCheckedChange={(value) =>
                form.setValue("is_primary", value === true)
              }
            />
            <FieldLabel htmlFor="contact-primary">Primary contact</FieldLabel>
          </Field>
          <Field orientation="horizontal">
            <Checkbox
              id="contact-active"
              checked={form.watch("is_active")}
              onCheckedChange={(value) =>
                form.setValue("is_active", value === true)
              }
            />
            <FieldLabel htmlFor="contact-active">Active</FieldLabel>
          </Field>
        </div>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save contact"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export function SiteForm({
  customerId,
  contacts,
  site,
  onSaved,
}: {
  customerId: string;
  contacts: CustomerContact[];
  site?: CustomerSite;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const form = useForm<SiteValues>({
    defaultValues: {
      address_type: site?.address_type ?? "SITE",
      label: site?.label ?? "",
      address_line_1: site?.address_line_1 ?? "",
      address_line_2: site?.address_line_2 ?? "",
      city: site?.city ?? "",
      district: site?.district ?? "",
      state: site?.state ?? "",
      country: site?.country ?? "India",
      postal_code: site?.postal_code ?? "",
      gstin: site?.gstin ?? "",
      contact: site?.contact ?? "",
      phone: site?.phone ?? "",
      is_default: site?.is_default ?? false,
      is_active: site?.is_active ?? true,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: SiteValues) => {
      const payload = { ...values, contact: values.contact || null };
      return site
        ? apiPatch(`/customer-sites/${site.id}/`, payload)
        : apiPost("/customer-sites/", { ...payload, customer: customerId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-360", customerId] });
      toast.success("Site saved.");
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <ErrorAlert error={mutation.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="site-type">Address type</FieldLabel>
            <NativeSelect
              id="site-type"
              className="w-full"
              {...form.register("address_type")}
            >
              <NativeSelectOption value="SITE">Project site</NativeSelectOption>
              <NativeSelectOption value="REGISTERED">
                Registered
              </NativeSelectOption>
              <NativeSelectOption value="BILLING">Billing</NativeSelectOption>
              <NativeSelectOption value="SHIPPING">Shipping</NativeSelectOption>
              <NativeSelectOption value="OTHER">Other</NativeSelectOption>
            </NativeSelect>
          </Field>
          <Field data-invalid={Boolean(form.formState.errors.label)}>
            <FieldLabel htmlFor="site-label">Site label</FieldLabel>
            <Input
              id="site-label"
              autoFocus
              {...form.register("label", {
                required: "Site label is required.",
              })}
            />
            <FieldError>{form.formState.errors.label?.message}</FieldError>
          </Field>
          <Field className="sm:col-span-2">
            <FieldLabel htmlFor="site-line-1">Address line 1</FieldLabel>
            <Input
              id="site-line-1"
              {...form.register("address_line_1", {
                required: "Address is required.",
              })}
            />
          </Field>
          <Field className="sm:col-span-2">
            <FieldLabel htmlFor="site-line-2">Address line 2</FieldLabel>
            <Input id="site-line-2" {...form.register("address_line_2")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-city">City</FieldLabel>
            <Input
              id="site-city"
              {...form.register("city", { required: "City is required." })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-district">District</FieldLabel>
            <Input id="site-district" {...form.register("district")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-state">State</FieldLabel>
            <Input
              id="site-state"
              {...form.register("state", { required: "State is required." })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-postal">Postal code</FieldLabel>
            <Input
              id="site-postal"
              {...form.register("postal_code", {
                required: "Postal code is required.",
              })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-country">Country</FieldLabel>
            <Input id="site-country" {...form.register("country")} />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-gstin">Site GSTIN</FieldLabel>
            <Input
              id="site-gstin"
              className="uppercase"
              maxLength={15}
              {...form.register("gstin")}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="site-contact">Site contact</FieldLabel>
            <NativeSelect
              id="site-contact"
              className="w-full"
              {...form.register("contact")}
            >
              <NativeSelectOption value="">Not assigned</NativeSelectOption>
              {contacts.map((contact) => (
                <NativeSelectOption key={contact.id} value={contact.id}>
                  {contact.display_name}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="site-phone">Site phone</FieldLabel>
            <Input id="site-phone" {...form.register("phone")} />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field orientation="horizontal">
            <Checkbox
              id="site-default"
              checked={form.watch("is_default")}
              onCheckedChange={(value) =>
                form.setValue("is_default", value === true)
              }
            />
            <FieldLabel htmlFor="site-default">
              Default for this type
            </FieldLabel>
          </Field>
          <Field orientation="horizontal">
            <Checkbox
              id="site-active"
              checked={form.watch("is_active")}
              onCheckedChange={(value) =>
                form.setValue("is_active", value === true)
              }
            />
            <FieldLabel htmlFor="site-active">Active</FieldLabel>
          </Field>
        </div>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save site"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export function ActivityForm({
  customer,
  activity,
  onSaved,
}: {
  customer?: Customer;
  activity?: CrmActivity;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const customers = useQuery({
    queryKey: ["crm-options", "customers"],
    queryFn: () => apiGet<Paginated<Customer>>("/customers/?page_size=100"),
    enabled: !customer,
  });
  const employees = useQuery({
    queryKey: ["crm-options", "employees"],
    queryFn: () =>
      apiGet<Paginated<RelationOption>>(
        "/employees/?employment_status=ACTIVE&page_size=100",
      ),
    staleTime: 60_000,
  });
  const form = useForm<ActivityValues>({
    defaultValues: {
      customer: customer?.id ?? activity?.customer ?? "",
      enquiry: activity?.enquiry ?? "",
      contact: activity?.contact ?? "",
      activity_type: activity?.activity_type ?? "CALL",
      subject: activity?.subject ?? "",
      description: activity?.description ?? "",
      activity_date: activity?.activity_date
        ? activity.activity_date.slice(0, 16)
        : new Date().toISOString().slice(0, 16),
      next_follow_up_at: activity?.next_follow_up_at?.slice(0, 16) ?? "",
      follow_up_owner: activity?.follow_up_owner ?? "",
      priority: activity?.priority ?? "NORMAL",
    },
  });
  const selectedCustomerId = form.watch("customer");
  const selectedType = form.watch("activity_type");
  const selectedCustomer =
    customer ??
    customers.data?.results.find((item) => item.id === selectedCustomerId);
  const enquiries = useQuery({
    queryKey: ["crm-options", "enquiries", selectedCustomerId],
    queryFn: () =>
      apiGet<Paginated<{ id: string; enquiry_number: string; title: string }>>(
        `/enquiries/?customer=${selectedCustomerId}&page_size=100`,
      ),
    enabled: Boolean(selectedCustomerId),
  });
  useEffect(() => {
    if (customer && !form.getValues("customer"))
      form.setValue("customer", customer.id);
  }, [customer, form]);
  const mutation = useMutation({
    mutationFn: (values: ActivityValues) => {
      const payload = {
        ...values,
        enquiry: values.enquiry || null,
        contact: values.contact || null,
        follow_up_owner: values.follow_up_owner || null,
        next_follow_up_at: values.next_follow_up_at || null,
      };
      return activity
        ? apiPatch(`/crm-activities/${activity.id}/`, payload)
        : apiPost("/crm-activities/", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-activities"] });
      if (selectedCustomerId)
        queryClient.invalidateQueries({
          queryKey: ["customer-360", selectedCustomerId],
        });
      toast.success(
        selectedType === "FOLLOW_UP"
          ? "Follow-up scheduled."
          : "Activity recorded.",
      );
      onSaved();
    },
  });
  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        <ErrorAlert error={mutation.error} />
        {!customer ? (
          <Field>
            <FieldLabel htmlFor="activity-customer">Customer</FieldLabel>
            <NativeSelect
              id="activity-customer"
              className="w-full"
              {...form.register("customer", {
                required: "Customer is required.",
              })}
            >
              <NativeSelectOption value="">Select customer</NativeSelectOption>
              {customers.data?.results.map((item) => (
                <NativeSelectOption key={item.id} value={item.id}>
                  {item.customer_code} · {item.legal_name}
                </NativeSelectOption>
              ))}
            </NativeSelect>
            <FieldError>{form.formState.errors.customer?.message}</FieldError>
          </Field>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="activity-type">Activity type</FieldLabel>
            <NativeSelect
              id="activity-type"
              className="w-full"
              {...form.register("activity_type")}
            >
              <NativeSelectOption value="CALL">Call</NativeSelectOption>
              <NativeSelectOption value="EMAIL">Email</NativeSelectOption>
              <NativeSelectOption value="MEETING">Meeting</NativeSelectOption>
              <NativeSelectOption value="WHATSAPP">WhatsApp</NativeSelectOption>
              <NativeSelectOption value="SITE_VISIT">
                Site visit
              </NativeSelectOption>
              <NativeSelectOption value="NOTE">Note</NativeSelectOption>
              <NativeSelectOption value="FOLLOW_UP">
                Follow-up
              </NativeSelectOption>
              <NativeSelectOption value="OTHER">Other</NativeSelectOption>
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="activity-date">Activity date</FieldLabel>
            <Input
              id="activity-date"
              type="datetime-local"
              {...form.register("activity_date", { required: true })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="activity-contact">Contact</FieldLabel>
            <NativeSelect
              id="activity-contact"
              className="w-full"
              {...form.register("contact")}
            >
              <NativeSelectOption value="">No contact</NativeSelectOption>
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
            <FieldLabel htmlFor="activity-enquiry">Enquiry / RFQ</FieldLabel>
            <NativeSelect
              id="activity-enquiry"
              className="w-full"
              {...form.register("enquiry")}
            >
              <NativeSelectOption value="">No enquiry</NativeSelectOption>
              {enquiries.data?.results.map((item) => (
                <NativeSelectOption key={item.id} value={item.id}>
                  {item.enquiry_number} · {item.title}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
        </div>
        <Field data-invalid={Boolean(form.formState.errors.subject)}>
          <FieldLabel htmlFor="activity-subject">Subject</FieldLabel>
          <Input
            id="activity-subject"
            autoFocus
            {...form.register("subject", { required: "Subject is required." })}
          />
          <FieldError>{form.formState.errors.subject?.message}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="activity-description">
            Discussion / outcome
          </FieldLabel>
          <Textarea
            id="activity-description"
            rows={4}
            {...form.register("description")}
          />
        </Field>
        {selectedType === "FOLLOW_UP" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="follow-up-at">Follow-up due</FieldLabel>
              <Input
                id="follow-up-at"
                type="datetime-local"
                {...form.register("next_follow_up_at", {
                  required: "Due date is required for a follow-up.",
                })}
              />
              <FieldError>
                {form.formState.errors.next_follow_up_at?.message}
              </FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="follow-up-owner">Owner</FieldLabel>
              <NativeSelect
                id="follow-up-owner"
                className="w-full"
                {...form.register("follow_up_owner", {
                  required: "Owner is required for a follow-up.",
                })}
              >
                <NativeSelectOption value="">Select owner</NativeSelectOption>
                {employees.data?.results.map((employee) => (
                  <NativeSelectOption key={employee.id} value={employee.id}>
                    {employee.employee_code} · {employee.display_name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              <FieldError>
                {form.formState.errors.follow_up_owner?.message}
              </FieldError>
            </Field>
          </div>
        ) : null}
        <Field>
          <FieldLabel htmlFor="activity-priority">Priority</FieldLabel>
          <NativeSelect
            id="activity-priority"
            className="w-full"
            {...form.register("priority")}
          >
            <NativeSelectOption value="LOW">Low</NativeSelectOption>
            <NativeSelectOption value="NORMAL">Normal</NativeSelectOption>
            <NativeSelectOption value="HIGH">High</NativeSelectOption>
            <NativeSelectOption value="URGENT">Urgent</NativeSelectOption>
          </NativeSelect>
        </Field>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending
            ? "Saving…"
            : selectedType === "FOLLOW_UP"
              ? "Schedule follow-up"
              : "Record activity"}
        </Button>
      </FieldGroup>
    </form>
  );
}
