import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Building2,
  ChevronRight,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiGet, apiPatch, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  Customer,
  CustomerFormValues,
  RelationOption,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatDateTime,
} from "@/production/components/shared";
import SpreadsheetImport from "@/production/components/spreadsheet-import";

const customerImport = {
  headers: [
    "company_code",
    "legal_name",
    "trade_name",
    "customer_type",
    "gstin",
    "pan",
    "cin",
    "industry",
    "website",
    "primary_email",
    "primary_phone",
    "account_manager_code",
    "default_currency_code",
    "source",
    "notes",
  ],
  required: ["company_code", "legal_name", "default_currency_code"],
  example: [
    "ME",
    "ABC Industries Pvt. Ltd.",
    "ABC Industries",
    "ORGANIZATION",
    "",
    "",
    "",
    "Electrical panels",
    "",
    "purchase@abc.example",
    "+91 99000 01111",
    "ME-001",
    "INR",
    "Existing spreadsheet",
    "",
  ],
};

const emptyCustomer: CustomerFormValues = {
  legal_name: "",
  trade_name: "",
  customer_type: "ORGANIZATION",
  gstin: "",
  pan: "",
  cin: "",
  industry: "",
  website: "",
  primary_email: "",
  primary_phone: "",
  account_manager: "",
  credit_limit: "",
  payment_term: "",
  default_currency: "",
  default_tax: "",
  source: "",
  notes: "",
  duplicate_override_reason: "",
};

function customerDefaults(customer?: Customer): CustomerFormValues {
  if (!customer) return emptyCustomer;
  return {
    legal_name: customer.legal_name,
    trade_name: customer.trade_name,
    customer_type: customer.customer_type,
    gstin: customer.gstin ?? "",
    pan: customer.pan ?? "",
    cin: customer.cin ?? "",
    industry: customer.industry,
    website: customer.website,
    primary_email: customer.primary_email,
    primary_phone: customer.primary_phone,
    account_manager: customer.account_manager ?? "",
    credit_limit: customer.credit_limit ?? "",
    payment_term: customer.payment_term ?? "",
    default_currency: customer.default_currency,
    default_tax: customer.default_tax ?? "",
    source: customer.source,
    notes: customer.notes,
    duplicate_override_reason: "",
  };
}

function relationLabel(option: RelationOption) {
  return (
    [
      option.code ?? option.employee_code,
      option.name ?? option.display_name ?? option.title ?? option.rate_name,
    ]
      .filter(Boolean)
      .join(" · ") || option.id
  );
}

function firstServerError(error: unknown, field: string) {
  if (
    !(error instanceof ApiError) ||
    !error.details ||
    typeof error.details !== "object"
  )
    return undefined;
  const details = error.details as Record<string, unknown>;
  const value = details[field];
  return Array.isArray(value)
    ? String(value[0])
    : typeof value === "string"
      ? value
      : undefined;
}

