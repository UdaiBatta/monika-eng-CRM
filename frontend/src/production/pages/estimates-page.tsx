import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Calculator,
  CheckCircle2,
  CircleDollarSign,
  Plus,
  Search,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatDateTime,
} from "@/production/components/shared";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  CommercialEstimate,
  EngineeringReview,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

function money(value?: string, currency = "INR") {
  if (value === undefined) return "Restricted";
  return `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value))}`;
}

export default function EstimatesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedEnquiry = searchParams.get("enquiry") ?? "";
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [showCreate, setShowCreate] = useState(Boolean(requestedEnquiry));
  const [enquiryId, setEnquiryId] = useState(requestedEnquiry);
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25", ordering: "-created_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    return next;
  }, [page, search, status]);
  const query = useQuery({
    queryKey: ["commercial-estimates", params.toString()],
    queryFn: () => apiGet<Paginated<CommercialEstimate>>(`/commercial-estimates/?${params}`),
  });
  const readyReviews = useQuery({
    queryKey: ["estimate-ready-engineering"],
    queryFn: () => apiGet<Paginated<EngineeringReview>>("/engineering-reviews/?current=true&status=FEASIBLE&page_size=100"),
    enabled: showCreate,
  });
  const eligible = (readyReviews.data?.results ?? []).filter((review) => review.ready_for_estimation);
  const create = useMutation({
    mutationFn: () => apiPost<CommercialEstimate>("/commercial-estimates/", { enquiry_id: enquiryId }),
    onSuccess: async (estimate) => {
      await queryClient.invalidateQueries({ queryKey: ["commercial-estimates"] });
      setShowCreate(false);
      navigate(`/app/crm/estimates/${estimate.id}`);
    },
  });
  const results = query.data?.results ?? [];
  const pending = results.filter((item) => item.status === "PENDING_APPROVAL").length;
  const approved = results.filter((item) => item.status === "APPROVED").length;
  const value = results.reduce((sum, item) => sum + Number(item.proposed_selling_price ?? 0), 0);

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM · Costing gate"
        title="Commercial estimates"
        description="Build auditable cost estimates from Workshop-approved requirements, apply controlled pricing, and route the commercial snapshot through approval."
        actions={hasPermission(user, "estimation.estimate.create") ? <Button onClick={() => setShowCreate(true)}><Plus data-icon="inline-start" />New estimate</Button> : undefined}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="border-primary/30"><CardContent className="relative p-4"><Calculator className="absolute right-4 top-4 size-8 text-primary/20" /><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Estimate register</p><p className="mt-2 text-2xl font-semibold">{query.data?.pagination.count ?? 0}</p><p className="mt-1 text-xs text-muted-foreground">Controlled revisions</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Pending approval</p><p className="mt-2 text-2xl font-semibold text-status-warning">{pending}</p><p className="mt-1 text-xs text-muted-foreground">Current page</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Approved</p><p className="mt-2 text-2xl font-semibold text-status-success">{approved}</p><p className="mt-1 text-xs text-muted-foreground">Commercially authorized</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Proposed value</p><p className="mt-2 text-xl font-semibold">{value ? money(String(value)) : "—"}</p><p className="mt-1 text-xs text-muted-foreground">Visible records on page</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div><CardTitle>Estimate register</CardTitle><CardDescription>One current revision per enquiry with complete approval and supersession history.</CardDescription></div>
          <div className="grid w-full gap-2 sm:grid-cols-[minmax(260px,1fr)_200px] xl:max-w-2xl">
            <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput); setPage(1); }}>
              <Field><FieldLabel htmlFor="estimate-search" className="sr-only">Search estimates</FieldLabel><Input id="estimate-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Estimate, enquiry, customer…" /></Field>
              <Button type="submit" variant="outline"><Search data-icon="inline-start" />Search</Button>
            </form>
            <Field><FieldLabel htmlFor="estimate-status" className="sr-only">Status</FieldLabel><NativeSelect id="estimate-status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><NativeSelectOption value="">All statuses</NativeSelectOption><NativeSelectOption value="DRAFT">Draft</NativeSelectOption><NativeSelectOption value="IN_PREPARATION">In preparation</NativeSelectOption><NativeSelectOption value="PENDING_APPROVAL">Pending approval</NativeSelectOption><NativeSelectOption value="APPROVED">Approved</NativeSelectOption><NativeSelectOption value="RETURNED_FOR_CHANGES">Returned</NativeSelectOption><NativeSelectOption value="REJECTED">Rejected</NativeSelectOption><NativeSelectOption value="SUPERSEDED">Superseded</NativeSelectOption></NativeSelect></Field>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? <ERPLoadingState rows={8} /> : query.isError ? <ERPErrorState message={query.error.message} /> : !results.length ? <ERPEmptyState title="No estimates found" description="Start from a Workshop-approved requirement to create the first controlled estimate." action={hasPermission(user, "estimation.estimate.create") ? <Button onClick={() => setShowCreate(true)}>New estimate</Button> : undefined} /> : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <Table><TableHeader><TableRow><TableHead>Estimate</TableHead><TableHead>Customer / enquiry</TableHead><TableHead>Status</TableHead><TableHead>Total cost</TableHead><TableHead>Proposed price</TableHead><TableHead>Margin</TableHead><TableHead>Prepared by</TableHead><TableHead><span className="sr-only">Open</span></TableHead></TableRow></TableHeader><TableBody>{results.map((estimate) => <TableRow key={estimate.id} className="cursor-pointer" onClick={() => navigate(`/app/crm/estimates/${estimate.id}`)}><TableCell><p className="font-semibold">{estimate.estimate_number}</p><p className="text-xs text-muted-foreground">Revision {estimate.revision_number} · {formatDateTime(estimate.updated_at)}</p></TableCell><TableCell><p className="font-medium">{estimate.customer_name}</p><p className="text-xs text-muted-foreground">{estimate.enquiry_number} · {estimate.enquiry_subject}</p></TableCell><TableCell><ERPStatusBadge value={estimate.status} /></TableCell><TableCell>{money(estimate.total_cost, estimate.currency_code)}</TableCell><TableCell className="font-semibold">{money(estimate.proposed_selling_price, estimate.currency_code)}</TableCell><TableCell>{estimate.gross_margin_percent === undefined ? "Restricted" : `${Number(estimate.gross_margin_percent).toFixed(2)}%`}</TableCell><TableCell>{estimate.prepared_by_name}</TableCell><TableCell><Button aria-label={`Open ${estimate.estimate_number}`} variant="ghost" size="icon"><ArrowUpRight /></Button></TableCell></TableRow>)}</TableBody></Table>
              </div>
              <div className="grid gap-3 md:hidden">{results.map((estimate) => <button key={estimate.id} type="button" onClick={() => navigate(`/app/crm/estimates/${estimate.id}`)} className="rounded-lg border p-4 text-left hover:border-primary/50"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{estimate.estimate_number} · Rev {estimate.revision_number}</p><p className="text-xs text-muted-foreground">{estimate.customer_name}</p></div><ERPStatusBadge value={estimate.status} /></div><p className="mt-3 text-sm">{estimate.enquiry_subject}</p><div className="mt-4 grid grid-cols-2 gap-3 text-xs"><div><p className="text-muted-foreground">Total cost</p><p className="font-semibold">{money(estimate.total_cost, estimate.currency_code)}</p></div><div><p className="text-muted-foreground">Proposed</p><p className="font-semibold text-primary">{money(estimate.proposed_selling_price, estimate.currency_code)}</p></div></div></button>)}</div>
            </>
          )}
          {query.data && query.data.pagination.pages > 1 ? <div className="mt-4 flex justify-end gap-3"><Button variant="outline" disabled={!query.data.pagination.previous} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="self-center text-sm text-muted-foreground">Page {page} of {query.data.pagination.pages}</span><Button variant="outline" disabled={!query.data.pagination.next} onClick={() => setPage((value) => value + 1)}>Next</Button></div> : null}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Start commercial estimation</DialogTitle><DialogDescription>Only enquiries with a current Workshop approval and no open clarifications are eligible.</DialogDescription></DialogHeader>
          {readyReviews.isPending ? <ERPLoadingState rows={3} /> : readyReviews.isError ? <ERPErrorState message={readyReviews.error.message} /> : !eligible.length ? <ERPEmptyState title="No enquiry is ready" description="Complete the Workshop Review first." /> : <Field><FieldLabel htmlFor="estimate-enquiry">Ready enquiry</FieldLabel><NativeSelect id="estimate-enquiry" value={enquiryId} onChange={(event) => setEnquiryId(event.target.value)}><NativeSelectOption value="">Choose enquiry</NativeSelectOption>{eligible.map((review) => <NativeSelectOption key={review.enquiry} value={review.enquiry}>{review.enquiry_number} · {review.customer_name} · {review.enquiry_subject}</NativeSelectOption>)}</NativeSelect><FieldDescription>The Workshop snapshot remains linked to the estimate revision.</FieldDescription></Field>}
          {create.isError ? <ERPErrorState title="Estimate could not be started" message={create.error.message} /> : null}
          <div className="grid grid-cols-3 gap-2 rounded-lg border bg-muted/30 p-3 text-center text-xs"><div><ShieldCheck className="mx-auto mb-1 text-status-success" />Workshop approved</div><div><TrendingUp className="mx-auto mb-1 text-primary" />Server priced</div><div><CheckCircle2 className="mx-auto mb-1 text-status-warning" />Approval controlled</div></div>
          <DialogFooter><Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button><Button onClick={() => create.mutate()} disabled={!enquiryId || create.isPending}><CircleDollarSign data-icon="inline-start" />{create.isPending ? "Starting…" : "Start estimate"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
