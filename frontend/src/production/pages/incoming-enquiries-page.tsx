import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Inbox, MessageSquareText, Phone, Plus, Search, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
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
import type { ExternalEnquirySubmission } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

const channels = ["TRADEINDIA", "WHATSAPP", "PHONE", "EMAIL", "IN_PERSON", "MANUAL", "OTHER"];

const blankCapture = {
  channel: "PHONE",
  source_reference: "",
  person_name: "",
  company_name: "",
  email: "",
  phone: "",
  subject: "",
  message: "",
  priority: "NORMAL",
};

export default function IncomingEnquiriesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [queue, setQueue] = useState("team");
  const [showCapture, setShowCapture] = useState(false);
  const [capture, setCapture] = useState(blankCapture);
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25", ordering: "-received_at" });
    if (search) next.set("search", search);
    if (status) next.set("review_status", status);
    if (channel) next.set("channel", channel);
    if (queue !== "team") next.set("queue", queue);
    return next;
  }, [channel, page, queue, search, status]);
  const query = useQuery({
    queryKey: ["incoming-enquiries", params.toString()],
    queryFn: () => apiGet<Paginated<ExternalEnquirySubmission>>(`/external-enquiries/?${params}`),
  });
  const create = useMutation({
    mutationFn: () => apiPost<ExternalEnquirySubmission>("/external-enquiries/manual-capture/", capture),
    onSuccess: async (item) => {
      await queryClient.invalidateQueries({ queryKey: ["incoming-enquiries"] });
      setShowCapture(false);
      setCapture(blankCapture);
      navigate(`/app/crm/incoming-enquiries/${item.id}`);
    },
  });
  const results = query.data?.results ?? [];
  const unassigned = results.filter((item) => !item.assigned_to).length;
  const duplicates = results.filter((item) => item.duplicate_status === "POSSIBLE").length;
  const website = results.filter((item) => item.channel === "WEBSITE").length;

  const updateCapture = (field: keyof typeof blankCapture, value: string) => {
    setCapture((current) => ({ ...current, [field]: value }));
  };

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM · Unified intake"
        title="Incoming enquiries"
        description="One controlled queue for website, TradeIndia, WhatsApp, phone, email, in-person and manual enquiries—with the original source preserved."
        actions={hasPermission(user, "crm.external_enquiry.review") ? (
          <Button onClick={() => setShowCapture(true)}><Plus data-icon="inline-start" />Capture enquiry</Button>
        ) : undefined}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="border-primary/30"><CardContent className="relative p-4"><Inbox className="absolute right-4 top-4 size-8 text-primary/20" /><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Incoming queue</p><p className="mt-2 text-2xl font-semibold">{query.data?.pagination.count ?? 0}</p><p className="mt-1 text-xs text-muted-foreground">Current filtered records</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Unassigned</p><p className="mt-2 text-2xl font-semibold text-status-warning">{unassigned}</p><p className="mt-1 text-xs text-muted-foreground">Shared sales queue</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Possible duplicates</p><p className="mt-2 text-2xl font-semibold text-status-warning">{duplicates}</p><p className="mt-1 text-xs text-muted-foreground">Human review required</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Website on page</p><p className="mt-2 text-2xl font-semibold text-status-info">{website}</p><p className="mt-1 text-xs text-muted-foreground">Signed integration records</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div><CardTitle>Review queue</CardTitle><CardDescription>Filter by source and ownership; conversion continues into the same controlled CRM enquiry.</CardDescription></div>
          <div className="grid w-full gap-2 sm:grid-cols-2 xl:max-w-5xl xl:grid-cols-[minmax(240px,1fr)_160px_160px_150px]">
            <form className="flex gap-2 sm:col-span-2 xl:col-span-1" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput); setPage(1); }}>
              <Field><FieldLabel htmlFor="incoming-search" className="sr-only">Search enquiries</FieldLabel><Input id="incoming-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Company, contact, subject…" /></Field>
              <Button type="submit" variant="outline"><Search data-icon="inline-start" />Search</Button>
            </form>
            <NativeSelect aria-label="Review status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><NativeSelectOption value="">All states</NativeSelectOption><NativeSelectOption value="NEW">New</NativeSelectOption><NativeSelectOption value="NEEDS_REVIEW">Needs review</NativeSelectOption><NativeSelectOption value="POSSIBLE_DUPLICATE">Possible duplicate</NativeSelectOption><NativeSelectOption value="CONVERTED">Converted</NativeSelectOption><NativeSelectOption value="REJECTED">Rejected</NativeSelectOption></NativeSelect>
            <NativeSelect aria-label="Source channel" value={channel} onChange={(event) => { setChannel(event.target.value); setPage(1); }}><NativeSelectOption value="">All sources</NativeSelectOption><NativeSelectOption value="WEBSITE">Website</NativeSelectOption>{channels.map((item) => <NativeSelectOption key={item} value={item}>{item.replaceAll("_", " ")}</NativeSelectOption>)}</NativeSelect>
            <NativeSelect aria-label="Ownership queue" value={queue} onChange={(event) => { setQueue(event.target.value); setPage(1); }}><NativeSelectOption value="team">Team queue</NativeSelectOption><NativeSelectOption value="mine">My enquiries</NativeSelectOption><NativeSelectOption value="unassigned">Unassigned</NativeSelectOption></NativeSelect>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? <ERPLoadingState rows={8} /> : query.isError ? <ERPErrorState message={query.error.message} /> : !results.length ? <ERPEmptyState title="No incoming enquiries found" description="Signed website submissions and staff-captured enquiries will appear here." /> : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <Table><TableHeader><TableRow><TableHead>Received</TableHead><TableHead>Source</TableHead><TableHead>Person / company</TableHead><TableHead>Request</TableHead><TableHead>Review</TableHead><TableHead>Owner</TableHead><TableHead><span className="sr-only">Open</span></TableHead></TableRow></TableHeader><TableBody>{results.map((item) => <TableRow key={item.id} className="cursor-pointer" onClick={() => navigate(`/app/crm/incoming-enquiries/${item.id}`)}><TableCell className="whitespace-nowrap">{formatDateTime(item.received_at)}</TableCell><TableCell><ERPStatusBadge value={item.channel} /></TableCell><TableCell><p className="font-semibold">{item.company_name || item.person_name}</p><p className="text-xs text-muted-foreground">{item.person_name} · {item.phone || item.email || "No contact supplied"}</p></TableCell><TableCell><p className="max-w-sm truncate font-medium">{item.subject}</p><p className="text-xs text-muted-foreground">{item.external_submission_id}</p></TableCell><TableCell><ERPStatusBadge value={item.review_status} /></TableCell><TableCell>{item.assigned_to_name || <span className="text-status-warning">Shared queue</span>}</TableCell><TableCell><Button aria-label={`Open ${item.subject}`} variant="ghost" size="icon"><ArrowUpRight /></Button></TableCell></TableRow>)}</TableBody></Table>
              </div>
              <div className="grid gap-3 md:hidden">{results.map((item) => <button key={item.id} type="button" onClick={() => navigate(`/app/crm/incoming-enquiries/${item.id}`)} className="rounded-lg border p-4 text-left hover:border-primary/50"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{item.company_name || item.person_name}</p><p className="text-xs text-muted-foreground">{item.channel_label || item.channel}</p></div><ERPStatusBadge value={item.review_status} /></div><p className="mt-3 text-sm">{item.subject}</p><p className="mt-3 text-xs text-muted-foreground">{item.assigned_to_name || "Shared queue"} · {formatDateTime(item.received_at)}</p></button>)}</div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCapture} onOpenChange={setShowCapture}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader><DialogTitle>Capture incoming enquiry</DialogTitle><DialogDescription>Record what actually arrived. TradeIndia, WhatsApp and other live integrations are not simulated; staff capture them here until connected.</DialogDescription></DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field><FieldLabel htmlFor="capture-channel">Source</FieldLabel><NativeSelect id="capture-channel" value={capture.channel} onChange={(event) => updateCapture("channel", event.target.value)}>{channels.map((item) => <NativeSelectOption key={item} value={item}>{item.replaceAll("_", " ")}</NativeSelectOption>)}</NativeSelect></Field>
            <Field><FieldLabel htmlFor="capture-reference">Source reference</FieldLabel><Input id="capture-reference" value={capture.source_reference} onChange={(event) => updateCapture("source_reference", event.target.value)} placeholder="TradeIndia RFQ, email subject, call note…" /></Field>
            <Field><FieldLabel htmlFor="capture-person">Contact person</FieldLabel><Input id="capture-person" value={capture.person_name} onChange={(event) => updateCapture("person_name", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="capture-company">Company</FieldLabel><Input id="capture-company" value={capture.company_name} onChange={(event) => updateCapture("company_name", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="capture-phone">Phone</FieldLabel><Input id="capture-phone" value={capture.phone} onChange={(event) => updateCapture("phone", event.target.value)} /></Field>
            <Field><FieldLabel htmlFor="capture-email">Email</FieldLabel><Input id="capture-email" type="email" value={capture.email} onChange={(event) => updateCapture("email", event.target.value)} /></Field>
            <Field className="sm:col-span-2"><FieldLabel htmlFor="capture-subject">Subject</FieldLabel><Input id="capture-subject" value={capture.subject} onChange={(event) => updateCapture("subject", event.target.value)} /></Field>
            <Field className="sm:col-span-2"><FieldLabel htmlFor="capture-message">Original message / requirement</FieldLabel><Textarea id="capture-message" rows={5} value={capture.message} onChange={(event) => updateCapture("message", event.target.value)} /><FieldDescription>Preserved in source history exactly as entered.</FieldDescription></Field>
            <Field><FieldLabel htmlFor="capture-priority">Priority</FieldLabel><NativeSelect id="capture-priority" value={capture.priority} onChange={(event) => updateCapture("priority", event.target.value)}><NativeSelectOption value="LOW">Low</NativeSelectOption><NativeSelectOption value="NORMAL">Normal</NativeSelectOption><NativeSelectOption value="HIGH">High</NativeSelectOption><NativeSelectOption value="URGENT">Urgent</NativeSelectOption></NativeSelect></Field>
            <div className="flex items-center gap-3 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground"><Users className="text-primary" />Starts in the shared queue unless assigned later.</div>
          </div>
          {create.isError ? <ERPErrorState title="Enquiry could not be captured" message={create.error.message} /> : null}
          <div className="grid grid-cols-2 gap-3 rounded-lg border p-3 text-xs text-muted-foreground"><span className="flex items-center gap-2"><Phone className="text-primary" />Manual channels supported</span><span className="flex items-center gap-2"><MessageSquareText className="text-primary" />Original wording retained</span></div>
          <DialogFooter><Button variant="outline" onClick={() => setShowCapture(false)}>Cancel</Button><Button onClick={() => create.mutate()} disabled={create.isPending || !capture.person_name.trim() || !capture.subject.trim() || !capture.message.trim()}>{create.isPending ? "Capturing…" : "Capture enquiry"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
