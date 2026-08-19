import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, CircleDollarSign, FileText, Plus, Search, ShieldCheck, Zap } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasFeature, hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { CommercialEstimate, Customer, Quotation } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

const blankQuick = {
  customer_id: "",
  quick_reason: "",
  description: "",
  quantity: "1",
  unit_of_measure: "NOS",
  unit_price: "0",
  discount_percent: "0",
  tax_percent: "18",
};

function money(value: string, currency = "INR") {
  return `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value))}`;
}

export default function QuotationsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedEstimate = searchParams.get("estimate") ?? "";
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [path, setPath] = useState("");
  const queue = searchParams.get("queue") === "mine" ? "mine" : "team";
  const [showCreate, setShowCreate] = useState(Boolean(requestedEstimate));
  const [createPath, setCreatePath] = useState<"STANDARD" | "QUICK">("STANDARD");
  const [estimateId, setEstimateId] = useState(requestedEstimate);
  const [quick, setQuick] = useState(blankQuick);
  const quickQuotationEnabled = hasFeature(user, "quick_quotation");

  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25", ordering: "-updated_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    if (path) next.set("path", path);
    if (queue === "mine") next.set("queue", "mine");
    return next;
  }, [page, path, queue, search, status]);
  const query = useQuery({
    queryKey: ["quotations", params.toString()],
    queryFn: () => apiGet<Paginated<Quotation>>(`/quotations/?${params}`),
  });
  const estimates = useQuery({
    queryKey: ["quotation-approved-estimates"],
    queryFn: () => apiGet<Paginated<CommercialEstimate>>( "/commercial-estimates/?status=APPROVED&is_current=true&page_size=100&ordering=-approved_at"),
    enabled: showCreate && createPath === "STANDARD",
  });
  const customers = useQuery({
    queryKey: ["quotation-customers"],
    queryFn: () => apiGet<Paginated<Customer>>("/customers/?page_size=100&ordering=legal_name"),
    enabled: showCreate && createPath === "QUICK",
  });
  const selectedEstimate = estimates.data?.results.find((item) => item.id === estimateId);
  const create = useMutation({
    mutationFn: () => {
      if (createPath === "STANDARD" && selectedEstimate) {
        return apiPost<Quotation>("/quotations/", {
          path: "STANDARD",
          customer_id: selectedEstimate.customer_id,
          enquiry_id: selectedEstimate.enquiry,
          estimate_id: selectedEstimate.id,
        });
      }
      return apiPost<Quotation>("/quotations/", {
        path: "QUICK",
        customer_id: quick.customer_id,
        quick_reason: quick.quick_reason,
        lines: [{
          description: quick.description,
          quantity: quick.quantity,
          unit_of_measure: quick.unit_of_measure,
          unit_price: quick.unit_price,
          discount_percent: quick.discount_percent,
          tax_percent: quick.tax_percent,
        }],
      });
    },
    onSuccess: async (quotation) => {
      await queryClient.invalidateQueries({ queryKey: ["quotations"] });
      setShowCreate(false);
      setEstimateId("");
      setQuick(blankQuick);
      navigate(`/app/crm/quotations/${quotation.id}`);
    },
  });
  const results = query.data?.results ?? [];
  const draft = results.filter((item) => item.status === "DRAFT").length;
  const sent = results.filter((item) => item.status === "SENT" || item.status === "UNDER_NEGOTIATION").length;
  const accepted = results.filter((item) => ["ACCEPTED", "READY_FOR_SALES_ORDER"].includes(item.status)).length;

  const updateQuick = (field: keyof typeof blankQuick, value: string) => {
    setQuick((current) => ({ ...current, [field]: value }));
  };

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM · Controlled offers"
        title="Quotations"
        description="Prepare customer-facing commercial offers, preserve every revision, record the real communication channel, and carry accepted terms to the Sales Order handoff gate."
        actions={hasPermission(user, "crm.quotation.create") ? <Button onClick={() => setShowCreate(true)}><Plus data-icon="inline-start" />New quotation</Button> : undefined}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="border-primary/30"><CardContent className="relative p-4"><FileText className="absolute right-4 top-4 size-8 text-primary/20" /><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Quotation register</p><p className="mt-2 text-2xl font-semibold">{query.data?.pagination.count ?? 0}</p><p className="mt-1 text-xs text-muted-foreground">Current filtered records</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Draft</p><p className="mt-2 text-2xl font-semibold text-status-warning">{draft}</p><p className="mt-1 text-xs text-muted-foreground">Being prepared</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">With customer</p><p className="mt-2 text-2xl font-semibold text-status-info">{sent}</p><p className="mt-1 text-xs text-muted-foreground">Sent or negotiating</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Commercially accepted</p><p className="mt-2 text-2xl font-semibold text-status-success">{accepted}</p><p className="mt-1 text-xs text-muted-foreground">Ready for controlled handoff</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div><CardTitle>Commercial offer register</CardTitle><CardDescription>One live quotation record with immutable customer-facing revision history.</CardDescription></div>
          <div className="grid w-full gap-2 sm:grid-cols-2 xl:max-w-5xl xl:grid-cols-[minmax(240px,1fr)_180px_160px_140px]">
            <form className="flex gap-2 sm:col-span-2 xl:col-span-1" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput); setPage(1); }}>
              <Field><FieldLabel htmlFor="quotation-search" className="sr-only">Search quotations</FieldLabel><Input id="quotation-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Quotation, customer, enquiry…" /></Field>
              <Button type="submit" variant="outline"><Search data-icon="inline-start" />Search</Button>
            </form>
            <NativeSelect aria-label="Quotation status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><NativeSelectOption value="">All statuses</NativeSelectOption>{["DRAFT", "IN_APPROVAL", "APPROVED", "READY_TO_SEND", "SENT", "UNDER_NEGOTIATION", "ACCEPTED", "READY_FOR_SALES_ORDER", "REJECTED", "EXPIRED", "CANCELLED"].map((item) => <NativeSelectOption key={item} value={item}>{item.replaceAll("_", " ")}</NativeSelectOption>)}</NativeSelect>
            <NativeSelect aria-label="Quotation path" value={path} onChange={(event) => { setPath(event.target.value); setPage(1); }}><NativeSelectOption value="">All paths</NativeSelectOption><NativeSelectOption value="STANDARD">Standard</NativeSelectOption><NativeSelectOption value="QUICK">Quick</NativeSelectOption></NativeSelect>
            <NativeSelect aria-label="Quotation ownership" value={queue} onChange={(event) => { const value = event.target.value; setSearchParams(value === "mine" ? { queue: "mine" } : {}, { replace: true }); setPage(1); }}><NativeSelectOption value="team">Team</NativeSelectOption><NativeSelectOption value="mine">Mine</NativeSelectOption></NativeSelect>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? <ERPLoadingState rows={8} /> : query.isError ? <ERPErrorState message={query.error.message} /> : !results.length ? <ERPEmptyState title="No quotations found" description="Create a standard quotation from an approved estimate, or use the controlled quick path when permitted." /> : <>
            <div className="hidden overflow-x-auto md:block"><Table><TableHeader><TableRow><TableHead>Quotation</TableHead><TableHead>Customer / enquiry</TableHead><TableHead>Status</TableHead><TableHead>Revision</TableHead><TableHead>Total</TableHead><TableHead>Owner</TableHead><TableHead>Updated</TableHead><TableHead><span className="sr-only">Open</span></TableHead></TableRow></TableHeader><TableBody>{results.map((item) => <TableRow key={item.id} className="cursor-pointer" onClick={() => navigate(`/app/crm/quotations/${item.id}`)}><TableCell><p className="font-semibold">{item.quotation_number}</p><p className="text-xs text-muted-foreground">{item.path_label}</p></TableCell><TableCell><p className="font-medium">{item.customer_name}</p><p className="text-xs text-muted-foreground">{item.enquiry_number || "Direct quotation"}</p></TableCell><TableCell><ERPStatusBadge value={item.status} /></TableCell><TableCell>Rev {item.current_revision.revision_number}</TableCell><TableCell className="font-semibold">{money(item.current_revision.grand_total, item.current_revision.currency_code)}</TableCell><TableCell>{item.owner_name}</TableCell><TableCell>{formatDateTime(item.updated_at)}</TableCell><TableCell><Button variant="ghost" size="icon" aria-label={`Open ${item.quotation_number}`}><ArrowUpRight /></Button></TableCell></TableRow>)}</TableBody></Table></div>
            <div className="grid gap-3 md:hidden">{results.map((item) => <button key={item.id} type="button" onClick={() => navigate(`/app/crm/quotations/${item.id}`)} className="rounded-lg border p-4 text-left hover:border-primary/50"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{item.quotation_number}</p><p className="text-xs text-muted-foreground">{item.customer_name}</p></div><ERPStatusBadge value={item.status} /></div><div className="mt-4 flex items-end justify-between gap-3"><div><p className="text-xs text-muted-foreground">Rev {item.current_revision.revision_number} · {item.path_label}</p><p className="font-semibold">{money(item.current_revision.grand_total, item.current_revision.currency_code)}</p></div><ArrowUpRight className="size-4 text-primary" /></div></button>)}</div>
          </>}
          {query.data && query.data.pagination.pages > 1 ? <div className="mt-4 flex justify-end gap-3"><Button variant="outline" disabled={!query.data.pagination.previous} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="self-center text-sm text-muted-foreground">Page {page} of {query.data.pagination.pages}</span><Button variant="outline" disabled={!query.data.pagination.next} onClick={() => setPage((value) => value + 1)}>Next</Button></div> : null}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader><DialogTitle>Start a quotation</DialogTitle><DialogDescription>Use the approved-estimate path by default. Quick quotations are intentionally explicit and permission controlled.</DialogDescription></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => setCreatePath("STANDARD")} className={`rounded-lg border p-4 text-left ${createPath === "STANDARD" ? "border-primary bg-primary/[0.04]" : ""}`}><ShieldCheck className="mb-3 text-status-success" /><p className="font-semibold">Standard</p><p className="mt-1 text-xs text-muted-foreground">Approved estimate, customer-safe price only.</p></button>
            <button type="button" disabled={!hasPermission(user, "crm.quotation.quick_create") || !quickQuotationEnabled} onClick={() => setCreatePath("QUICK")} className={`rounded-lg border p-4 text-left disabled:cursor-not-allowed disabled:opacity-50 ${createPath === "QUICK" ? "border-primary bg-primary/[0.04]" : ""}`}><Zap className="mb-3 text-primary" /><p className="font-semibold">Quick</p><p className="mt-1 text-xs text-muted-foreground">{quickQuotationEnabled ? "Direct commercial offer with a mandatory reason." : "Disabled by the Owner; use an approved estimate."}</p></button>
          </div>
          {createPath === "STANDARD" ? (estimates.isPending ? <ERPLoadingState rows={3} /> : estimates.isError ? <ERPErrorState message={estimates.error.message} /> : <Field><FieldLabel htmlFor="quotation-estimate">Approved current estimate</FieldLabel><NativeSelect id="quotation-estimate" value={estimateId} onChange={(event) => setEstimateId(event.target.value)}><NativeSelectOption value="">Choose estimate</NativeSelectOption>{estimates.data?.results.map((estimate) => <NativeSelectOption key={estimate.id} value={estimate.id}>{estimate.estimate_number} · {estimate.customer_name} · {money(estimate.proposed_selling_price ?? "0", estimate.currency_code)}</NativeSelectOption>)}</NativeSelect><FieldDescription>Internal cost and margin are not copied to the quotation.</FieldDescription></Field>) : <div className="grid gap-4 sm:grid-cols-2">
            <Field className="sm:col-span-2"><FieldLabel htmlFor="quick-customer">Customer</FieldLabel><NativeSelect id="quick-customer" value={quick.customer_id} onChange={(event) => updateQuick("customer_id", event.target.value)}><NativeSelectOption value="">Choose customer</NativeSelectOption>{customers.data?.results.filter((customer) => ["ACTIVE", "PROSPECT"].includes(customer.status)).map((customer) => <NativeSelectOption key={customer.id} value={customer.id}>{customer.legal_name} · {customer.customer_code}</NativeSelectOption>)}</NativeSelect></Field>
            <Field className="sm:col-span-2"><FieldLabel htmlFor="quick-reason">Why is the quick path appropriate?</FieldLabel><Textarea id="quick-reason" value={quick.quick_reason} onChange={(event) => updateQuick("quick_reason", event.target.value)} placeholder="Explain the operational reason…" /></Field>
            <Field className="sm:col-span-2"><FieldLabel htmlFor="quick-description">Offer description</FieldLabel><Textarea id="quick-description" value={quick.description} onChange={(event) => updateQuick("description", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="quick-quantity">Quantity</FieldLabel><Input id="quick-quantity" type="number" min="0.0001" step="0.0001" value={quick.quantity} onChange={(event) => updateQuick("quantity", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="quick-uom">Unit</FieldLabel><Input id="quick-uom" value={quick.unit_of_measure} onChange={(event) => updateQuick("unit_of_measure", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="quick-price">Unit price</FieldLabel><Input id="quick-price" type="number" min="0" step="0.01" value={quick.unit_price} onChange={(event) => updateQuick("unit_price", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="quick-tax">Tax %</FieldLabel><Input id="quick-tax" type="number" min="0" max="100" step="0.01" value={quick.tax_percent} onChange={(event) => updateQuick("tax_percent", event.target.value)} /></Field>
          </div>}
          {create.isError ? <ERPErrorState title="Quotation could not be created" message={create.error.message} /> : null}
          <DialogFooter><Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button><Button onClick={() => create.mutate()} disabled={create.isPending || (createPath === "STANDARD" ? !selectedEstimate : !quick.customer_id || !quick.quick_reason.trim() || !quick.description.trim())}><CircleDollarSign data-icon="inline-start" />{create.isPending ? "Creating…" : "Create draft"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
