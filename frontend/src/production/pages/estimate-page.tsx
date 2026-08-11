import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowUpRight,
  Calculator,
  ClipboardCheck,
  FileText,
  History,
  Pencil,
  Plus,
  RotateCcw,
  ShieldCheck,
  Trash2,
  TrendingUp,
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
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatDateTime,
} from "@/production/components/shared";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  CommercialEstimate,
  EstimateCostLine,
  EstimateWorkspace,
} from "@/production/lib/crm-types";

const categories = [
  "MATERIAL",
  "LABOUR",
  "MACHINE",
  "SUBCONTRACT",
  "ENGINEERING",
  "OVERHEAD",
  "PACKING",
  "FREIGHT",
  "INSTALLATION",
  "TRAVEL",
  "OTHER",
  "CONTINGENCY",
];

function money(value?: string, currency = "INR") {
  if (value === undefined) return "Restricted";
  return `${currency} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value))}`;
}

function PricingPanel({
  estimate,
  onSaved,
}: {
  estimate: CommercialEstimate;
  onSaved: () => Promise<void>;
}) {
  const [method, setMethod] = useState(estimate.pricing_method ?? "MARKUP");
  const [markup, setMarkup] = useState(estimate.markup_percent ?? "0");
  const [margin, setMargin] = useState(estimate.target_margin_percent ?? "0");
  const [manual, setManual] = useState(estimate.manual_selling_price ?? "");
  const [assumptions, setAssumptions] = useState(estimate.assumptions);
  const [exclusions, setExclusions] = useState(estimate.exclusions);
  const [notes, setNotes] = useState(estimate.commercial_notes);
  const [technical, setTechnical] = useState(estimate.technical_reference_summary);
  const save = useMutation({
    mutationFn: () =>
      apiPatch<CommercialEstimate>(`/commercial-estimates/${estimate.id}/details/`, {
        pricing_method: method,
        markup_percent: markup || "0",
        target_margin_percent: margin || "0",
        manual_selling_price: method === "MANUAL" ? manual || null : null,
        assumptions,
        exclusions,
        commercial_notes: notes,
        technical_reference_summary: technical,
      }),
    onSuccess: onSaved,
  });
  const editable = ["DRAFT", "IN_PREPARATION", "RETURNED_FOR_CHANGES"].includes(estimate.status);
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <Card className="border-primary/30">
        <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="text-primary" />Pricing logic</CardTitle><CardDescription>Server-authoritative selling price and gross margin.</CardDescription></CardHeader>
        <CardContent className="grid gap-4">
          <Field><FieldLabel htmlFor="pricing-method">Pricing method</FieldLabel><NativeSelect id="pricing-method" value={method} onChange={(event) => setMethod(event.target.value)} disabled={!editable}><NativeSelectOption value="MARKUP">Cost plus markup</NativeSelectOption><NativeSelectOption value="MARGIN">Target gross margin</NativeSelectOption><NativeSelectOption value="MANUAL">Manual selling price</NativeSelectOption></NativeSelect></Field>
          {method === "MARKUP" ? <Field><FieldLabel htmlFor="estimate-markup">Markup %</FieldLabel><Input id="estimate-markup" type="number" min="0" step="0.01" value={markup} onChange={(event) => setMarkup(event.target.value)} disabled={!editable} /><FieldDescription>Applied to the included total cost.</FieldDescription></Field> : null}
          {method === "MARGIN" ? <Field><FieldLabel htmlFor="estimate-margin">Target gross margin %</FieldLabel><Input id="estimate-margin" type="number" min="0" max="99.99" step="0.01" value={margin} onChange={(event) => setMargin(event.target.value)} disabled={!editable} /></Field> : null}
          {method === "MANUAL" ? <Field><FieldLabel htmlFor="estimate-manual-price">Manual selling price</FieldLabel><Input id="estimate-manual-price" type="number" min="0" step="0.01" value={manual} onChange={(event) => setManual(event.target.value)} disabled={!editable} /></Field> : null}
          <Separator />
          <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-lg border p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Calculated selling price</p><p className="mt-2 text-xl font-semibold text-primary">{money(estimate.proposed_selling_price, estimate.currency_code)}</p></div><div className="rounded-lg border p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Gross margin</p><p className="mt-2 text-xl font-semibold">{estimate.gross_margin_percent === undefined ? "Restricted" : `${Number(estimate.gross_margin_percent).toFixed(2)}%`}</p><p className="text-xs text-muted-foreground">{money(estimate.gross_margin_amount, estimate.currency_code)}</p></div></div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Commercial basis</CardTitle><CardDescription>Assumptions, exclusions, and technical handoff remain revision controlled.</CardDescription></CardHeader>
        <CardContent className="grid gap-4">
          <Field><FieldLabel htmlFor="technical-reference">Engineering reference</FieldLabel><Textarea id="technical-reference" value={technical} onChange={(event) => setTechnical(event.target.value)} disabled={!editable} rows={4} /></Field>
          <div className="grid gap-4 md:grid-cols-2"><Field><FieldLabel htmlFor="estimate-assumptions">Assumptions</FieldLabel><Textarea id="estimate-assumptions" value={assumptions} onChange={(event) => setAssumptions(event.target.value)} disabled={!editable} rows={5} /></Field><Field><FieldLabel htmlFor="estimate-exclusions">Exclusions</FieldLabel><Textarea id="estimate-exclusions" value={exclusions} onChange={(event) => setExclusions(event.target.value)} disabled={!editable} rows={5} /></Field></div>
          <Field><FieldLabel htmlFor="commercial-notes">Internal commercial notes</FieldLabel><Textarea id="commercial-notes" value={notes} onChange={(event) => setNotes(event.target.value)} disabled={!editable} rows={4} /></Field>
          {save.isError ? <ERPErrorState title="Estimate could not be saved" message={save.error.message} /> : null}
          {editable ? <div className="flex justify-end"><Button onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? "Recalculating…" : "Save & recalculate"}</Button></div> : <Alert><ShieldCheck /><AlertTitle>Revision locked</AlertTitle><AlertDescription>Pricing and commercial basis cannot be changed in this status.</AlertDescription></Alert>}
        </CardContent>
      </Card>
    </div>
  );
}

