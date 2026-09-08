import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Plus, Search, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { Product, Supplier } from "@/production/lib/inventory-types";
import type { PurchaseRequisition } from "@/production/lib/purchasing-types";
import type { Paginated } from "@/production/lib/types";

type DraftLine = { product: string; quantity: string; notes: string };
const emptyLine: DraftLine = { product: "", quantity: "1", notes: "" };
const blankForm = {
  warehouse_id: "",
  requested_by_id: "",
  preferred_supplier_id: "",
  justification: "",
  required_by_date: "",
};

export default function PurchaseRequisitionsPage() {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blankForm);
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);
  const [selected, setSelected] = useState<PurchaseRequisition | null>(null);

  const params = useMemo(() => {
    const next = new URLSearchParams({ page_size: "50", ordering: "-updated_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    return next;
  }, [search, status]);

  const query = useQuery({
    queryKey: ["purchase-requisitions", params.toString()],
    queryFn: () => apiGet<Paginated<PurchaseRequisition>>(`/purchasing/requisitions/?${params}`),
  });
  const warehouses = useQuery({
    queryKey: ["pr-warehouses"],
    queryFn: () => apiGet<Paginated<{ id: string; name: string }>>("/warehouses/?page_size=100"),
    enabled: open,
  });
  const employees = useQuery({
    queryKey: ["pr-employees"],
    queryFn: () => apiGet<Paginated<{ id: string; display_name: string }>>("/employees/?page_size=200"),
    enabled: open,
  });
  const suppliers = useQuery({
    queryKey: ["pr-suppliers"],
    queryFn: () => apiGet<Paginated<Supplier>>("/inventory/suppliers/?page_size=200&is_active=true"),
    enabled: open,
  });
  const products = useQuery({
    queryKey: ["pr-products"],
    queryFn: () => apiGet<Paginated<Product>>("/inventory/products/?page_size=500&is_active=true"),
    enabled: open,
  });

  const create = useMutation({
    mutationFn: () =>
      apiPost<PurchaseRequisition>("/purchasing/requisitions/", {
        warehouse: form.warehouse_id,
        requested_by: form.requested_by_id,
        preferred_supplier: form.preferred_supplier_id || null,
        justification: form.justification,
        required_by_date: form.required_by_date || null,
        lines: lines
          .filter((line) => line.product && Number(line.quantity) > 0)
          .map((line) => ({ product: line.product, quantity: line.quantity, notes: line.notes })),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["purchase-requisitions"] });
      setForm(blankForm);
      setLines([{ ...emptyLine }]);
      setOpen(false);
    },
  });

  const submit = useMutation({
    mutationFn: (id: string) => apiPost(`/purchasing/requisitions/${id}/submit/`, {}),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["purchase-requisitions"] });
      setSelected(null);
    },
  });

  const results = query.data?.results ?? [];
  const updateLine = (index: number, field: keyof DraftLine, value: string) =>
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, [field]: value } : line)));

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Inventory & Purchase · Requisitions"
        title="Purchase Requisitions"
        description="What stores or workshop need to buy, before it becomes a formal Purchase Order."
        actions={
          hasPermission(user, "purchasing.requisition.create") ? (
            <Button onClick={() => setOpen(true)}>
              <Plus data-icon="inline-start" />
              New requisition
            </Button>
          ) : undefined
        }
      />
      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Requisition register</CardTitle>
            <CardDescription>Open a requisition to submit it for approval or track its status.</CardDescription>
          </div>
          <div className="flex w-full gap-2 lg:max-w-xl">
            <form
              className="flex flex-1 gap-2"
              onSubmit={(event) => {
                event.preventDefault();
              }}
            >
              <Input
                aria-label="Search requisitions"
                placeholder="Requisition number…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <Button type="submit" variant="outline">
                <Search />
              </Button>
            </form>
            <NativeSelect aria-label="Requisition status" value={status} onChange={(event) => setStatus(event.target.value)}>
              <NativeSelectOption value="">All statuses</NativeSelectOption>
              <NativeSelectOption value="DRAFT">Draft</NativeSelectOption>
              <NativeSelectOption value="PENDING_APPROVAL">Awaiting Approval</NativeSelectOption>
              <NativeSelectOption value="APPROVED">Approved</NativeSelectOption>
              <NativeSelectOption value="CONVERTED">Converted to PO</NativeSelectOption>
              <NativeSelectOption value="REJECTED">Rejected</NativeSelectOption>
            </NativeSelect>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {query.isPending ? (
            <div className="p-4"><ERPLoadingState rows={6} /></div>
          ) : query.isError ? (
            <div className="p-4"><ERPErrorState message={query.error.message} /></div>
          ) : !results.length ? (
            <div className="p-4"><ERPEmptyState title="No requisitions found" description="Create a requisition when stores or workshop need to buy something." /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Requisition</TableHead>
                    <TableHead>Warehouse</TableHead>
                    <TableHead>Requested by</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => setSelected(item)}>
                      <TableCell className="font-medium">{item.requisition_number}</TableCell>
                      <TableCell>{item.warehouse_name}</TableCell>
                      <TableCell>{item.requested_by_name}</TableCell>
                      <TableCell><ERPStatusBadge value={item.status} label={item.status_label} /></TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(item.updated_at)}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" aria-label={`Open ${item.requisition_number}`}>
                          <ArrowUpRight />
                        </Button>
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
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>New Purchase Requisition</DialogTitle>
            <DialogDescription>Record what needs to be bought. It can be reviewed and approved before ordering.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="pr-warehouse">Warehouse</FieldLabel>
              <NativeSelect id="pr-warehouse" value={form.warehouse_id} onChange={(event) => setForm((c) => ({ ...c, warehouse_id: event.target.value }))}>
                <NativeSelectOption value="">Choose warehouse</NativeSelectOption>
                {warehouses.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="pr-requested-by">Requested by</FieldLabel>
              <NativeSelect id="pr-requested-by" value={form.requested_by_id} onChange={(event) => setForm((c) => ({ ...c, requested_by_id: event.target.value }))}>
                <NativeSelectOption value="">Choose employee</NativeSelectOption>
                {employees.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.display_name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="pr-supplier">Preferred supplier (optional)</FieldLabel>
              <NativeSelect id="pr-supplier" value={form.preferred_supplier_id} onChange={(event) => setForm((c) => ({ ...c, preferred_supplier_id: event.target.value }))}>
                <NativeSelectOption value="">No preference</NativeSelectOption>
                {suppliers.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="pr-required-by">Required by</FieldLabel>
              <Input id="pr-required-by" type="date" value={form.required_by_date} onChange={(event) => setForm((c) => ({ ...c, required_by_date: event.target.value }))} />
            </Field>
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="pr-justification">Justification</FieldLabel>
              <Textarea id="pr-justification" value={form.justification} onChange={(event) => setForm((c) => ({ ...c, justification: event.target.value }))} />
            </Field>
          </div>
          <div className="mt-2">
            <p className="mb-2 text-sm font-medium">Requested items</p>
            <div className="grid gap-2">
              {lines.map((line, index) => (
                <div key={index} className="grid grid-cols-[1fr_100px_1fr_auto] items-end gap-2">
                  <Field>
                    <FieldLabel htmlFor={`pr-line-product-${index}`}>Product</FieldLabel>
                    <NativeSelect id={`pr-line-product-${index}`} value={line.product} onChange={(event) => updateLine(index, "product", event.target.value)}>
                      <NativeSelectOption value="">Choose product</NativeSelectOption>
                      {products.data?.results.map((product) => (
                        <NativeSelectOption key={product.id} value={product.id}>{product.internal_code} · {product.description}</NativeSelectOption>
                      ))}
                    </NativeSelect>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`pr-line-qty-${index}`}>Qty</FieldLabel>
                    <Input id={`pr-line-qty-${index}`} type="number" min="0.0001" step="0.0001" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`pr-line-notes-${index}`}>Notes</FieldLabel>
                    <Input id={`pr-line-notes-${index}`} value={line.notes} onChange={(event) => updateLine(index, "notes", event.target.value)} />
                  </Field>
                  <Button variant="ghost" size="icon" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, i) => i !== index))}>
                    <Trash2 />
                  </Button>
                </div>
              ))}
            </div>
            <Button variant="outline" className="mt-2" onClick={() => setLines((current) => [...current, { ...emptyLine }])}>
              <Plus data-icon="inline-start" />
              Add item
            </Button>
          </div>
          {create.isError ? (
            <ERPErrorState title="Requisition could not be saved" message={create.error instanceof ApiError ? create.error.message : "The request could not be completed."} />
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={create.isPending || !form.warehouse_id || !form.requested_by_id || !lines.some((line) => line.product)}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Saving…" : "Save requisition"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(selected)} onOpenChange={(value) => !value && setSelected(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle>{selected.requisition_number}</DialogTitle>
                <DialogDescription>{selected.warehouse_name} · Requested by {selected.requested_by_name}</DialogDescription>
              </DialogHeader>
              <div className="flex items-center gap-2">
                <ERPStatusBadge value={selected.status} label={selected.status_label} />
              </div>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Product</TableHead>
                      <TableHead className="text-right">Quantity</TableHead>
                      <TableHead>Notes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selected.lines.map((line) => (
                      <TableRow key={line.id}>
                        <TableCell>
                          <p className="font-medium">{line.product_code}</p>
                          <p className="text-xs text-muted-foreground">{line.product_description}</p>
                        </TableCell>
                        <TableCell className="text-right">{Number(line.quantity).toLocaleString("en-IN")}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{line.notes}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {submit.isError ? (
                <ERPErrorState title="Could not submit" message={submit.error instanceof ApiError ? submit.error.message : "The request could not be completed."} />
              ) : null}
              <DialogFooter>
                <Button variant="outline" onClick={() => setSelected(null)}>Close</Button>
                {selected.status === "DRAFT" && hasPermission(user, "purchasing.requisition.submit") ? (
                  <Button onClick={() => submit.mutate(selected.id)} disabled={submit.isPending}>
                    {submit.isPending ? "Submitting…" : "Submit for approval"}
                  </Button>
                ) : null}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
