import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, NextActionPanel, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { Customer } from "@/production/lib/crm-types";
import type { Product } from "@/production/lib/inventory-types";
import type { Equipment, ServiceTicket } from "@/production/lib/service-types";
import type { Paginated } from "@/production/lib/types";

const blankForm = { customer_id: "", equipment_id: "", source: "MANUAL", complaint: "", priority: "NORMAL" };

function ErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "The request could not be completed.";
}

export default function ServiceTicketsPage() {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blankForm);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"assign" | "diagnose" | "job-line" | "status" | "dispatch" | null>(null);
  const [assignForm, setAssignForm] = useState({ technician_id: "", scheduled_visit_at: "" });
  const [diagnosis, setDiagnosis] = useState("");
  const [jobLineForm, setJobLineForm] = useState({ line_type: "PART", product: "", description: "", quantity: "1", unit_price: "0" });
  const [statusChoice, setStatusChoice] = useState("UNDER_REPAIR");
  const [statusNotes, setStatusNotes] = useState("");
  const [dispatchForm, setDispatchForm] = useState({ dispatch_reference: "", warranty_claim: false });

  const params = useMemo(() => {
    const next = new URLSearchParams({ page_size: "50", ordering: "-updated_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    return next;
  }, [search, status]);

  const query = useQuery({
    queryKey: ["service-tickets", params.toString()],
    queryFn: () => apiGet<Paginated<ServiceTicket>>(`/service/tickets/?${params}`),
  });
  const detail = useQuery({
    queryKey: ["service-ticket", selectedId],
    queryFn: () => apiGet<ServiceTicket>(`/service/tickets/${selectedId}/`),
    enabled: Boolean(selectedId),
  });
  const customers = useQuery({
    queryKey: ["service-ticket-customers"],
    queryFn: () => apiGet<Paginated<Customer>>("/customers/?page_size=200&ordering=legal_name"),
    enabled: open,
  });
  const equipmentList = useQuery({
    queryKey: ["service-ticket-equipment", form.customer_id],
    queryFn: () => apiGet<Paginated<Equipment>>(`/service/equipment/?customer=${form.customer_id}&page_size=200`),
    enabled: open && Boolean(form.customer_id),
  });
  const employees = useQuery({
    queryKey: ["service-ticket-employees"],
    queryFn: () => apiGet<Paginated<{ id: string; display_name: string }>>("/employees/?page_size=200"),
    enabled: dialog === "assign",
  });
  const products = useQuery({
    queryKey: ["service-ticket-products"],
    queryFn: () => apiGet<Paginated<Product>>("/inventory/products/?page_size=500&is_active=true"),
    enabled: dialog === "job-line",
  });

  const refreshDetail = async () => {
    await queryClient.invalidateQueries({ queryKey: ["service-tickets"] });
    await queryClient.invalidateQueries({ queryKey: ["service-ticket", selectedId] });
  };

  const create = useMutation({
    mutationFn: () =>
      apiPost<ServiceTicket>("/service/tickets/", {
        customer: form.customer_id,
        equipment: form.equipment_id || null,
        source: form.source,
        complaint: form.complaint,
        priority: form.priority,
      }),
    onSuccess: async (ticket) => {
      await queryClient.invalidateQueries({ queryKey: ["service-tickets"] });
      setForm(blankForm);
      setOpen(false);
      setSelectedId(ticket.id);
    },
  });

  const assign = useMutation({
    mutationFn: () =>
      apiPost(`/service/tickets/${selectedId}/assign/`, {
        technician_id: assignForm.technician_id,
        scheduled_visit_at: assignForm.scheduled_visit_at || null,
      }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setAssignForm({ technician_id: "", scheduled_visit_at: "" });
    },
  });

  const diagnose = useMutation({
    mutationFn: () => apiPost(`/service/tickets/${selectedId}/diagnose/`, { diagnosis }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setDiagnosis("");
    },
  });

  const addJobLine = useMutation({
    mutationFn: () =>
      apiPost(`/service/tickets/${selectedId}/job-lines/`, {
        line_type: jobLineForm.line_type,
        product: jobLineForm.line_type === "PART" ? jobLineForm.product || null : null,
        description: jobLineForm.description,
        quantity: jobLineForm.quantity,
        unit_price: jobLineForm.unit_price,
      }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setJobLineForm({ line_type: "PART", product: "", description: "", quantity: "1", unit_price: "0" });
    },
  });

  const changeStatus = useMutation({
    mutationFn: () =>
      apiPost(`/service/tickets/${selectedId}/change-status/`, {
        to_status: statusChoice,
        notes: statusNotes,
      }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setStatusNotes("");
    },
  });

  const dispatchTicket = useMutation({
    mutationFn: () =>
      apiPost(`/service/tickets/${selectedId}/dispatch/`, {
        dispatch_reference: dispatchForm.dispatch_reference,
        warranty_claim: dispatchForm.warranty_claim,
      }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setDispatchForm({ dispatch_reference: "", warranty_claim: false });
    },
  });

  const close = useMutation({
    mutationFn: () => apiPost(`/service/tickets/${selectedId}/close/`, {}),
    onSuccess: refreshDetail,
  });

  const results = query.data?.results ?? [];
  const ticket = detail.data;

  const nextActionFor = (item: ServiceTicket) => {
    if (item.status === "NEW") return "Assign a technician";
    if (item.status === "ASSIGNED" && !item.diagnosis.trim()) return "Record diagnosis";
    if (item.status === "ASSIGNED") return "Start repair";
    if (item.status === "UNDER_REPAIR") return "Record parts, labour and progress";
    if (item.status === "AWAITING_PARTS") return "Wait for parts, then resume repair";
    if (item.status === "AWAITING_CUSTOMER_APPROVAL") return "Waiting for customer to approve quotation";
    if (item.status === "READY_FOR_DISPATCH") return "Dispatch to customer";
    return "Review ticket";
  };

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Service · Tickets"
        title="Service & Repair"
        description="Equipment complaints from first call through diagnosis, repair, dispatch and warranty tracking."
        actions={
          hasPermission(user, "service.ticket.create") ? (
            <Button onClick={() => setOpen(true)}>
              <Plus data-icon="inline-start" />
              New Service Ticket
            </Button>
          ) : undefined
        }
      />
      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Ticket register</CardTitle>
            <CardDescription>Open a ticket to assign a technician, record diagnosis, or move it forward.</CardDescription>
          </div>
          <div className="flex w-full gap-2 lg:max-w-xl">
            <form className="flex flex-1 gap-2" onSubmit={(event) => event.preventDefault()}>
              <Input aria-label="Search Service Tickets" placeholder="Ticket number, complaint, customer…" value={search} onChange={(event) => setSearch(event.target.value)} />
              <Button type="submit" variant="outline"><Search /></Button>
            </form>
            <NativeSelect aria-label="Ticket status" value={status} onChange={(event) => setStatus(event.target.value)}>
              <NativeSelectOption value="">All statuses</NativeSelectOption>
              <NativeSelectOption value="NEW">New</NativeSelectOption>
              <NativeSelectOption value="ASSIGNED">Assigned</NativeSelectOption>
              <NativeSelectOption value="AWAITING_PARTS">Awaiting Parts</NativeSelectOption>
              <NativeSelectOption value="UNDER_REPAIR">Under Repair</NativeSelectOption>
              <NativeSelectOption value="AWAITING_CUSTOMER_APPROVAL">Awaiting Customer Approval</NativeSelectOption>
              <NativeSelectOption value="READY_FOR_DISPATCH">Ready for Dispatch</NativeSelectOption>
              <NativeSelectOption value="CLOSED">Closed</NativeSelectOption>
              <NativeSelectOption value="CANCELLED">Cancelled</NativeSelectOption>
            </NativeSelect>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {query.isPending ? (
            <div className="p-4"><ERPLoadingState rows={7} /></div>
          ) : query.isError ? (
            <div className="p-4"><ERPErrorState message={query.error.message} /></div>
          ) : !results.length ? (
            <div className="p-4"><ERPEmptyState title="No Service Tickets found" description="Create a ticket when a customer calls, emails, or walks in with a complaint." /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ticket / customer</TableHead>
                    <TableHead>Complaint</TableHead>
                    <TableHead>Technician</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => setSelectedId(item.id)}>
                      <TableCell>
                        <p className="font-semibold">{item.ticket_number}</p>
                        <p className="text-xs text-muted-foreground">{item.customer_name}</p>
                      </TableCell>
                      <TableCell className="max-w-64 truncate">{item.complaint}</TableCell>
                      <TableCell>{item.technician_name || "Unassigned"}</TableCell>
                      <TableCell><ERPStatusBadge value={item.priority} label={item.priority_label} /></TableCell>
                      <TableCell><ERPStatusBadge value={item.status} label={item.status_label} /></TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(item.updated_at)}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" aria-label={`Open ${item.ticket_number}`}><ArrowUpRight /></Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>New Service Ticket</DialogTitle>
            <DialogDescription>Record the complaint. Technician assignment and diagnosis happen next.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="svc-customer">Customer</FieldLabel>
              <NativeSelect id="svc-customer" value={form.customer_id} onChange={(event) => setForm((c) => ({ ...c, customer_id: event.target.value, equipment_id: "" }))}>
                <NativeSelectOption value="">Choose customer</NativeSelectOption>
                {customers.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.legal_name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="svc-equipment">Equipment (optional)</FieldLabel>
              <NativeSelect id="svc-equipment" value={form.equipment_id} onChange={(event) => setForm((c) => ({ ...c, equipment_id: event.target.value }))} disabled={!form.customer_id}>
                <NativeSelectOption value="">Not specified</NativeSelectOption>
                {equipmentList.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.equipment_name}{item.serial_number ? ` · ${item.serial_number}` : ""}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="svc-source">Source</FieldLabel>
              <NativeSelect id="svc-source" value={form.source} onChange={(event) => setForm((c) => ({ ...c, source: event.target.value }))}>
                <NativeSelectOption value="MANUAL">Manual</NativeSelectOption>
                <NativeSelectOption value="CALL">Call</NativeSelectOption>
                <NativeSelectOption value="EMAIL">Email</NativeSelectOption>
                <NativeSelectOption value="WHATSAPP">WhatsApp</NativeSelectOption>
                <NativeSelectOption value="WEBSITE">Website</NativeSelectOption>
                <NativeSelectOption value="INDIAMART">IndiaMART</NativeSelectOption>
                <NativeSelectOption value="TRADEINDIA">TradeIndia</NativeSelectOption>
                <NativeSelectOption value="WALK_IN">Walk-in</NativeSelectOption>
                <NativeSelectOption value="REFERRAL">Referral</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="svc-priority">Priority</FieldLabel>
              <NativeSelect id="svc-priority" value={form.priority} onChange={(event) => setForm((c) => ({ ...c, priority: event.target.value }))}>
                <NativeSelectOption value="LOW">Low</NativeSelectOption>
                <NativeSelectOption value="NORMAL">Normal</NativeSelectOption>
                <NativeSelectOption value="HIGH">High</NativeSelectOption>
                <NativeSelectOption value="URGENT">Urgent</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="svc-complaint">Complaint</FieldLabel>
              <Textarea id="svc-complaint" value={form.complaint} onChange={(event) => setForm((c) => ({ ...c, complaint: event.target.value }))} />
            </Field>
          </div>
          {create.isError ? <ERPErrorState title="Ticket could not be saved" message={ErrorMessage(create.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button disabled={!form.customer_id || !form.complaint.trim() || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? "Saving…" : "Save ticket"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(selectedId)} onOpenChange={(value) => { if (!value) { setSelectedId(null); setDialog(null); } }}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          {detail.isPending ? (
            <ERPLoadingState rows={6} />
          ) : detail.isError ? (
            <ERPErrorState message={detail.error.message} />
          ) : ticket ? (
            <>
              <DialogHeader>
                <DialogTitle>{ticket.ticket_number} · {ticket.customer_name}</DialogTitle>
                <DialogDescription>{ticket.complaint}</DialogDescription>
              </DialogHeader>
              <NextActionPanel
                status={ticket.status}
                statusText={ticket.status_label}
                title={nextActionFor(ticket)}
                description={ticket.equipment_name ? `Equipment: ${ticket.equipment_name}` : "No equipment linked to this ticket."}
                primaryAction={
                  ticket.status === "NEW" && hasPermission(user, "service.ticket.assign") ? (
                    <Button onClick={() => setDialog("assign")}>Assign technician</Button>
                  ) : ticket.status === "ASSIGNED" && !ticket.diagnosis.trim() && hasPermission(user, "service.ticket.diagnose") ? (
                    <Button onClick={() => setDialog("diagnose")}>Record diagnosis</Button>
                  ) : ticket.status === "ASSIGNED" && hasPermission(user, "service.ticket.repair") ? (
                    <Button onClick={() => { setStatusChoice("UNDER_REPAIR"); setDialog("status"); }}>Start repair</Button>
                  ) : ticket.status === "READY_FOR_DISPATCH" && hasPermission(user, "service.ticket.dispatch") ? (
                    <Button onClick={() => setDialog("dispatch")}>Dispatch</Button>
                  ) : undefined
                }
                secondaryActions={
                  !["CLOSED", "CANCELLED"].includes(ticket.status) &&
                  (hasPermission(user, "service.ticket.repair") ||
                    hasPermission(user, "service.ticket.record_parts_labour") ||
                    (ticket.status === "READY_FOR_DISPATCH" && hasPermission(user, "service.ticket.close"))) ? (
                    <>
                      {hasPermission(user, "service.ticket.repair") ? (
                        <Button variant="outline" onClick={() => setDialog("status")}>Change status</Button>
                      ) : null}
                      {hasPermission(user, "service.ticket.record_parts_labour") ? (
                        <Button variant="outline" onClick={() => setDialog("job-line")}>Add part / labour</Button>
                      ) : null}
                      {ticket.status === "READY_FOR_DISPATCH" && hasPermission(user, "service.ticket.close") ? (
                        <Button variant="outline" onClick={() => close.mutate()} disabled={close.isPending}>Close ticket</Button>
                      ) : null}
                    </>
                  ) : undefined
                }
              />
              <Tabs defaultValue="parts" className="gap-3">
                <TabsList>
                  <TabsTrigger value="parts">Parts & labour</TabsTrigger>
                  <TabsTrigger value="history">Activity timeline</TabsTrigger>
                </TabsList>
                <TabsContent value="parts">
                  {!ticket.job_lines.length ? (
                    <ERPEmptyState title="No parts or labour recorded yet" description="Add what was used to repair this equipment." />
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Type</TableHead>
                            <TableHead>Description</TableHead>
                            <TableHead className="text-right">Qty</TableHead>
                            <TableHead className="text-right">Unit price</TableHead>
                            <TableHead className="text-right">Total</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {ticket.job_lines.map((line) => (
                            <TableRow key={line.id}>
                              <TableCell>{line.line_type_label}</TableCell>
                              <TableCell>{line.description}{line.product_code ? ` · ${line.product_code}` : ""}</TableCell>
                              <TableCell className="text-right">{Number(line.quantity).toLocaleString("en-IN")}</TableCell>
                              <TableCell className="text-right">{Number(line.unit_price).toLocaleString("en-IN")}</TableCell>
                              <TableCell className="text-right">{Number(line.total_amount).toLocaleString("en-IN")}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="history">
                  {!ticket.stage_events.length ? (
                    <ERPEmptyState title="No activity yet" description="Status changes and notes appear here." />
                  ) : (
                    <div className="relative ml-2 border-l pl-6">
                      {ticket.stage_events.map((event) => (
                        <div key={event.id} className="relative pb-6 last:pb-0">
                          <span className="absolute -left-[29px] top-1 size-2 rounded-full bg-primary" />
                          <p className="font-medium">{event.from_status_label ? `${event.from_status_label} → ` : ""}{event.to_status_label}</p>
                          {event.notes ? <p className="text-sm text-muted-foreground">{event.notes}</p> : null}
                          <p className="text-xs text-muted-foreground">{event.actor_name || "System"} · {formatDateTime(event.occurred_at)}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
              <DialogFooter>
                <Button variant="outline" onClick={() => { setSelectedId(null); setDialog(null); }}>Close</Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "assign"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Assign technician</DialogTitle><DialogDescription>Optionally schedule a visit date and time.</DialogDescription></DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="assign-technician">Technician</FieldLabel>
              <NativeSelect id="assign-technician" value={assignForm.technician_id} onChange={(event) => setAssignForm((c) => ({ ...c, technician_id: event.target.value }))}>
                <NativeSelectOption value="">Choose technician</NativeSelectOption>
                {employees.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.display_name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="assign-visit">Scheduled visit (optional)</FieldLabel>
              <Input id="assign-visit" type="datetime-local" value={assignForm.scheduled_visit_at} onChange={(event) => setAssignForm((c) => ({ ...c, scheduled_visit_at: event.target.value }))} />
            </Field>
          </div>
          {assign.isError ? <ERPErrorState message={ErrorMessage(assign.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!assignForm.technician_id || assign.isPending} onClick={() => assign.mutate()}>{assign.isPending ? "Assigning…" : "Assign"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "diagnose"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Record diagnosis</DialogTitle><DialogDescription>What the technician found.</DialogDescription></DialogHeader>
          <Field><FieldLabel htmlFor="diagnosis-text">Diagnosis</FieldLabel><Textarea id="diagnosis-text" value={diagnosis} onChange={(event) => setDiagnosis(event.target.value)} /></Field>
          {diagnose.isError ? <ERPErrorState message={ErrorMessage(diagnose.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!diagnosis.trim() || diagnose.isPending} onClick={() => diagnose.mutate()}>{diagnose.isPending ? "Saving…" : "Save diagnosis"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "job-line"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add part or labour</DialogTitle><DialogDescription>Record what was used or billed for this repair.</DialogDescription></DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="jobline-type">Type</FieldLabel>
              <NativeSelect id="jobline-type" value={jobLineForm.line_type} onChange={(event) => setJobLineForm((c) => ({ ...c, line_type: event.target.value }))}>
                <NativeSelectOption value="PART">Part</NativeSelectOption>
                <NativeSelectOption value="LABOUR">Labour</NativeSelectOption>
              </NativeSelect>
            </Field>
            {jobLineForm.line_type === "PART" ? (
              <Field>
                <FieldLabel htmlFor="jobline-product">Product</FieldLabel>
                <NativeSelect id="jobline-product" value={jobLineForm.product} onChange={(event) => setJobLineForm((c) => ({ ...c, product: event.target.value }))}>
                  <NativeSelectOption value="">Choose product</NativeSelectOption>
                  {products.data?.results.map((product) => (
                    <NativeSelectOption key={product.id} value={product.id}>{product.internal_code} · {product.description}</NativeSelectOption>
                  ))}
                </NativeSelect>
              </Field>
            ) : null}
            <Field><FieldLabel htmlFor="jobline-description">Description</FieldLabel><Input id="jobline-description" value={jobLineForm.description} onChange={(event) => setJobLineForm((c) => ({ ...c, description: event.target.value }))} /></Field>
            <Field><FieldLabel htmlFor="jobline-qty">Quantity</FieldLabel><Input id="jobline-qty" type="number" min="0.0001" step="0.0001" value={jobLineForm.quantity} onChange={(event) => setJobLineForm((c) => ({ ...c, quantity: event.target.value }))} /></Field>
            <Field><FieldLabel htmlFor="jobline-price">Unit price</FieldLabel><Input id="jobline-price" type="number" min="0" step="0.01" value={jobLineForm.unit_price} onChange={(event) => setJobLineForm((c) => ({ ...c, unit_price: event.target.value }))} /></Field>
          </div>
          {addJobLine.isError ? <ERPErrorState message={ErrorMessage(addJobLine.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!jobLineForm.description.trim() || addJobLine.isPending} onClick={() => addJobLine.mutate()}>{addJobLine.isPending ? "Adding…" : "Add"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "status"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Change status</DialogTitle><DialogDescription>Move the ticket to its next practical state.</DialogDescription></DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="status-choice">New status</FieldLabel>
              <NativeSelect id="status-choice" value={statusChoice} onChange={(event) => setStatusChoice(event.target.value)}>
                <NativeSelectOption value="AWAITING_PARTS">Awaiting Parts</NativeSelectOption>
                <NativeSelectOption value="UNDER_REPAIR">Under Repair</NativeSelectOption>
                <NativeSelectOption value="READY_FOR_DISPATCH">Ready for Dispatch</NativeSelectOption>
                <NativeSelectOption value="CANCELLED">Cancelled</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field><FieldLabel htmlFor="status-notes">Notes (optional)</FieldLabel><Textarea id="status-notes" value={statusNotes} onChange={(event) => setStatusNotes(event.target.value)} /></Field>
          </div>
          {changeStatus.isError ? <ERPErrorState message={ErrorMessage(changeStatus.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={changeStatus.isPending} onClick={() => changeStatus.mutate()}>{changeStatus.isPending ? "Working…" : "Confirm"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "dispatch"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Dispatch to customer</DialogTitle><DialogDescription>Record the courier/dispatch reference and warranty status.</DialogDescription></DialogHeader>
          <div className="grid gap-3">
            <Field><FieldLabel htmlFor="dispatch-ref">Dispatch reference</FieldLabel><Input id="dispatch-ref" value={dispatchForm.dispatch_reference} onChange={(event) => setDispatchForm((c) => ({ ...c, dispatch_reference: event.target.value }))} /></Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={dispatchForm.warranty_claim} onChange={(event) => setDispatchForm((c) => ({ ...c, warranty_claim: event.target.checked }))} />
              This repair was under warranty
            </label>
          </div>
          {dispatchTicket.isError ? <ERPErrorState message={ErrorMessage(dispatchTicket.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!dispatchForm.dispatch_reference.trim() || dispatchTicket.isPending} onClick={() => dispatchTicket.mutate()}>{dispatchTicket.isPending ? "Dispatching…" : "Confirm dispatch"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