export default function EstimatePage() {
  const { estimateId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [lineOpen, setLineOpen] = useState(false);
  const [editingLine, setEditingLine] = useState<EstimateCostLine | null>(null);
  const [lineCategory, setLineCategory] = useState("MATERIAL");
  const [lineDescription, setLineDescription] = useState("");
  const [lineQuantity, setLineQuantity] = useState("1");
  const [lineUom, setLineUom] = useState("NOS");
  const [lineUnitCost, setLineUnitCost] = useState("");
  const [lineReference, setLineReference] = useState("");
  const [lineNotes, setLineNotes] = useState("");
  const [lineOptional, setLineOptional] = useState("false");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitComment, setSubmitComment] = useState("");
  const [reviseOpen, setReviseOpen] = useState(false);
  const [revisionReason, setRevisionReason] = useState("");
  const query = useQuery({
    queryKey: ["commercial-estimate-workspace", estimateId],
    queryFn: () => apiGet<EstimateWorkspace>(`/commercial-estimates/${estimateId}/workspace/`),
    enabled: Boolean(estimateId),
  });
  const revisions = useQuery({
    queryKey: ["commercial-estimate-revisions", estimateId],
    queryFn: () => apiGet<CommercialEstimate[]>(`/commercial-estimates/${estimateId}/revisions/`),
    enabled: Boolean(estimateId),
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["commercial-estimate-workspace", estimateId] }),
      queryClient.invalidateQueries({ queryKey: ["commercial-estimate-revisions", estimateId] }),
      queryClient.invalidateQueries({ queryKey: ["commercial-estimates"] }),
    ]);
  };
  const saveLine = useMutation({
    mutationFn: () => {
      const body = { category: lineCategory, description: lineDescription, quantity: lineQuantity, unit_of_measure: lineUom, unit_cost: lineUnitCost, source_reference: lineReference, notes: lineNotes, is_optional: lineOptional === "true" };
      return editingLine ? apiPatch<EstimateCostLine>(`/estimate-cost-lines/${editingLine.id}/`, body) : apiPost<EstimateCostLine>("/estimate-cost-lines/", { estimate_id: estimateId, ...body });
    },
    onSuccess: async () => { setLineOpen(false); setEditingLine(null); await refresh(); },
  });
  const removeLine = useMutation({
    mutationFn: (lineId: string) => apiDelete<void>(`/estimate-cost-lines/${lineId}/`),
    onSuccess: refresh,
  });
  const submit = useMutation({
    mutationFn: () => apiPost<CommercialEstimate>(`/commercial-estimates/${estimateId}/submit/`, { comment: submitComment }),
    onSuccess: async () => { setSubmitOpen(false); await refresh(); },
  });
  const revise = useMutation({
    mutationFn: () => apiPost<CommercialEstimate>(`/commercial-estimates/${estimateId}/revise/`, { reason: revisionReason }),
    onSuccess: async (estimate) => { await queryClient.invalidateQueries({ queryKey: ["commercial-estimates"] }); navigate(`/app/crm/estimates/${estimate.id}`, { replace: true }); },
  });

  const openNewLine = () => {
    setEditingLine(null); setLineCategory("MATERIAL"); setLineDescription(""); setLineQuantity("1"); setLineUom("NOS"); setLineUnitCost(""); setLineReference(""); setLineNotes(""); setLineOptional("false"); setLineOpen(true);
  };
  const openEditLine = (line: EstimateCostLine) => {
    setEditingLine(line); setLineCategory(line.category); setLineDescription(line.description); setLineQuantity(line.quantity); setLineUom(line.unit_of_measure); setLineUnitCost(line.unit_cost); setLineReference(line.source_reference); setLineNotes(line.notes); setLineOptional(String(line.is_optional)); setLineOpen(true);
  };

  if (query.isPending) return <ERPLoadingState rows={10} />;
  if (query.isError) return <ERPErrorState message={query.error.message} />;
  const { estimate, approvals, documents, timeline } = query.data;
  const lines = estimate.cost_lines ?? [];
  const editable = ["DRAFT", "IN_PREPARATION", "RETURNED_FOR_CHANGES"].includes(estimate.status);
  const canEdit = editable && hasPermission(user, "estimation.estimate.edit");
  const totals = Object.entries(estimate.category_totals ?? {});
  const maxCategory = Math.max(...totals.map(([, value]) => Number(value)), 1);

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM · Estimate workspace"
        title={`${estimate.estimate_number} · Revision ${estimate.revision_number}`}
        description={`${estimate.customer_name} · ${estimate.enquiry_number} · ${estimate.enquiry_subject}`}
        actions={<><Button variant="outline" onClick={() => navigate("/app/crm/estimates")}><ArrowLeft data-icon="inline-start" />Estimate register</Button><ERPStatusBadge value={estimate.status} />{estimate.approval_request ? <Link to={`/app/approvals/${estimate.approval_request}`}><Button variant="outline"><ClipboardCheck data-icon="inline-start" />Approval</Button></Link> : null}{editable && hasPermission(user, "estimation.estimate.submit") ? <Button onClick={() => setSubmitOpen(true)} disabled={!lines.length}><ShieldCheck data-icon="inline-start" />Submit for approval</Button> : null}{["APPROVED", "REJECTED", "RETURNED_FOR_CHANGES"].includes(estimate.status) && estimate.is_current && hasPermission(user, "estimation.estimate.revise") ? <Button onClick={() => setReviseOpen(true)}><RotateCcw data-icon="inline-start" />New revision</Button> : null}</>}
      />

      <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        {[{ step: "1 · Engineering", text: `Feasible · Rev ${estimate.engineering_review_revision}`, active: false }, { step: "2 · Cost build-up", text: `${lines.length} controlled lines`, active: editable }, { step: "3 · Approval", text: estimate.approval_status || "Not submitted", active: estimate.status === "PENDING_APPROVAL" }, { step: "4 · Commercial release", text: estimate.status === "APPROVED" ? "Approved" : "Awaiting approval", active: estimate.status === "APPROVED" }].map((item) => <div key={item.step} className={`rounded-lg border p-4 ${item.active ? "border-primary/40 bg-primary/5" : ""}`}><p className={`text-xs font-semibold uppercase tracking-[0.12em] ${item.active ? "text-primary" : "text-muted-foreground"}`}>{item.step}</p><p className="mt-1 text-sm">{item.text}</p></div>).flatMap((item, index) => index < 3 ? [item, <div key={`arrow-${index}`} className="hidden self-center text-muted-foreground lg:block">→</div>] : [item])}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Included cost</p><p className="mt-2 text-xl font-semibold">{money(estimate.total_cost, estimate.currency_code)}</p><p className="mt-1 text-xs text-muted-foreground">Optional lines excluded</p></CardContent></Card>
        <Card className="border-primary/30"><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Proposed selling price</p><p className="mt-2 text-xl font-semibold text-primary">{money(estimate.proposed_selling_price, estimate.currency_code)}</p><p className="mt-1 text-xs text-muted-foreground">{estimate.pricing_method?.replaceAll("_", " ") ?? "Restricted"}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Gross margin</p><p className="mt-2 text-xl font-semibold">{estimate.gross_margin_percent === undefined ? "Restricted" : `${Number(estimate.gross_margin_percent).toFixed(2)}%`}</p><p className="mt-1 text-xs text-muted-foreground">{money(estimate.gross_margin_amount, estimate.currency_code)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Commercial owner</p><p className="mt-2 text-lg font-semibold">{estimate.prepared_by_name}</p><p className="mt-1 text-xs text-muted-foreground">Sales: {estimate.sales_owner_name}</p></CardContent></Card>
      </div>

      {(saveLine.error || removeLine.error || submit.error || revise.error) ? <ERPErrorState title="Action could not be completed" message={(saveLine.error || removeLine.error || submit.error || revise.error)?.message ?? "Unknown error"} /> : null}

      <Tabs defaultValue="costs" className="gap-4">
        <TabsList className="h-auto w-full justify-start overflow-x-auto"><TabsTrigger value="costs">Cost build-up</TabsTrigger><TabsTrigger value="pricing">Pricing & basis</TabsTrigger><TabsTrigger value="approval">Approval & revisions</TabsTrigger><TabsTrigger value="evidence">Documents & history</TabsTrigger></TabsList>

        <TabsContent value="costs" className="mt-0 grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.5fr)]">
          <Card><CardHeader className="gap-3 sm:flex-row sm:items-end sm:justify-between"><div><CardTitle>Cost lines</CardTitle><CardDescription>Quantity × unit cost is calculated and rounded by the server.</CardDescription></div>{canEdit ? <Button onClick={openNewLine}><Plus data-icon="inline-start" />Add cost line</Button> : null}</CardHeader><CardContent>{!lines.length ? <ERPEmptyState title="No cost lines yet" description="Add material, labour, engineering, freight, and other cost inputs." action={canEdit ? <Button onClick={openNewLine}>Add first cost line</Button> : undefined} /> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>#</TableHead><TableHead>Category / description</TableHead><TableHead>Qty</TableHead><TableHead>Unit cost</TableHead><TableHead>Amount</TableHead><TableHead>Basis</TableHead><TableHead><span className="sr-only">Actions</span></TableHead></TableRow></TableHeader><TableBody>{lines.map((line) => <TableRow key={line.id} className={line.is_optional ? "opacity-60" : ""}><TableCell>{line.line_number}</TableCell><TableCell><div className="flex items-center gap-2"><ERPStatusBadge value={line.category} />{line.is_optional ? <ERPStatusBadge value="OPTIONAL" /> : null}</div><p className="mt-1 font-medium">{line.description}</p>{line.notes ? <p className="text-xs text-muted-foreground">{line.notes}</p> : null}</TableCell><TableCell className="whitespace-nowrap">{Number(line.quantity).toLocaleString("en-IN")} {line.unit_of_measure}</TableCell><TableCell>{money(line.unit_cost, estimate.currency_code)}</TableCell><TableCell className="font-semibold">{money(line.amount, estimate.currency_code)}</TableCell><TableCell className="max-w-44 text-xs text-muted-foreground">{line.source_reference || "Manual basis"}</TableCell><TableCell>{canEdit ? <div className="flex"><Button aria-label={`Edit line ${line.line_number}`} variant="ghost" size="icon" onClick={() => openEditLine(line)}><Pencil /></Button><Button aria-label={`Delete line ${line.line_number}`} variant="ghost" size="icon" onClick={() => removeLine.mutate(line.id)}><Trash2 /></Button></div> : null}</TableCell></TableRow>)}</TableBody></Table></div>}</CardContent></Card>
          <Card className="content-start"><CardHeader><CardTitle>Cost distribution</CardTitle><CardDescription>Included totals by category.</CardDescription></CardHeader><CardContent className="grid gap-4">{!totals.length ? <p className="text-sm text-muted-foreground">Distribution appears after included cost lines are added.</p> : totals.sort((a, b) => Number(b[1]) - Number(a[1])).map(([category, value]) => <div key={category}><div className="mb-1 flex justify-between gap-3 text-sm"><span>{category.replaceAll("_", " ")}</span><span className="font-medium">{money(value, estimate.currency_code)}</span></div><Progress value={Number(value) / maxCategory * 100} /></div>)}<Separator /><div className="flex justify-between text-sm font-semibold"><span>Included total</span><span>{money(estimate.total_cost, estimate.currency_code)}</span></div></CardContent></Card>
        </TabsContent>

        <TabsContent value="pricing" className="mt-0"><PricingPanel key={estimate.updated_at} estimate={estimate} onSaved={refresh} /></TabsContent>

        <TabsContent value="approval" className="mt-0 grid gap-4 xl:grid-cols-2">
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><ClipboardCheck className="text-primary" />Approval state</CardTitle><CardDescription>The shared approval engine owns approver resolution and decisions.</CardDescription></CardHeader><CardContent>{!approvals.length ? <ERPEmptyState title="Not submitted" description="Complete the cost and pricing basis, then submit this revision." /> : <div className="grid gap-3">{approvals.map((approval) => <Link key={approval.id} to={`/app/approvals/${approval.id}`} className="rounded-lg border p-4 hover:border-primary/50"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{approval.workflow_name}</p><p className="text-xs text-muted-foreground">Requested {formatDateTime(approval.requested_at)}</p></div><ERPStatusBadge value={approval.status} /></div><p className="mt-3 text-sm text-muted-foreground">{approval.current_step_name || approval.status_label}</p></Link>)}</div>}</CardContent></Card>
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><History className="text-primary" />Revision history</CardTitle><CardDescription>Approved snapshots stay preserved when a new revision is created.</CardDescription></CardHeader><CardContent className="grid gap-3">{revisions.isPending ? <ERPLoadingState rows={3} /> : revisions.data?.map((revision) => <button type="button" key={revision.id} onClick={() => navigate(`/app/crm/estimates/${revision.id}`)} className={`rounded-lg border p-4 text-left hover:border-primary/50 ${revision.id === estimate.id ? "border-primary/40 bg-primary/5" : ""}`}><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">Revision {revision.revision_number}</p><p className="text-xs text-muted-foreground">{formatDateTime(revision.created_at)} · {revision.prepared_by_name}</p></div><ERPStatusBadge value={revision.status} /></div><p className="mt-3 text-sm">{money(revision.proposed_selling_price, revision.currency_code)}</p></button>)}</CardContent></Card>
        </TabsContent>

        <TabsContent value="evidence" className="mt-0 grid gap-4 xl:grid-cols-2">
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><FileText className="text-primary" />Linked documents</CardTitle><CardDescription>Evidence linked to the enquiry, engineering review, or this estimate.</CardDescription></CardHeader><CardContent>{!documents.length ? <ERPEmptyState title="No linked documents" description="Controlled documents can be linked through the shared document service." /> : <div className="grid gap-2">{documents.map((document) => <Link key={document.id} to={`/app/documents/${document.id}`} className="flex items-center justify-between rounded-lg border p-3 hover:border-primary/50"><div><p className="font-medium">{document.title}</p><p className="text-xs text-muted-foreground">{document.document_number} · {document.category_name}</p></div><ArrowUpRight /></Link>)}</div>}</CardContent></Card>
          <Card><CardHeader><CardTitle>Audit history</CardTitle><CardDescription>Immutable business events for this estimate revision.</CardDescription></CardHeader><CardContent>{!timeline.length ? <ERPEmptyState title="No visible history" description="History appears as controlled actions are completed." /> : <div className="relative grid gap-4 border-l pl-5">{timeline.map((event) => <div key={event.id} className="relative"><span className="absolute -left-[25px] top-1 size-2 rounded-full bg-primary" /><p className="text-sm font-medium">{event.summary}</p><p className="text-xs text-muted-foreground">{event.actor_name} · {formatDateTime(event.occurred_at)}</p></div>)}</div>}</CardContent></Card>
        </TabsContent>
      </Tabs>

      <Dialog open={lineOpen} onOpenChange={setLineOpen}><DialogContent className="max-h-[calc(100svh-2rem)] overflow-y-auto sm:max-w-2xl"><DialogHeader><DialogTitle>{editingLine ? `Edit cost line ${editingLine.line_number}` : "Add cost line"}</DialogTitle><DialogDescription>Enter the commercial cost basis. Amount is calculated by the server.</DialogDescription></DialogHeader><div className="grid gap-4 sm:grid-cols-2"><Field><FieldLabel htmlFor="line-category">Category</FieldLabel><NativeSelect id="line-category" value={lineCategory} onChange={(event) => setLineCategory(event.target.value)}>{categories.map((category) => <NativeSelectOption key={category} value={category}>{category.replaceAll("_", " ")}</NativeSelectOption>)}</NativeSelect></Field><Field><FieldLabel htmlFor="line-description">Description</FieldLabel><Input id="line-description" value={lineDescription} onChange={(event) => setLineDescription(event.target.value)} /></Field><Field><FieldLabel htmlFor="line-quantity">Quantity</FieldLabel><Input id="line-quantity" type="number" min="0.0001" step="0.0001" value={lineQuantity} onChange={(event) => setLineQuantity(event.target.value)} /></Field><Field><FieldLabel htmlFor="line-uom">Unit</FieldLabel><Input id="line-uom" value={lineUom} onChange={(event) => setLineUom(event.target.value)} /></Field><Field><FieldLabel htmlFor="line-unit-cost">Unit cost ({estimate.currency_code})</FieldLabel><Input id="line-unit-cost" type="number" min="0" step="0.0001" value={lineUnitCost} onChange={(event) => setLineUnitCost(event.target.value)} /></Field><Field><FieldLabel htmlFor="line-optional">Commercial inclusion</FieldLabel><NativeSelect id="line-optional" value={lineOptional} onChange={(event) => setLineOptional(event.target.value)}><NativeSelectOption value="false">Included in total</NativeSelectOption><NativeSelectOption value="true">Optional / excluded</NativeSelectOption></NativeSelect></Field><Field className="sm:col-span-2"><FieldLabel htmlFor="line-reference">Source / calculation reference</FieldLabel><Input id="line-reference" value={lineReference} onChange={(event) => setLineReference(event.target.value)} placeholder="Vendor quote, rate card, engineering hours…" /></Field><Field className="sm:col-span-2"><FieldLabel htmlFor="line-notes">Notes</FieldLabel><Textarea id="line-notes" value={lineNotes} onChange={(event) => setLineNotes(event.target.value)} /></Field></div><DialogFooter><Button variant="outline" onClick={() => setLineOpen(false)}>Cancel</Button><Button onClick={() => saveLine.mutate()} disabled={!lineDescription.trim() || !lineQuantity || !lineUnitCost || saveLine.isPending}><Calculator data-icon="inline-start" />{saveLine.isPending ? "Calculating…" : "Save cost line"}</Button></DialogFooter></DialogContent></Dialog>

      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}><DialogContent><DialogHeader><DialogTitle>Submit this estimate for approval?</DialogTitle><DialogDescription>The cost and margin snapshot will be copied into the shared approval request and this revision will lock.</DialogDescription></DialogHeader><Field><FieldLabel htmlFor="submit-comment">Submission comment</FieldLabel><Textarea id="submit-comment" value={submitComment} onChange={(event) => setSubmitComment(event.target.value)} placeholder="Summarize the commercial basis…" /></Field><Alert><ShieldCheck /><AlertTitle>Approval-controlled boundary</AlertTitle><AlertDescription>No quotation is created by this action. Quotation remains outside this milestone.</AlertDescription></Alert><DialogFooter><Button variant="outline" onClick={() => setSubmitOpen(false)}>Cancel</Button><Button onClick={() => submit.mutate()} disabled={submit.isPending}><ClipboardCheck data-icon="inline-start" />{submit.isPending ? "Submitting…" : "Submit estimate"}</Button></DialogFooter></DialogContent></Dialog>

      <Dialog open={reviseOpen} onOpenChange={setReviseOpen}><DialogContent><DialogHeader><DialogTitle>Create a new estimate revision?</DialogTitle><DialogDescription>The current revision stays in history and a new editable copy becomes current.</DialogDescription></DialogHeader><Field><FieldLabel htmlFor="revision-reason">Revision reason</FieldLabel><Textarea id="revision-reason" value={revisionReason} onChange={(event) => setRevisionReason(event.target.value)} placeholder="Explain what changed…" /></Field><DialogFooter><Button variant="outline" onClick={() => setReviseOpen(false)}>Cancel</Button><Button onClick={() => revise.mutate()} disabled={!revisionReason.trim() || revise.isPending}><RotateCcw data-icon="inline-start" />{revise.isPending ? "Creating…" : "Create revision"}</Button></DialogFooter></DialogContent></Dialog>
    </div>
  );
}
