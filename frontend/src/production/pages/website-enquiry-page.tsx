import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowUpRight,
  Building2,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  FileCheck2,
  FileText,
  Globe2,
  Mail,
  MapPin,
  MessageSquareText,
  Phone,
  ShieldCheck,
  Sparkles,
  UserRound,
  UserRoundCheck,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

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
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
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
  CustomerContact,
  ExternalEnquiryCandidates,
  ExternalEnquirySubmission,
  RelationOption,
} from "@/production/lib/crm-types";
import { useRealtimeEntity } from "@/production/lib/realtime";
import type { EmployeeSummary, Paginated } from "@/production/lib/types";

type Decision = "reject" | "mark-spam" | "restore-for-review";

function DetailRow({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="grid gap-1 border-b py-3 last:border-b-0 sm:grid-cols-[150px_1fr]">
      <dt className="text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </dt>
      <dd className="break-words text-sm">{value || "—"}</dd>
    </div>
  );
}

function splitName(value: string) {
  const [firstName, ...rest] = value.trim().split(/\s+/);
  return { first_name: firstName || "Incoming", last_name: rest.join(" ") };
}

function MutationError({ error }: { error: Error | null }) {
  return error ? <ERPErrorState title="Action could not be completed" message={error.message} /> : null;
}

export default function WebsiteEnquiryPage() {
  const { submissionId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const companyId = user?.employee?.company_id ?? "";
  const [assignEmployee, setAssignEmployee] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [reason, setReason] = useState("");
  const [customerMode, setCustomerMode] = useState<"existing" | "new">("existing");
  const [contactMode, setContactMode] = useState<"existing" | "new">("existing");
  const [customerId, setCustomerId] = useState("");
  const [contactId, setContactId] = useState("");
  const [salespersonId, setSalespersonId] = useState("");
  const [currencyId, setCurrencyId] = useState("");
  const [documentCategoryId, setDocumentCategoryId] = useState("");
  const [followUpAt, setFollowUpAt] = useState("");
  const [newCustomerName, setNewCustomerName] = useState("");
  const [newContactName, setNewContactName] = useState("");
  const viewers = useRealtimeEntity("external_enquiry_submission", submissionId);

  const query = useQuery({
    queryKey: ["incoming-enquiry", submissionId],
    queryFn: () => apiGet<ExternalEnquirySubmission>(`/external-enquiries/${submissionId}/`),
    enabled: Boolean(submissionId),
  });
  const candidates = useQuery({
    queryKey: ["incoming-enquiry-candidates", submissionId],
    queryFn: () => apiGet<ExternalEnquiryCandidates>(`/external-enquiries/${submissionId}/candidates/`),
    enabled: Boolean(submissionId) && hasPermission(user, "crm.external_enquiry.review"),
  });
  const employees = useQuery({
    queryKey: ["incoming-enquiry-employees", companyId],
    queryFn: () => apiGet<Paginated<EmployeeSummary>>(`/employees/?company=${companyId}&employment_status=ACTIVE&page_size=100`),
    enabled: Boolean(companyId),
  });
  const customers = useQuery({
    queryKey: ["incoming-enquiry-customers"],
    queryFn: () => apiGet<Paginated<Customer>>("/customers/?status=ACTIVE&page_size=100&ordering=legal_name"),
  });
  const effectiveCustomerId =
    customerId || query.data?.matched_customer || candidates.data?.customers[0]?.id || "";
  const contacts = useQuery({
    queryKey: ["incoming-enquiry-contacts", effectiveCustomerId],
    queryFn: () => apiGet<Paginated<CustomerContact>>(`/customer-contacts/?customer=${effectiveCustomerId}&is_active=true&page_size=100`),
    enabled: customerMode === "existing" && Boolean(effectiveCustomerId),
  });
  const currencies = useQuery({
    queryKey: ["incoming-enquiry-currencies"],
    queryFn: () => apiGet<Paginated<RelationOption>>("/currencies/?is_active=true&page_size=100"),
  });
  const categories = useQuery({
    queryKey: ["incoming-enquiry-document-categories", companyId],
    queryFn: () => apiGet<Paginated<RelationOption>>(`/document-categories/?company=${companyId}&is_active=true&page_size=100`),
    enabled: Boolean(companyId),
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["incoming-enquiry", submissionId] }),
      queryClient.invalidateQueries({ queryKey: ["incoming-enquiry-candidates", submissionId] }),
      queryClient.invalidateQueries({ queryKey: ["incoming-enquiries"] }),
    ]);
  };
  const assign = useMutation({
    mutationFn: () =>
      apiPost<ExternalEnquirySubmission>(`/external-enquiries/${submissionId}/assign/`, {
        employee_id: assignEmployee || query.data?.assigned_to,
        priority,
      }),
    onSuccess: refresh,
  });
  const takeOwnership = useMutation({
    mutationFn: () => apiPost<ExternalEnquirySubmission>(`/external-enquiries/${submissionId}/take-ownership/`, {}),
    onSuccess: refresh,
  });
  const decide = useMutation({
    mutationFn: () =>
      apiPost<ExternalEnquirySubmission>(`/external-enquiries/${submissionId}/${decision}/`, {
        reason,
      }),
    onSuccess: async () => {
      setDecision(null);
      setReason("");
      await refresh();
    },
  });
  const convert = useMutation({
    mutationFn: () => {
      if (!query.data) throw new Error("The submission is not available.");
      const selectedCustomer = effectiveCustomerId;
      const effectiveContactId =
        contactId || query.data.matched_contact || contacts.data?.results[0]?.id || "";
      const effectiveSalesperson = salespersonId || query.data.assigned_to || "";
      const effectiveCurrency = currencyId || currencies.data?.results[0]?.id || "";
      if (!effectiveSalesperson) throw new Error("Choose the responsible salesperson.");
      if (customerMode === "existing" && !selectedCustomer) {
        throw new Error("Choose an existing customer or create a new one.");
      }
      if (customerMode === "existing" && contactMode === "existing" && !effectiveContactId) {
        throw new Error("Choose an existing contact or create a new one.");
      }
      if (customerMode === "new" && !effectiveCurrency) {
        throw new Error("Choose the default currency for the new customer.");
      }
      if (query.data.attachments.length && !documentCategoryId) {
        throw new Error("Choose a document category for the incoming attachments.");
      }
      const contactName = splitName(newContactName || query.data.person_name);
      return apiPost<ExternalEnquirySubmission>(`/external-enquiries/${submissionId}/convert/`, {
        ...(customerMode === "existing"
          ? { customer_id: selectedCustomer }
          : {
              new_customer: {
                legal_name: newCustomerName || query.data.company_name || query.data.person_name,
                primary_email: query.data.email,
                primary_phone: query.data.phone,
                default_currency: effectiveCurrency,
                account_manager: effectiveSalesperson,
              },
            }),
        ...(customerMode === "existing" && contactMode === "existing"
          ? { contact_id: effectiveContactId }
          : {
              new_contact: {
                ...contactName,
                email: query.data.email,
                phone: query.data.phone,
                is_primary: customerMode === "new",
              },
            }),
        responsible_salesperson_id: effectiveSalesperson,
        priority,
        ...(followUpAt ? { follow_up_at: new Date(followUpAt).toISOString() } : {}),
        ...(documentCategoryId ? { document_category_id: documentCategoryId } : {}),
      });
    },
    onSuccess: refresh,
  });

  if (query.isPending) return <ERPLoadingState rows={10} />;
  if (query.isError) return <ERPErrorState message={query.error.message} />;
  const item = query.data;
  const terminal = ["CONVERTED", "REJECTED", "SPAM"].includes(item.review_status);
  const effectiveContactId = contactId || item.matched_contact || contacts.data?.results[0]?.id || "";
  const effectiveSalesperson = salespersonId || item.assigned_to || "";
  const effectiveCurrency = currencyId || currencies.data?.results[0]?.id || "";

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow={`Commercial CRM · ${item.channel_label || item.channel} intake review`}
        title={item.subject}
        description={`${item.external_submission_id} · Received ${formatDateTime(item.received_at)}`}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate("/app/crm/incoming-enquiries")}>
              <ArrowLeft data-icon="inline-start" /> Inbox
            </Button>
            {viewers.length ? (
              <span className="rounded-full border bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground">
                {viewers.length} active {viewers.length === 1 ? "viewer" : "viewers"}
              </span>
            ) : null}
            <ERPStatusBadge value={item.review_status} />
            {item.converted_enquiry ? (
              <Link to={`/app/crm/enquiries/${item.converted_enquiry}`}>
                <Button>
                  Open {item.converted_enquiry_number} <ArrowUpRight data-icon="inline-end" />
                </Button>
              </Link>
            ) : null}
          </>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <div className="rounded-lg border border-status-success/30 bg-status-success/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-status-success">1 · Captured</p>
          <p className="mt-1 text-sm">Original {(item.channel_label || item.channel).toLowerCase()} request stored</p>
        </div>
        <div className="hidden self-center text-muted-foreground lg:block">→</div>
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-primary">2 · Review</p>
          <p className="mt-1 text-sm">Match identity and assign ownership</p>
        </div>
        <div className="hidden self-center text-muted-foreground lg:block">→</div>
        <div className="rounded-lg border p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">3 · CRM enquiry</p>
          <p className="mt-1 text-sm">Atomic conversion with traceability</p>
        </div>
      </div>

      <MutationError error={(assign.error || takeOwnership.error || decide.error || convert.error) as Error | null} />

      <Tabs defaultValue="review" className="gap-4">
        <TabsList className="h-auto w-full justify-start overflow-x-auto">
          <TabsTrigger value="review">Review workspace</TabsTrigger>
          <TabsTrigger value="conversion">CRM conversion</TabsTrigger>
          <TabsTrigger value="provenance">Source & security</TabsTrigger>
        </TabsList>

        <TabsContent value="review" className="mt-0 grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.75fr)]">
          <div className="grid gap-4">
            <Card className="overflow-hidden">
              <CardHeader className="border-b bg-muted/30">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2"><MessageSquareText className="text-primary" /> Customer request</CardTitle>
                    <CardDescription>Original content preserved exactly as received.</CardDescription>
                  </div>
                  <div className="flex gap-2"><ERPStatusBadge value={item.priority} /><ERPStatusBadge value={item.spam_status} /></div>
                </div>
              </CardHeader>
              <CardContent className="grid gap-5 p-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Contact identity</p>
                    <p className="flex items-center gap-2 font-semibold"><UserRound className="size-4 text-primary" />{item.person_name}</p>
                    <p className="mt-2 flex items-center gap-2 text-sm"><Building2 className="size-4 text-muted-foreground" />{item.company_name || "Company not supplied"}</p>
                    <p className="mt-2 flex items-center gap-2 text-sm"><Mail className="size-4 text-muted-foreground" />{item.email || "Email not supplied"}</p>
                    <p className="mt-2 flex items-center gap-2 text-sm"><Phone className="size-4 text-muted-foreground" />{item.phone || "Phone not supplied"}</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Product context</p>
                    <p className="font-semibold">{item.product_name || "General enquiry"}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.product_reference || "No product reference"}</p>
                    {item.product_url ? <a className="mt-2 inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline" href={item.product_url} target="_blank" rel="noreferrer">Open product page <ExternalLink className="size-4" /></a> : null}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Message</p>
                  <div className="whitespace-pre-wrap rounded-lg border-l-4 border-l-primary bg-muted/30 p-4 text-sm leading-7">{item.message}</div>
                </div>
                {item.attachments.length ? (
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Quarantined attachments</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {item.attachments.map((attachment) => (
                        <div key={attachment.id} className="flex items-center gap-3 rounded-lg border p-3">
                          <FileText className="text-primary" />
                          <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{attachment.safe_display_filename}</p><p className="text-xs text-muted-foreground">{formatBytes(attachment.size_bytes)} · {attachment.mime_type}</p></div>
                          <ERPStatusBadge value={attachment.scan_status} />
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="text-status-warning" /> Duplicate intelligence</CardTitle><CardDescription>Deterministic customer and contact matches for human review.</CardDescription></CardHeader>
              <CardContent>
                {candidates.isPending ? <ERPLoadingState rows={3} /> : candidates.isError ? <ERPErrorState message={candidates.error.message} /> : !candidates.data?.customers.length && !candidates.data?.contacts.length ? (
                  <Alert><CheckCircle2 /><AlertTitle>No likely match found</AlertTitle><AlertDescription>This looks like a new customer or contact.</AlertDescription></Alert>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {candidates.data.customers.map((candidate) => (
                      <button key={candidate.id} type="button" onClick={() => { setCustomerMode("existing"); setCustomerId(candidate.id); }} className="rounded-lg border p-4 text-left hover:border-primary/50">
                        <div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{candidate.legal_name}</p><p className="text-xs text-muted-foreground">{candidate.customer_code}</p></div><ERPStatusBadge value={candidate.status} /></div>
                        <p className="mt-3 text-xs text-status-warning">{candidate.reasons.join(" · ")}</p>
                      </button>
                    ))}
                    {candidates.data.contacts.map((candidate) => (
                      <button key={candidate.id} type="button" onClick={() => { setCustomerMode("existing"); setContactMode("existing"); setCustomerId(candidate.customer_id); setContactId(candidate.id); }} className="rounded-lg border p-4 text-left hover:border-primary/50">
                        <p className="font-semibold">{candidate.display_name}</p><p className="text-xs text-muted-foreground">{candidate.customer_name} · {candidate.customer_code}</p><p className="mt-3 text-xs text-status-warning">{candidate.reasons.join(" · ")}</p>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid content-start gap-4">
            <Card className="border-primary/25">
              <CardHeader><CardTitle className="flex items-center gap-2"><UserRoundCheck className="text-primary" /> Ownership</CardTitle><CardDescription>Assign an active internal owner before conversion.</CardDescription></CardHeader>
              <CardContent className="grid gap-4">
                <Field><FieldLabel htmlFor="assign-owner">Sales owner</FieldLabel><NativeSelect id="assign-owner" value={assignEmployee || item.assigned_to || ""} onChange={(event) => setAssignEmployee(event.target.value)} disabled={terminal}><NativeSelectOption value="">Choose owner</NativeSelectOption>{employees.data?.results.map((employee) => <NativeSelectOption key={employee.id} value={employee.id}>{employee.display_name} · {employee.employee_code}</NativeSelectOption>)}</NativeSelect></Field>
                <Field><FieldLabel htmlFor="assign-priority">Priority</FieldLabel><NativeSelect id="assign-priority" value={priority} onChange={(event) => setPriority(event.target.value)} disabled={terminal}><NativeSelectOption value="LOW">Low</NativeSelectOption><NativeSelectOption value="NORMAL">Normal</NativeSelectOption><NativeSelectOption value="HIGH">High</NativeSelectOption><NativeSelectOption value="URGENT">Urgent</NativeSelectOption></NativeSelect></Field>
                {hasPermission(user, "crm.external_enquiry.assign") && !terminal ? <Button onClick={() => assign.mutate()} disabled={assign.isPending || !(assignEmployee || item.assigned_to)}>{assign.isPending ? "Assigning…" : item.assigned_to ? "Update assignment" : "Assign for review"}</Button> : null}
                {hasPermission(user, "crm.external_enquiry.assign") && !terminal && !item.assigned_to ? <Button variant="outline" onClick={() => takeOwnership.mutate()} disabled={takeOwnership.isPending}>{takeOwnership.isPending ? "Taking ownership…" : "Take ownership"}</Button> : null}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Review decision</CardTitle><CardDescription>Terminal decisions require a reason and remain in audit history.</CardDescription></CardHeader>
              <CardContent className="grid gap-2">
                {item.review_status === "REJECTED" || item.review_status === "SPAM" ? (
                  <><Alert><CircleAlert /><AlertTitle>{item.review_status === "SPAM" ? "Marked as spam" : "Rejected"}</AlertTitle><AlertDescription>{item.rejection_reason}</AlertDescription></Alert>{hasPermission(user, "crm.external_enquiry.review") ? <Button variant="outline" onClick={() => setDecision("restore-for-review")}>Restore for review</Button> : null}</>
                ) : item.review_status === "CONVERTED" ? (
                  <Alert><FileCheck2 /><AlertTitle>Converted to CRM</AlertTitle><AlertDescription>{item.converted_enquiry_number} was created atomically on {formatDateTime(item.converted_at)}.</AlertDescription></Alert>
                ) : (
                  <>{hasPermission(user, "crm.external_enquiry.reject") ? <Button variant="outline" onClick={() => setDecision("reject")}>Reject enquiry</Button> : null}{hasPermission(user, "crm.external_enquiry.mark_spam") ? <Button variant="outline" onClick={() => setDecision("mark-spam")}>Mark as spam</Button> : null}</>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="conversion" className="mt-0">
          <Card className="border-primary/30">
            <CardHeader className="border-b bg-primary/[0.03]"><CardTitle>Controlled CRM conversion</CardTitle><CardDescription>Create or select the customer and contact, assign sales ownership, and generate exactly one numbered enquiry.</CardDescription></CardHeader>
            <CardContent className="grid gap-6 p-5">
              {item.review_status === "CONVERTED" ? <Alert><CheckCircle2 /><AlertTitle>Conversion complete</AlertTitle><AlertDescription>The submission is locked and linked to {item.converted_enquiry_number}.</AlertDescription></Alert> : null}
              <div className="grid gap-5 xl:grid-cols-2">
                <div className="grid gap-4 rounded-lg border p-4">
                  <div><p className="font-semibold">1. Customer</p><p className="text-sm text-muted-foreground">Reuse a verified record or create a controlled CRM customer.</p></div>
                  <Field><FieldLabel htmlFor="customer-mode">Customer action</FieldLabel><NativeSelect id="customer-mode" value={customerMode} onChange={(event) => { const mode = event.target.value as "existing" | "new"; setCustomerMode(mode); if (mode === "new") setContactMode("new"); }} disabled={terminal}><NativeSelectOption value="existing">Use existing customer</NativeSelectOption><NativeSelectOption value="new">Create new customer</NativeSelectOption></NativeSelect></Field>
                  {customerMode === "existing" ? <Field><FieldLabel htmlFor="conversion-customer">Existing customer</FieldLabel><NativeSelect id="conversion-customer" value={effectiveCustomerId} onChange={(event) => { setCustomerId(event.target.value); setContactId(""); }} disabled={terminal}><NativeSelectOption value="">Choose customer</NativeSelectOption>{customers.data?.results.map((customer) => <NativeSelectOption key={customer.id} value={customer.id}>{customer.legal_name} · {customer.customer_code}</NativeSelectOption>)}</NativeSelect><FieldDescription>Likely matches are preselected when available.</FieldDescription></Field> : <><Field><FieldLabel htmlFor="new-customer-name">Legal name</FieldLabel><Input id="new-customer-name" value={newCustomerName || item.company_name} onChange={(event) => setNewCustomerName(event.target.value)} disabled={terminal} /></Field><Field><FieldLabel htmlFor="new-customer-currency">Default currency</FieldLabel><NativeSelect id="new-customer-currency" value={effectiveCurrency} onChange={(event) => setCurrencyId(event.target.value)} disabled={terminal}><NativeSelectOption value="">Choose currency</NativeSelectOption>{currencies.data?.results.map((currency) => <NativeSelectOption key={currency.id} value={currency.id}>{currency.code || currency.name}</NativeSelectOption>)}</NativeSelect></Field></>}
                </div>

                <div className="grid gap-4 rounded-lg border p-4">
                  <div><p className="font-semibold">2. Contact</p><p className="text-sm text-muted-foreground">Link the request to the correct customer contact.</p></div>
                  {customerMode === "existing" ? <Field><FieldLabel htmlFor="contact-mode">Contact action</FieldLabel><NativeSelect id="contact-mode" value={contactMode} onChange={(event) => setContactMode(event.target.value as "existing" | "new")} disabled={terminal}><NativeSelectOption value="existing">Use existing contact</NativeSelectOption><NativeSelectOption value="new">Create new contact</NativeSelectOption></NativeSelect></Field> : null}
                  {customerMode === "existing" && contactMode === "existing" ? <Field><FieldLabel htmlFor="conversion-contact">Existing contact</FieldLabel><NativeSelect id="conversion-contact" value={effectiveContactId} onChange={(event) => setContactId(event.target.value)} disabled={terminal || !effectiveCustomerId}><NativeSelectOption value="">Choose contact</NativeSelectOption>{contacts.data?.results.map((contact) => <NativeSelectOption key={contact.id} value={contact.id}>{contact.display_name} · {contact.email || contact.phone}</NativeSelectOption>)}</NativeSelect></Field> : <><Field><FieldLabel htmlFor="new-contact-name">Contact name</FieldLabel><Input id="new-contact-name" value={newContactName || item.person_name} onChange={(event) => setNewContactName(event.target.value)} disabled={terminal} /></Field><div className="grid gap-2 text-sm text-muted-foreground"><span className="flex items-center gap-2"><Mail className="size-4" />{item.email || "No email supplied"}</span><span className="flex items-center gap-2"><Phone className="size-4" />{item.phone || "No phone supplied"}</span></div></>}
                </div>
              </div>

              <div className="grid gap-5 rounded-lg border p-4 md:grid-cols-2 xl:grid-cols-4">
                <Field><FieldLabel htmlFor="conversion-owner">Responsible salesperson</FieldLabel><NativeSelect id="conversion-owner" value={effectiveSalesperson} onChange={(event) => setSalespersonId(event.target.value)} disabled={terminal}><NativeSelectOption value="">Choose owner</NativeSelectOption>{employees.data?.results.map((employee) => <NativeSelectOption key={employee.id} value={employee.id}>{employee.display_name}</NativeSelectOption>)}</NativeSelect></Field>
                <Field><FieldLabel htmlFor="conversion-priority">Priority</FieldLabel><NativeSelect id="conversion-priority" value={priority} onChange={(event) => setPriority(event.target.value)} disabled={terminal}><NativeSelectOption value="LOW">Low</NativeSelectOption><NativeSelectOption value="NORMAL">Normal</NativeSelectOption><NativeSelectOption value="HIGH">High</NativeSelectOption><NativeSelectOption value="URGENT">Urgent</NativeSelectOption></NativeSelect></Field>
                <Field><FieldLabel htmlFor="conversion-follow-up">First follow-up</FieldLabel><Input id="conversion-follow-up" type="datetime-local" value={followUpAt} onChange={(event) => setFollowUpAt(event.target.value)} disabled={terminal} /></Field>
                {item.attachments.length ? <Field><FieldLabel htmlFor="conversion-category">Attachment category</FieldLabel><NativeSelect id="conversion-category" value={documentCategoryId} onChange={(event) => setDocumentCategoryId(event.target.value)} disabled={terminal}><NativeSelectOption value="">Choose category</NativeSelectOption>{categories.data?.results.map((category) => <NativeSelectOption key={category.id} value={category.id}>{category.name || category.code}</NativeSelectOption>)}</NativeSelect></Field> : <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground"><ShieldCheck className="mb-2 text-status-success" />No attachments require promotion.</div>}
              </div>
              {hasPermission(user, "crm.external_enquiry.convert") && !terminal ? <div className="flex justify-end"><Button size="lg" onClick={() => convert.mutate()} disabled={convert.isPending}>{convert.isPending ? "Creating controlled records…" : "Convert to CRM enquiry"}<ArrowUpRight data-icon="inline-end" /></Button></div> : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="provenance" className="mt-0 grid gap-4 xl:grid-cols-2">
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><Globe2 className="text-primary" /> Source attribution</CardTitle><CardDescription>The original source and wording remain available through every CRM transition.</CardDescription></CardHeader><CardContent><dl><DetailRow label="Source type" value={item.source_type.replaceAll("_", " ")} /><DetailRow label="Source page" value={item.source_page_url} /><DetailRow label="Referrer" value={item.referrer_url} /><DetailRow label="UTM source" value={item.utm_source} /><DetailRow label="UTM medium" value={item.utm_medium} /><DetailRow label="UTM campaign" value={item.utm_campaign} /></dl>{item.source_history?.length ? <><Separator className="my-4" /><div className="grid gap-3">{item.source_history.map((event) => <div key={event.id} className="rounded-lg border p-3"><div className="flex items-center justify-between gap-3"><ERPStatusBadge value={event.channel} /><span className="text-xs text-muted-foreground">{formatDateTime(event.created_at)}</span></div><p className="mt-2 text-sm font-medium">{event.source_reference || event.channel_label}</p><p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{event.original_message}</p></div>)}</div></> : null}</CardContent></Card>
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="text-status-success" /> Integration evidence</CardTitle><CardDescription>Trace identifiers and validation state; raw secrets and IP addresses are never displayed.</CardDescription></CardHeader><CardContent><dl><DetailRow label="Submission ID" value={item.external_submission_id} /><DetailRow label="Received" value={formatDateTime(item.received_at)} /><DetailRow label="Submitted" value={formatDateTime(item.submitted_at)} /><DetailRow label="Channel" value={item.channel} /><DetailRow label="Spam screen" value={item.spam_status} /><DetailRow label="Duplicate screen" value={item.duplicate_status} /></dl><Separator className="my-4" /><p className="flex items-start gap-2 text-xs leading-5 text-muted-foreground"><MapPin className="mt-0.5 size-4 shrink-0" />Source IPs are privacy-preserving hashes and signature secrets remain server-side environment configuration.</p></CardContent></Card>
        </TabsContent>
      </Tabs>

      <Dialog open={Boolean(decision)} onOpenChange={(open) => { if (!open) setDecision(null); }}>
        <DialogContent>
          <DialogHeader><DialogTitle>{decision === "mark-spam" ? "Mark this submission as spam?" : decision === "reject" ? "Reject this incoming enquiry?" : "Restore this enquiry for review?"}</DialogTitle><DialogDescription>This decision is recorded in the immutable audit history. Add a clear operational reason.</DialogDescription></DialogHeader>
          <Field><FieldLabel htmlFor="decision-reason">Reason</FieldLabel><Textarea id="decision-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain this review decision…" /></Field>
          <DialogFooter><Button variant="outline" onClick={() => setDecision(null)}>Cancel</Button><Button onClick={() => decide.mutate()} disabled={!reason.trim() || decide.isPending}>{decide.isPending ? "Saving…" : "Confirm decision"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
