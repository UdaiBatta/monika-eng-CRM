import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, PackageCheck, PauseCircle, PlayCircle, Plus, XCircle } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

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
import type { Product } from "@/production/lib/inventory-types";
import type { Paginated } from "@/production/lib/types";
import type { PanelJob } from "@/production/lib/workshop-types";

const ADVANCE_LABEL: Record<string, string> = {
  READY_FOR_ASSEMBLY: "Start Assembly",
  ASSEMBLY: "Move to Wiring",
  WIRING: "Move to Testing",
  TESTING: "Move to Quality Check",
  FITTING_INSTALLATION: "Move to Handover",
};

function ErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "The request could not be completed.";
}

export default function PanelJobPage() {
  const { panelJobId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [dialog, setDialog] = useState<"add-material" | "reserve" | "movement" | "quality" | "handover" | "hold" | "cancel" | null>(null);
  const [materialForm, setMaterialForm] = useState({ product: "", required_quantity: "1", notes: "" });
  const [reserveLocation, setReserveLocation] = useState("");
  const [movementForm, setMovementForm] = useState({ material_line: "", movement_type: "ISSUE", quantity: "1", location: "" });
  const [qualityForm, setQualityForm] = useState({ passed: true, notes: "" });
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState("");

  const query = useQuery({
    queryKey: ["panel-job", panelJobId],
    queryFn: () => apiGet<PanelJob>(`/workshop/panel-jobs/${panelJobId}/`),
    enabled: Boolean(panelJobId),
  });
  const products = useQuery({
    queryKey: ["panel-job-products"],
    queryFn: () => apiGet<Paginated<Product>>("/inventory/products/?page_size=500&is_active=true"),
    enabled: dialog === "add-material",
  });
  const locations = useQuery({
    queryKey: ["panel-job-locations"],
    queryFn: () => apiGet<Paginated<{ id: string; warehouse_name: string; bin_code: string }>>("/inventory/stock-locations/?page_size=500"),
    enabled: dialog === "reserve" || dialog === "movement",
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["panel-job", panelJobId] });
    await queryClient.invalidateQueries({ queryKey: ["stock-items"] });
  };

  const action = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => apiPost(path, body),
    onSuccess: async () => {
      await refresh();
      setDialog(null);
      setNotes("");
      setReason("");
    },
  });

  const addMaterial = useMutation({
    mutationFn: () =>
      apiPost(`/workshop/panel-jobs/${panelJobId}/material-lines/`, {
        product: materialForm.product,
        required_quantity: materialForm.required_quantity,
        notes: materialForm.notes,
      }),
    onSuccess: async () => {
      await refresh();
      setMaterialForm({ product: "", required_quantity: "1", notes: "" });
      setDialog(null);
    },
  });

  const reserve = useMutation({
    mutationFn: () => apiPost(`/workshop/panel-jobs/${panelJobId}/reserve-materials/`, { location: reserveLocation }),
    onSuccess: async () => {
      await refresh();
      setReserveLocation("");
      setDialog(null);
    },
  });

  const recordMovement = useMutation({
    mutationFn: () =>
      apiPost(`/workshop/panel-jobs/${panelJobId}/material-movements/`, {
        material_line: movementForm.material_line,
        movement_type: movementForm.movement_type,
        quantity: movementForm.quantity,
        location: movementForm.location,
      }),
    onSuccess: async () => {
      await refresh();
      setMovementForm({ material_line: "", movement_type: "ISSUE", quantity: "1", location: "" });
      setDialog(null);
    },
  });

  const qualityCheck = useMutation({
    mutationFn: () =>
      apiPost(`/workshop/panel-jobs/${panelJobId}/quality-check/`, {
        passed: qualityForm.passed,
        notes: qualityForm.notes,
      }),
    onSuccess: async () => {
      await refresh();
      setQualityForm({ passed: true, notes: "" });
      setDialog(null);
    },
  });

  const panelJob = query.data;
  if (query.isPending || !panelJob) return <ERPLoadingState rows={9} />;
  if (query.isError) return <ERPErrorState message={query.error.message} />;

  const run = (path: string, body?: unknown) => action.mutate({ path, body });
  const canAdvance = Boolean(ADVANCE_LABEL[panelJob.status]) && hasPermission(user, "workshop.panel_job.advance");
  const inMaterialStage = ["REQUIREMENT_REVIEW", "MATERIAL_PLANNING", "MATERIAL_SHORTAGE"].includes(panelJob.status);
  const canReserve = ["MATERIAL_PLANNING", "MATERIAL_SHORTAGE"].includes(panelJob.status) && hasPermission(user, "workshop.panel_job.reserve_stock");
  const canRecordMaterial = !inMaterialStage && !["HANDOVER", "CLOSED", "CANCELLED", "ON_HOLD"].includes(panelJob.status) && hasPermission(user, "workshop.panel_job.record_material");
  const canQualityCheck = panelJob.status === "QUALITY_CHECK" && hasPermission(user, "workshop.panel_job.quality_check");
  const canHandover = panelJob.status === "HANDOVER" && hasPermission(user, "workshop.panel_job.handover");
  const canHold = !["CLOSED", "CANCELLED", "ON_HOLD"].includes(panelJob.status) && hasPermission(user, "workshop.panel_job.hold");
  const canResume = panelJob.status === "ON_HOLD" && hasPermission(user, "workshop.panel_job.hold");
  const canCancel = !["CLOSED", "CANCELLED"].includes(panelJob.status) && hasPermission(user, "workshop.panel_job.cancel");

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Workshop · Panel Job"
        title={panelJob.panel_job_number}
        description={`${panelJob.panel_name} · ${panelJob.project_number} · ${panelJob.warehouse_name}`}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate(`/app/projects/${panelJob.project}`)}>
              <ArrowLeft data-icon="inline-start" />
              Back to Project
            </Button>
            <ERPStatusBadge value={panelJob.status} label={panelJob.status_label} />
          </>
        }
      />
      {action.isError ? <ERPErrorState title="Action could not be completed" message={ErrorMessage(action.error)} /> : null}

      <NextActionPanel
        status={panelJob.status}
        statusText={panelJob.status_label}
        title={
          panelJob.status === "REQUIREMENT_REVIEW"
            ? "Add material requirements"
            : panelJob.status === "MATERIAL_PLANNING"
              ? "Reserve stock for this Panel Job"
              : panelJob.status === "MATERIAL_SHORTAGE"
                ? "Some material is short — reserve what's available or wait for purchase"
                : canAdvance
                  ? ADVANCE_LABEL[panelJob.status]
                  : panelJob.status === "QUALITY_CHECK"
                    ? "Record the Quality Check result"
                    : panelJob.status === "HANDOVER"
                      ? "Hand over the completed panel"
                      : "Review the current Panel Job state"
        }
        description={
          panelJob.status === "MATERIAL_SHORTAGE"
            ? "Reserving again will pick up any material received since the last attempt."
            : "Guided next step for this Panel Job's current stage."
        }
        primaryAction={
          inMaterialStage ? (
            <Button onClick={() => setDialog("add-material")}>
              <Plus data-icon="inline-start" />
              Add material
            </Button>
          ) : canAdvance ? (
            <Button onClick={() => run(`/workshop/panel-jobs/${panelJobId}/advance/`, {})} disabled={action.isPending}>
              <CheckCircle2 data-icon="inline-start" />
              {ADVANCE_LABEL[panelJob.status]}
            </Button>
          ) : canQualityCheck ? (
            <Button onClick={() => setDialog("quality")}>
              <CheckCircle2 data-icon="inline-start" />
              Record Quality Check
            </Button>
          ) : canHandover ? (
            <Button onClick={() => setDialog("handover")}>
              <PackageCheck data-icon="inline-start" />
              Handover
            </Button>
          ) : undefined
        }
        secondaryActions={
          canReserve || canRecordMaterial || canHold || canResume || canCancel ? (
            <>
              {canReserve ? <Button variant="outline" onClick={() => setDialog("reserve")}>Reserve stock</Button> : null}
              {canRecordMaterial ? <Button variant="outline" onClick={() => setDialog("movement")}>Issue / Consume / Return</Button> : null}
              {canHold ? <Button variant="outline" onClick={() => setDialog("hold")}><PauseCircle data-icon="inline-start" />Put on hold</Button> : null}
              {canResume ? <Button variant="outline" onClick={() => run(`/workshop/panel-jobs/${panelJobId}/resume/`, {})}><PlayCircle data-icon="inline-start" />Resume</Button> : null}
              {canCancel ? <Button variant="destructive" onClick={() => setDialog("cancel")}><XCircle data-icon="inline-start" />Cancel</Button> : null}
            </>
          ) : undefined
        }
      />

      <Tabs defaultValue="material" className="gap-3">
        <TabsList>
          <TabsTrigger value="material">Material</TabsTrigger>
          <TabsTrigger value="stages">Stage history</TabsTrigger>
        </TabsList>
        <TabsContent value="material">
          <Card>
            <CardHeader>
              <CardTitle>Material lines</CardTitle>
              <CardDescription>Required, reserved, issued, consumed and returned quantities.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {!panelJob.material_lines.length ? (
                <div className="p-4"><ERPEmptyState title="No material lines yet" description="Add what this panel needs to start material planning." /></div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead className="text-right">Required</TableHead>
                        <TableHead className="text-right">Reserved</TableHead>
                        <TableHead className="text-right">Issued</TableHead>
                        <TableHead className="text-right">Consumed</TableHead>
                        <TableHead className="text-right">Returned</TableHead>
                        <TableHead className="text-right">Shortage</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {panelJob.material_lines.map((line) => (
                        <TableRow key={line.id}>
                          <TableCell>
                            <p className="font-medium">{line.product_code}</p>
                            <p className="text-xs text-muted-foreground">{line.product_description}</p>
                          </TableCell>
                          <TableCell className="text-right">{Number(line.required_quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell className="text-right">{Number(line.reserved_quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell className="text-right">{Number(line.issued_quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell className="text-right">{Number(line.consumed_quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell className="text-right">{Number(line.returned_quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell className="text-right">
                            {Number(line.shortage_quantity) > 0 ? (
                              <span className="font-semibold text-status-warning">{Number(line.shortage_quantity).toLocaleString("en-IN")}</span>
                            ) : (
                              "—"
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="stages">
          <Card>
            <CardHeader>
              <CardTitle>Stage history</CardTitle>
              <CardDescription>Every stage change for this Panel Job, permanently recorded.</CardDescription>
            </CardHeader>
            <CardContent>
              {!panelJob.stage_events.length ? (
                <ERPEmptyState title="No stage history yet" description="Stage changes appear here as the Panel Job progresses." />
              ) : (
                <div className="relative ml-2 border-l pl-6">
                  {panelJob.stage_events.map((event) => (
                    <div key={event.id} className="relative pb-6 last:pb-0">
                      <span className="absolute -left-[29px] top-1 size-2 rounded-full bg-primary" />
                      <p className="font-medium">
                        {event.from_status_label ? `${event.from_status_label} → ` : ""}
                        {event.to_status_label}
                      </p>
                      {event.notes ? <p className="text-sm text-muted-foreground">{event.notes}</p> : null}
                      <p className="text-xs text-muted-foreground">{event.actor_name || "System"} · {formatDateTime(event.occurred_at)}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={dialog === "add-material"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add material</DialogTitle>
            <DialogDescription>Record what this panel needs from stock.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="material-product">Product</FieldLabel>
              <NativeSelect id="material-product" value={materialForm.product} onChange={(event) => setMaterialForm((c) => ({ ...c, product: event.target.value }))}>
                <NativeSelectOption value="">Choose product</NativeSelectOption>
                {products.data?.results.map((product) => (
                  <NativeSelectOption key={product.id} value={product.id}>{product.internal_code} · {product.description}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="material-qty">Required quantity</FieldLabel>
              <Input id="material-qty" type="number" min="0.0001" step="0.0001" value={materialForm.required_quantity} onChange={(event) => setMaterialForm((c) => ({ ...c, required_quantity: event.target.value }))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="material-notes">Notes (optional)</FieldLabel>
              <Input id="material-notes" value={materialForm.notes} onChange={(event) => setMaterialForm((c) => ({ ...c, notes: event.target.value }))} />
            </Field>
          </div>
          {addMaterial.isError ? <ERPErrorState message={ErrorMessage(addMaterial.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!materialForm.product || addMaterial.isPending} onClick={() => addMaterial.mutate()}>
              {addMaterial.isPending ? "Adding…" : "Add material"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "reserve"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reserve stock</DialogTitle>
            <DialogDescription>Reserves what's available at this location for every material line.</DialogDescription>
          </DialogHeader>
          <Field>
            <FieldLabel htmlFor="reserve-location">Location</FieldLabel>
            <NativeSelect id="reserve-location" value={reserveLocation} onChange={(event) => setReserveLocation(event.target.value)}>
              <NativeSelectOption value="">Choose location</NativeSelectOption>
              {locations.data?.results.map((location) => (
                <NativeSelectOption key={location.id} value={location.id}>{location.warehouse_name}{location.bin_code ? ` · ${location.bin_code}` : ""}</NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
          {reserve.isError ? <ERPErrorState message={ErrorMessage(reserve.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!reserveLocation || reserve.isPending} onClick={() => reserve.mutate()}>
              {reserve.isPending ? "Reserving…" : "Reserve stock"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "movement"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Issue, consume or return material</DialogTitle>
            <DialogDescription>Issue moves reserved stock out; consume records usage; return brings unused material back.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="movement-line">Material line</FieldLabel>
              <NativeSelect id="movement-line" value={movementForm.material_line} onChange={(event) => setMovementForm((c) => ({ ...c, material_line: event.target.value }))}>
                <NativeSelectOption value="">Choose material line</NativeSelectOption>
                {panelJob.material_lines.map((line) => (
                  <NativeSelectOption key={line.id} value={line.id}>{line.product_code} · {line.product_description}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="movement-type">Movement</FieldLabel>
              <NativeSelect id="movement-type" value={movementForm.movement_type} onChange={(event) => setMovementForm((c) => ({ ...c, movement_type: event.target.value }))}>
                <NativeSelectOption value="ISSUE">Issue to workshop floor</NativeSelectOption>
                <NativeSelectOption value="CONSUME">Consume (used in panel)</NativeSelectOption>
                <NativeSelectOption value="RETURN">Return unused material</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="movement-qty">Quantity</FieldLabel>
              <Input id="movement-qty" type="number" min="0.0001" step="0.0001" value={movementForm.quantity} onChange={(event) => setMovementForm((c) => ({ ...c, quantity: event.target.value }))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="movement-location">Location</FieldLabel>
              <NativeSelect id="movement-location" value={movementForm.location} onChange={(event) => setMovementForm((c) => ({ ...c, location: event.target.value }))}>
                <NativeSelectOption value="">Choose location</NativeSelectOption>
                {locations.data?.results.map((location) => (
                  <NativeSelectOption key={location.id} value={location.id}>{location.warehouse_name}{location.bin_code ? ` · ${location.bin_code}` : ""}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
          </div>
          {recordMovement.isError ? <ERPErrorState message={ErrorMessage(recordMovement.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={!movementForm.material_line || !movementForm.location || recordMovement.isPending} onClick={() => recordMovement.mutate()}>
              {recordMovement.isPending ? "Recording…" : "Record"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "quality"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Quality Check</DialogTitle>
            <DialogDescription>A failed check sends the panel back to Testing.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="quality-result">Result</FieldLabel>
              <NativeSelect id="quality-result" value={qualityForm.passed ? "PASS" : "FAIL"} onChange={(event) => setQualityForm((c) => ({ ...c, passed: event.target.value === "PASS" }))}>
                <NativeSelectOption value="PASS">Passed</NativeSelectOption>
                <NativeSelectOption value="FAIL">Failed</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="quality-notes">Notes</FieldLabel>
              <Textarea id="quality-notes" value={qualityForm.notes} onChange={(event) => setQualityForm((c) => ({ ...c, notes: event.target.value }))} />
            </Field>
          </div>
          {qualityCheck.isError ? <ERPErrorState message={ErrorMessage(qualityCheck.error)} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={qualityCheck.isPending} onClick={() => qualityCheck.mutate()}>
              {qualityCheck.isPending ? "Recording…" : "Record result"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "handover"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Hand over Panel Job</DialogTitle>
            <DialogDescription>Closes this Panel Job as complete.</DialogDescription>
          </DialogHeader>
          <Field><FieldLabel htmlFor="handover-notes">Handover notes</FieldLabel><Textarea id="handover-notes" value={notes} onChange={(event) => setNotes(event.target.value)} /></Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
            <Button disabled={action.isPending} onClick={() => run(`/workshop/panel-jobs/${panelJobId}/handover/`, { notes })}>
              {action.isPending ? "Working…" : "Confirm handover"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "hold" || dialog === "cancel"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialog === "hold" ? "Put Panel Job on hold" : "Cancel Panel Job"}</DialogTitle>
            <DialogDescription>Give a clear business reason so colleagues understand the change.</DialogDescription>
          </DialogHeader>
          <Field><FieldLabel htmlFor="panel-job-reason">Reason</FieldLabel><Textarea id="panel-job-reason" value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Back</Button>
            <Button
              variant={dialog === "cancel" ? "destructive" : "default"}
              disabled={!reason.trim() || action.isPending}
              onClick={() => run(`/workshop/panel-jobs/${panelJobId}/${dialog}/`, { reason })}
            >
              {action.isPending ? "Working…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