export function CustomerForm({
  customer,
  onSaved,
}: {
  customer?: Customer;
  onSaved: (customer: Customer) => void;
}) {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const form = useForm<CustomerFormValues>({
    defaultValues: customerDefaults(customer),
  });
  const canSeeSensitive =
    !customer || hasPermission(user, "crm.customer.view_sensitive");
  const optionQueries = useQueries({
    queries: [
      {
        queryKey: ["crm-options", "employees"],
        queryFn: () =>
          apiGet<Paginated<RelationOption>>(
            "/employees/?employment_status=ACTIVE&page_size=100",
          ),
        staleTime: 60_000,
      },
      {
        queryKey: ["crm-options", "currencies"],
        queryFn: () =>
          apiGet<Paginated<RelationOption>>(
            "/currencies/?is_active=true&page_size=100",
          ),
        staleTime: 60_000,
      },
      {
        queryKey: ["crm-options", "payment-terms"],
        queryFn: () =>
          apiGet<Paginated<RelationOption>>(
            "/payment-terms/?is_active=true&page_size=100",
          ),
        staleTime: 60_000,
      },
      {
        queryKey: ["crm-options", "tax-rates"],
        queryFn: () =>
          apiGet<Paginated<RelationOption>>(
            "/tax-rates/?is_active=true&page_size=100",
          ),
        staleTime: 60_000,
      },
    ],
  });
  const mutation = useMutation({
    mutationFn: (values: CustomerFormValues) => {
      const payload: Record<string, unknown> = {
        ...values,
        company: customer?.company ?? user?.employee?.company_id,
        account_manager: values.account_manager || null,
        payment_term: values.payment_term || null,
        default_tax: values.default_tax || null,
        credit_limit: values.credit_limit || null,
      };
      if (!canSeeSensitive)
        [
          "gstin",
          "pan",
          "cin",
          "credit_limit",
          "payment_term",
          "default_tax",
        ].forEach((key) => delete payload[key]);
      if (customer) delete payload.duplicate_override_reason;
      return customer
        ? apiPatch<Customer>(`/customers/${customer.id}/`, payload)
        : apiPost<Customer>("/customers/", payload);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      toast.success(
        customer ? "Customer updated." : `${saved.customer_code} created.`,
      );
      onSaved(saved);
    },
  });

  const duplicateMessage = firstServerError(mutation.error, "message");
  const formError =
    mutation.error instanceof Error ? mutation.error.message : undefined;
  const select = (
    name: keyof CustomerFormValues,
    label: string,
    options: RelationOption[],
    required = false,
  ) => (
    <Field
      data-invalid={Boolean(
        form.formState.errors[name] || firstServerError(mutation.error, name),
      )}
    >
      <FieldLabel htmlFor={name}>{label}</FieldLabel>
      <NativeSelect
        id={name}
        className="w-full"
        {...form.register(name, {
          required: required ? `${label} is required.` : false,
        })}
      >
        <NativeSelectOption value="">
          Select {label.toLowerCase()}
        </NativeSelectOption>
        {options.map((option) => (
          <NativeSelectOption key={option.id} value={option.id}>
            {relationLabel(option)}
          </NativeSelectOption>
        ))}
      </NativeSelect>
      <FieldError>
        {form.formState.errors[name]?.message ||
          firstServerError(mutation.error, name)}
      </FieldError>
    </Field>
  );

  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        {mutation.error ? (
          <Alert variant="destructive">
            <AlertTitle>Customer could not be saved</AlertTitle>
            <AlertDescription>{duplicateMessage ?? formError}</AlertDescription>
          </Alert>
        ) : null}
        <FieldSet>
          <FieldLegend>Business identity</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field data-invalid={Boolean(form.formState.errors.legal_name)}>
              <FieldLabel htmlFor="legal_name">Legal name</FieldLabel>
              <Input
                id="legal_name"
                autoFocus
                {...form.register("legal_name", {
                  required: "Legal name is required.",
                })}
              />
              <FieldError>
                {form.formState.errors.legal_name?.message}
              </FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="trade_name">Trade name</FieldLabel>
              <Input id="trade_name" {...form.register("trade_name")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="customer_type">Customer type</FieldLabel>
              <NativeSelect
                id="customer_type"
                className="w-full"
                {...form.register("customer_type")}
              >
                <NativeSelectOption value="ORGANIZATION">
                  Organization
                </NativeSelectOption>
                <NativeSelectOption value="INDIVIDUAL">
                  Individual
                </NativeSelectOption>
                <NativeSelectOption value="GOVERNMENT">
                  Government
                </NativeSelectOption>
                <NativeSelectOption value="DEALER">
                  Dealer / channel partner
                </NativeSelectOption>
                <NativeSelectOption value="OTHER">Other</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="industry">Industry</FieldLabel>
              <Input id="industry" {...form.register("industry")} />
            </Field>
            {canSeeSensitive ? (
              <>
                <Field>
                  <FieldLabel htmlFor="gstin">GSTIN</FieldLabel>
                  <Input
                    id="gstin"
                    maxLength={15}
                    className="uppercase"
                    {...form.register("gstin")}
                  />
                  <FieldError>
                    {firstServerError(mutation.error, "gstin")}
                  </FieldError>
                </Field>
                <Field>
                  <FieldLabel htmlFor="pan">PAN</FieldLabel>
                  <Input
                    id="pan"
                    maxLength={10}
                    className="uppercase"
                    {...form.register("pan")}
                  />
                  <FieldError>
                    {firstServerError(mutation.error, "pan")}
                  </FieldError>
                </Field>
                <Field>
                  <FieldLabel htmlFor="cin">CIN</FieldLabel>
                  <Input
                    id="cin"
                    maxLength={21}
                    className="uppercase"
                    {...form.register("cin")}
                  />
                </Field>
              </>
            ) : null}
            <Field>
              <FieldLabel htmlFor="source">Source</FieldLabel>
              <Input
                id="source"
                placeholder="Referral, tender portal, exhibition…"
                {...form.register("source")}
              />
            </Field>
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Contact details</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="primary_email">Primary email</FieldLabel>
              <Input
                id="primary_email"
                type="email"
                {...form.register("primary_email")}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="primary_phone">Primary phone</FieldLabel>
              <Input id="primary_phone" {...form.register("primary_phone")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="website">Website</FieldLabel>
              <Input
                id="website"
                type="url"
                placeholder="https://"
                {...form.register("website")}
              />
            </Field>
            {select(
              "account_manager",
              "Account manager",
              optionQueries[0].data?.results ?? [],
            )}
          </FieldGroup>
        </FieldSet>
        <FieldSet>
          <FieldLegend>Commercial defaults</FieldLegend>
          <FieldGroup className="grid gap-4 md:grid-cols-2">
            {select(
              "default_currency",
              "Default currency",
              optionQueries[1].data?.results ?? [],
              true,
            )}
            {canSeeSensitive
              ? select(
                  "payment_term",
                  "Payment term",
                  optionQueries[2].data?.results ?? [],
                )
              : null}
            {canSeeSensitive
              ? select(
                  "default_tax",
                  "Default tax",
                  optionQueries[3].data?.results ?? [],
                )
              : null}
            {canSeeSensitive ? (
              <Field>
                <FieldLabel htmlFor="credit_limit">Credit limit</FieldLabel>
                <Input
                  id="credit_limit"
                  type="number"
                  min="0"
                  step="0.01"
                  {...form.register("credit_limit")}
                />
              </Field>
            ) : null}
          </FieldGroup>
        </FieldSet>
        <Field>
          <FieldLabel htmlFor="notes">Internal notes</FieldLabel>
          <Textarea id="notes" rows={4} {...form.register("notes")} />
        </Field>
        {!customer && duplicateMessage ? (
          <Field>
            <FieldLabel htmlFor="duplicate_override_reason">
              Reason to continue with a possible duplicate
            </FieldLabel>
            <Textarea
              id="duplicate_override_reason"
              {...form.register("duplicate_override_reason", {
                required: "Explain why this is a separate customer.",
              })}
            />
            <FieldError>
              {form.formState.errors.duplicate_override_reason?.message}
            </FieldError>
          </Field>
        ) : null}
        <Button
          type="submit"
          disabled={
            mutation.isPending || optionQueries.some((query) => query.isPending)
          }
        >
          {mutation.isPending
            ? "Saving…"
            : customer
              ? "Save changes"
              : "Create customer"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export default function CustomersPage() {
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [customerType, setCustomerType] = useState("");
  const [formCustomer, setFormCustomer] = useState<Customer | null | undefined>(
    undefined,
  );
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    if (customerType) next.set("customer_type", customerType);
    return next;
  }, [page, search, status, customerType]);
  const query = useQuery({
    queryKey: ["customers", params.toString()],
    queryFn: () => apiGet<Paginated<Customer>>(`/customers/?${params}`),
  });
  const canCreate = hasPermission(user, "crm.customer.create");

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM"
        title="Customers"
        description="A single account register for contacts, sites, enquiries, follow-ups, documents, and commercial history."
        actions={
          canCreate ? (
            <>
              <SpreadsheetImport
                endpoint="/customers/import-history/"
                label="customers"
                templateName="customers"
                headers={customerImport.headers}
                required={customerImport.required}
                example={customerImport.example}
                queryKey={["customers"]}
                note="Company, employee and currency codes must already exist. Download the template before preparing your sheet."
              />
              <Button onClick={() => setFormCustomer(null)}>
                <Plus data-icon="inline-start" />
                New customer
              </Button>
            </>
          ) : undefined
        }
      />
      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <CardTitle>Customer register</CardTitle>
            <CardDescription>
              {query.data?.pagination.count ?? 0} customer accounts in scope
            </CardDescription>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-[minmax(220px,1fr)_160px_180px_auto] xl:max-w-4xl">
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(searchInput);
                setPage(1);
              }}
            >
              <Field>
                <FieldLabel htmlFor="customer-search" className="sr-only">
                  Search customers
                </FieldLabel>
                <Input
                  id="customer-search"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Code, name, GSTIN, contact…"
                />
              </Field>
              <Button type="submit" variant="outline">
                <Search data-icon="inline-start" />
                Search
              </Button>
            </form>
            <Field>
              <FieldLabel htmlFor="customer-status" className="sr-only">
                Status
              </FieldLabel>
              <NativeSelect
                id="customer-status"
                className="w-full"
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All statuses</NativeSelectOption>
                <NativeSelectOption value="PROSPECT">
                  Prospect
                </NativeSelectOption>
                <NativeSelectOption value="ACTIVE">Active</NativeSelectOption>
                <NativeSelectOption value="INACTIVE">
                  Inactive
                </NativeSelectOption>
                <NativeSelectOption value="BLOCKED">Blocked</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="customer-type-filter" className="sr-only">
                Customer type
              </FieldLabel>
              <NativeSelect
                id="customer-type-filter"
                className="w-full"
                value={customerType}
                onChange={(event) => {
                  setCustomerType(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">
                  All customer types
                </NativeSelectOption>
                <NativeSelectOption value="ORGANIZATION">
                  Organization
                </NativeSelectOption>
                <NativeSelectOption value="GOVERNMENT">
                  Government
                </NativeSelectOption>
                <NativeSelectOption value="DEALER">Dealer</NativeSelectOption>
                <NativeSelectOption value="INDIVIDUAL">
                  Individual
                </NativeSelectOption>
              </NativeSelect>
            </Field>
            <Button
              variant="ghost"
              onClick={() => {
                setSearchInput("");
                setSearch("");
                setStatus("");
                setCustomerType("");
                setPage(1);
              }}
            >
              <SlidersHorizontal data-icon="inline-start" />
              Reset
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <ERPLoadingState rows={7} />
          ) : query.isError ? (
            <ERPErrorState message={query.error.message} />
          ) : !query.data.results.length ? (
            <ERPEmptyState
              title="No customers found"
              description="Adjust the filters or add the first customer account."
              action={
                canCreate ? (
                  <Button onClick={() => setFormCustomer(null)}>
                    <Plus data-icon="inline-start" />
                    New customer
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Primary contact</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Account manager</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last update</TableHead>
                    <TableHead>
                      <span className="sr-only">Open</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {query.data.results.map((customer) => (
                    <TableRow
                      key={customer.id}
                      className="cursor-pointer"
                      onClick={() =>
                        navigate(`/app/crm/customers/${customer.id}`)
                      }
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <span className="flex size-9 shrink-0 items-center justify-center rounded-md border bg-muted text-primary">
                            <Building2 aria-hidden="true" />
                          </span>
                          <div>
                            <p className="font-medium text-foreground">
                              {customer.legal_name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {customer.customer_code}
                              {customer.trade_name
                                ? ` · ${customer.trade_name}`
                                : ""}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <p>
                          {customer.primary_contact?.display_name ||
                            customer.primary_email ||
                            "—"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {customer.primary_contact?.phone ||
                            customer.primary_phone}
                        </p>
                      </TableCell>
                      <TableCell>
                        {customer.sites?.[0]
                          ? `${customer.sites[0].city}, ${customer.sites[0].state}`
                          : "—"}
                      </TableCell>
                      <TableCell>
                        {customer.account_manager_name || "Unassigned"}
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={customer.status} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-muted-foreground">
                        {formatDateTime(customer.last_activity_at ?? customer.updated_at)}
                      </TableCell>
                      <TableCell>
                        <Button
                          aria-label={`Open ${customer.legal_name}`}
                          variant="ghost"
                          size="icon"
                        >
                          <ChevronRight />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {query.data && query.data.pagination.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                disabled={!query.data.pagination.previous}
                onClick={() => setPage((current) => current - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {query.data.pagination.pages}
              </span>
              <Button
                variant="outline"
                disabled={!query.data.pagination.next}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <Sheet
        open={formCustomer !== undefined}
        onOpenChange={(open) => {
          if (!open) setFormCustomer(undefined);
        }}
      >
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>
              {formCustomer
                ? `Edit ${formCustomer.legal_name}`
                : "New customer"}
            </SheetTitle>
            <SheetDescription>
              Create the commercial account once; contacts, sites, and enquiries
              attach to it.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {formCustomer !== undefined ? (
              <CustomerForm
                customer={formCustomer ?? undefined}
                onSaved={(saved) => {
                  setFormCustomer(undefined);
                  navigate(`/app/crm/customers/${saved.id}`);
                }}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
