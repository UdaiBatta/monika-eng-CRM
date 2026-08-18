import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, FileCheck2, FileText, Plus, Search } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ERPDocumentUpload } from "@/production/pages/documents-page";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { Customer, Quotation, RelationOption } from "@/production/lib/crm-types";
import type { CustomerPO } from "@/production/lib/sales-types";
import type { ERPDocument, Paginated } from "@/production/lib/types";

const blankForm = { customer_id: "", po_number: "", po_date: new Date().toISOString().slice(0, 10), received_date: new Date().toISOString().slice(0, 10), quotation_id: "", currency_id: "", stated_total: "", supporting_document_id: "", delivery_information: "", payment_terms: "", notes: "" };

function money(value: string | null, currency = "INR") {
  return value ? `${currency} ${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "Not recorded";
}

export default function CustomerPOsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<CustomerPO | null>(null);
  const [form, setForm] = useState(blankForm);
  const params = useMemo(() => {
    const next = new URLSearchParams({ page_size: "50", ordering: "-updated_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    return next;
  }, [search, status]);
  const query = useQuery({ queryKey: ["customer-pos", params.toString()], queryFn: () => apiGet<Paginated<CustomerPO>>(`/sales/customer-pos/?${params}`) });
  const customers = useQuery({ queryKey: ["customer-po-customers"], queryFn: () => apiGet<Paginated<Customer>>("/customers/?page_size=100&ordering=legal_name"), enabled: open });
  const quotations = useQuery({ queryKey: ["customer-po-quotations"], queryFn: () => apiGet<Paginated<Quotation>>("/quotations/?status=READY_FOR_SALES_ORDER&page_size=100&ordering=-updated_at"), enabled: open });
  const currencies = useQuery({ queryKey: ["customer-po-currencies"], queryFn: () => apiGet<Paginated<RelationOption>>("/currencies/?is_active=true&page_size=100"), enabled: open });
  const create = useMutation({
    mutationFn: () => apiPost<CustomerPO>("/sales/customer-pos/", { ...form, quotation_id: form.quotation_id || null, currency_id: form.currency_id || null, stated_total: form.stated_total || null, supporting_document_id: form.supporting_document_id || null }),
    onSuccess: async (po) => { await queryClient.invalidateQueries({ queryKey: ["customer-pos"] }); setForm(blankForm); setOpen(false); setSelected(po); },
  });
  const review = useMutation({
    mutationFn: (id: string) => apiPost(`/sales/customer-pos/${id}/review-variance/`),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["customer-pos"] }); if (selected) setSelected((await apiGet<CustomerPO>(`/sales/customer-pos/${selected.id}/`))); },
  });
  const results = query.data?.results ?? [];
  const differences = results.filter((item) => item.current_revision.match_status === "DIFFERENCES").length;
  const update = (field: keyof typeof blankForm, value: string) => setForm((current) => ({ ...current, [field]: value }));

  return <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
    <ERPPageHeader eyebrow="Commercial CRM · Customer orders" title="Customer purchase orders" description="Record the customer’s formal PO, preserve revisions, and review differences without blocking genuine verbal orders." actions={hasPermission(user, "sales.customer_po.create") ? <Button onClick={() => setOpen(true)}><Plus data-icon="inline-start" />Record Customer PO</Button> : undefined} />
    <div className="grid gap-4 sm:grid-cols-3">
      <Card className="border-primary/30"><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">PO register</p><p className="mt-2 text-2xl font-semibold">{query.data?.pagination.count ?? 0}</p><p className="text-xs text-muted-foreground">Controlled customer records</p></CardContent></Card>
      <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Needs review</p><p className="mt-2 text-2xl font-semibold text-status-warning">{differences}</p><p className="text-xs text-muted-foreground">Commercial differences visible</p></CardContent></Card>
      <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Simple rule</p><p className="mt-2 font-semibold">PO can arrive later</p><p className="text-xs text-muted-foreground">A confirmed order is not lost</p></CardContent></Card>
    </div>
    <Card><CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between"><div><CardTitle>Customer PO register</CardTitle><CardDescription>Open a record to see its document, revision history, and quotation comparison.</CardDescription></div><div className="flex w-full gap-2 lg:max-w-2xl"><form className="flex flex-1 gap-2" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput); }}><Input aria-label="Search customer purchase orders" placeholder="PO number, customer, quotation…" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} /><Button type="submit" variant="outline"><Search /></Button></form><NativeSelect aria-label="PO status" value={status} onChange={(event) => setStatus(event.target.value)}><NativeSelectOption value="">All statuses</NativeSelectOption><NativeSelectOption value="ACTIVE">Active</NativeSelectOption><NativeSelectOption value="SUPERSEDED">Superseded</NativeSelectOption><NativeSelectOption value="CANCELLED">Cancelled</NativeSelectOption></NativeSelect></div></CardHeader><CardContent>
      {query.isPending ? <ERPLoadingState rows={7} /> : query.isError ? <ERPErrorState message={query.error.message} /> : !results.length ? <ERPEmptyState title="No customer POs found" description="Use Record Customer PO when a formal order arrives. Sales Orders may still be created with PO Pending when policy allows." /> : <><div className="hidden overflow-x-auto md:block"><Table><TableHeader><TableRow><TableHead>PO / customer</TableHead><TableHead>Quotation</TableHead><TableHead>Value</TableHead><TableHead>Match</TableHead><TableHead>Revision</TableHead><TableHead>Updated</TableHead><TableHead /></TableRow></TableHeader><TableBody>{results.map((po) => <TableRow key={po.id} className="cursor-pointer" onClick={() => setSelected(po)}><TableCell><p className="font-semibold">{po.po_number}</p><p className="text-xs text-muted-foreground">{po.customer_name}</p></TableCell><TableCell>{po.quotation_number || "Not linked"}</TableCell><TableCell>{money(po.current_revision.stated_total, po.current_revision.currency_code)}</TableCell><TableCell><ERPStatusBadge value={po.current_revision.match_status} label={po.current_revision.match_status_label} /></TableCell><TableCell>Rev {po.current_revision.revision_number}</TableCell><TableCell>{formatDateTime(po.updated_at)}</TableCell><TableCell><Button variant="ghost" size="icon" aria-label={`Open PO ${po.po_number}`}><ArrowUpRight /></Button></TableCell></TableRow>)}</TableBody></Table></div><div className="grid gap-3 md:hidden">{results.map((po) => <button key={po.id} onClick={() => setSelected(po)} className="rounded-lg border p-4 text-left"><div className="flex justify-between gap-3"><div><p className="font-semibold">{po.po_number}</p><p className="text-xs text-muted-foreground">{po.customer_name}</p></div><ERPStatusBadge value={po.current_revision.match_status} /></div><p className="mt-3 text-sm">{money(po.current_revision.stated_total, po.current_revision.currency_code)} · Rev {po.current_revision.revision_number}</p></button>)}</div></>}
    </CardContent></Card>

    <Dialog open={open} onOpenChange={setOpen}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"><DialogHeader><DialogTitle>Record Customer PO</DialogTitle><DialogDescription>Only the practical essentials are shown. Attach the original document so the commercial record stays complete.</DialogDescription></DialogHeader><div className="grid gap-4 sm:grid-cols-2">
      <Field className="sm:col-span-2"><FieldLabel htmlFor="po-customer">Customer</FieldLabel><NativeSelect id="po-customer" value={form.customer_id} onChange={(event) => update("customer_id", event.target.value)}><NativeSelectOption value="">Choose customer</NativeSelectOption>{customers.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.legal_name} · {item.customer_code}</NativeSelectOption>)}</NativeSelect></Field>
      <Field><FieldLabel htmlFor="po-number">PO number</FieldLabel><Input id="po-number" value={form.po_number} onChange={(event) => update("po_number", event.target.value)} /></Field><Field><FieldLabel htmlFor="po-date">PO date</FieldLabel><Input id="po-date" type="date" value={form.po_date} onChange={(event) => update("po_date", event.target.value)} /></Field>
      <Field><FieldLabel htmlFor="po-received">Received date</FieldLabel><Input id="po-received" type="date" value={form.received_date} onChange={(event) => update("received_date", event.target.value)} /></Field><Field><FieldLabel htmlFor="po-value">PO value</FieldLabel><Input id="po-value" type="number" min="0" step="0.01" value={form.stated_total} onChange={(event) => update("stated_total", event.target.value)} /></Field>
      <Field><FieldLabel htmlFor="po-currency">Currency</FieldLabel><NativeSelect id="po-currency" value={form.currency_id} onChange={(event) => update("currency_id", event.target.value)}><NativeSelectOption value="">Customer default</NativeSelectOption>{currencies.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.code || item.name}</NativeSelectOption>)}</NativeSelect></Field><Field><FieldLabel htmlFor="po-quote">Related quotation</FieldLabel><NativeSelect id="po-quote" value={form.quotation_id} onChange={(event) => update("quotation_id", event.target.value)}><NativeSelectOption value="">Not linked</NativeSelectOption>{quotations.data?.results.filter((item) => !form.customer_id || item.customer === form.customer_id).map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.quotation_number} · {item.customer_name}</NativeSelectOption>)}</NativeSelect></Field>
      <Field className="sm:col-span-2"><FieldLabel>PO document</FieldLabel><div className="flex flex-wrap items-center gap-3 rounded-lg border p-3">{form.supporting_document_id ? <p className="flex flex-1 items-center gap-2 text-sm font-medium text-status-success"><FileCheck2 />Document attached</p> : <p className="flex-1 text-sm text-muted-foreground">Upload the PDF, scan, image, or DOCX received from the customer.</p>}<ERPDocumentUpload onUploaded={(document: ERPDocument) => update("supporting_document_id", document.id)} /></div></Field>
      <details className="sm:col-span-2 rounded-lg border p-4"><summary className="cursor-pointer font-medium">More details</summary><div className="mt-4 grid gap-4 sm:grid-cols-2"><Field><FieldLabel htmlFor="po-delivery">Delivery requirement</FieldLabel><Input id="po-delivery" value={form.delivery_information} onChange={(event) => update("delivery_information", event.target.value)} /></Field><Field><FieldLabel htmlFor="po-payment">Payment terms</FieldLabel><Input id="po-payment" value={form.payment_terms} onChange={(event) => update("payment_terms", event.target.value)} /></Field><Field className="sm:col-span-2"><FieldLabel htmlFor="po-notes">Notes</FieldLabel><Textarea id="po-notes" value={form.notes} onChange={(event) => update("notes", event.target.value)} /></Field></div></details>
    </div>{create.isError ? <ERPErrorState title="Customer PO could not be saved" message={create.error.message} /> : null}<DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={() => create.mutate()} disabled={create.isPending || !form.customer_id || !form.po_number.trim() || !form.po_date}>{create.isPending ? "Saving…" : "Save Customer PO"}</Button></DialogFooter></DialogContent></Dialog>

    <Dialog open={Boolean(selected)} onOpenChange={(value) => !value && setSelected(null)}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">{selected ? <><DialogHeader><DialogTitle>{selected.po_number} · {selected.customer_name}</DialogTitle><DialogDescription>Customer PO record and preserved revision history.</DialogDescription></DialogHeader><div className="grid gap-4 sm:grid-cols-3"><Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Current value</p><p className="mt-1 font-semibold">{money(selected.current_revision.stated_total, selected.current_revision.currency_code)}</p></CardContent></Card><Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Quotation</p><p className="mt-1 font-semibold">{selected.quotation_number || "Not linked"}</p></CardContent></Card><Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Comparison</p><div className="mt-1"><ERPStatusBadge value={selected.current_revision.match_status} label={selected.current_revision.match_status_label} /></div></CardContent></Card></div>{selected.current_revision.variance_snapshot.length ? <Alert className="border-status-warning/40"><FileText /><AlertTitle>Differences need a person’s review</AlertTitle><AlertDescription><div className="mt-2 grid gap-2">{selected.current_revision.variance_snapshot.map((item) => <div key={item.field} className="rounded-md bg-background p-3"><p className="font-medium">{item.label}</p><p className="text-xs text-muted-foreground">Quotation: {String(item.quotation ?? "—")} · Customer PO: {String(item.customer_po ?? "—")}</p></div>)}</div></AlertDescription></Alert> : null}<Card><CardHeader><CardTitle>Revision history</CardTitle><CardDescription>Earlier PO documents and terms are never overwritten.</CardDescription></CardHeader><CardContent className="grid gap-3">{selected.revisions.map((revision) => <div key={revision.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"><div><p className="font-medium">Revision {revision.revision_number}{revision.customer_revision_reference ? ` · ${revision.customer_revision_reference}` : ""}</p><p className="text-xs text-muted-foreground">PO dated {revision.po_date} · received {revision.received_date}</p></div><div className="flex items-center gap-2"><ERPStatusBadge value={revision.match_status} />{revision.supporting_document ? <Link to={`/app/documents/${revision.supporting_document}`}><Button variant="outline" size="sm">Open document</Button></Link> : null}</div></div>)}</CardContent></Card><DialogFooter><Button variant="outline" onClick={() => setSelected(null)}>Close</Button>{selected.quotation && hasPermission(user, "sales.customer_po.review_variance") ? <Button onClick={() => review.mutate(selected.id)} disabled={review.isPending}>Compare with quotation</Button> : null}{selected.quotation ? <Button onClick={() => navigate(`/app/crm/quotations/${selected.quotation}`)}>Open quotation</Button> : null}</DialogFooter></> : null}</DialogContent></Dialog>
  </div>;
}
