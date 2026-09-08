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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, ERPStatusBadge, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { Product, Supplier } from "@/production/lib/inventory-types";
import type { GoodsReceipt, PurchaseOrder } from "@/production/lib/purchasing-types";
import type { Paginated } from "@/production/lib/types";

type DraftLine = { product: string; quantity: string; unit_price: string; tax_percent: string };
const emptyLine: DraftLine = { product: "", quantity: "1", unit_price: "0", tax_percent: "0" };
const blankForm = {
  supplier_id: "",
  warehouse_id: "",
  responsible_employee_id: "",
  currency_id: "",
  expected_delivery_date: "",
  payment_terms: "",
  delivery_terms: "",
  notes: "",
};

function money(value: string, currency = "INR") {
  return `${currency} ${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export default function PurchaseOrdersPage() {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blankForm);
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"cancel" | "payment" | "grn" | null>(null);
  const [reason, setReason] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("PART_PAID");
  const [grnReceivedBy, setGrnReceivedBy] = useState("");
  const [grnQuantities, setGrnQuantities] = useState<Record<string, string>>({});

  const params = useMemo(() => {
    const next = new URLSearchParams({ page_size: "50", ordering: "-updated_at" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    return next;
  }, [search, status]);

  const query = useQuery({
    queryKey: ["purchase-orders", params.toString()],
    queryFn: () => apiGet<Paginated<PurchaseOrder>>(`/purchasing/orders/?${params}`),
  });
  const detail = useQuery({
    queryKey: ["purchase-order", selectedId],
    queryFn: () => apiGet<PurchaseOrder>(`/purchasing/orders/${selectedId}/`),
    enabled: Boolean(selectedId),
  });
  const receipts = useQuery({
    queryKey: ["purchase-order-receipts", selectedId],
    queryFn: () => apiGet<Paginated<GoodsReceipt>>(`/purchasing/goods-receipts/?purchase_order=${selectedId}`),
    enabled: Boolean(selectedId),
  });

  const suppliers = useQuery({
    queryKey: ["po-suppliers"],
    queryFn: () => apiGet<Paginated<Supplier>>("/inventory/suppliers/?page_size=200&is_active=true"),
    enabled: open,
  });
  const warehouses = useQuery({
    queryKey: ["po-warehouses"],
    queryFn: () => apiGet<Paginated<{ id: string; name: string }>>("/warehouses/?page_size=100"),
    enabled: open,
  });
  const employees = useQuery({
    queryKey: ["po-employees"],
    queryFn: () => apiGet<Paginated<{ id: string; display_name: string }>>("/employees/?page_size=200"),
    enabled: open || dialog === "grn",
  });
  const currencies = useQuery({
    queryKey: ["po-currencies"],
    queryFn: () => apiGet<Paginated<{ id: string; code: string; name: string }>>("/currencies/?is_active=true&page_size=100"),
    enabled: open,
  });
  const products = useQuery({
    queryKey: ["po-products"],
    queryFn: () => apiGet<Paginated<Product>>("/inventory/products/?page_size=500&is_active=true"),
    enabled: open,
  });

  const refreshDetail = async () => {
    await queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    await queryClient.invalidateQueries({ queryKey: ["purchase-order", selectedId] });
    await queryClient.invalidateQueries({ queryKey: ["purchase-order-receipts", selectedId] });
    await queryClient.invalidateQueries({ queryKey: ["stock-items"] });
  };

  const create = useMutation({
    mutationFn: () =>
      apiPost<PurchaseOrder>("/purchasing/orders/", {
        supplier: form.supplier_id,
        warehouse: form.warehouse_id,
        responsible_employee: form.responsible_employee_id,
        currency: form.currency_id,
        expected_delivery_date: form.expected_delivery_date || null,
        payment_terms: form.payment_terms,
        delivery_terms: form.delivery_terms,
        notes: form.notes,
        lines: lines
          .filter((line) => line.product && Number(line.quantity) > 0)
          .map((line) => ({
            product: line.product,
            quantity: line.quantity,
            unit_price: line.unit_price,
            tax_percent: line.tax_percent,
          })),
      }),
    onSuccess: async (order) => {
      await queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      setForm(blankForm);
      setLines([{ ...emptyLine }]);
      setOpen(false);
      setSelectedId(order.id);
    },
  });

  const submit = useMutation({
    mutationFn: (id: string) => apiPost(`/purchasing/orders/${id}/submit/`, {}),
    onSuccess: refreshDetail,
  });
  const cancel = useMutation({
    mutationFn: (id: string) => apiPost(`/purchasing/orders/${id}/cancel/`, { reason }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setReason("");
    },
  });
  const recordPayment = useMutation({
    mutationFn: (id: string) =>
      apiPost(`/purchasing/orders/${id}/record-payment/`, {
        amount: paymentAmount,
        payment_status: paymentStatus,
      }),
    onSuccess: async () => {
      await refreshDetail();
      setDialog(null);
      setPaymentAmount("");
    },
  });
  const createReceipt = useMutation({
    mutationFn: () =>
      apiPost<GoodsReceipt>("/purchasing/goods-receipts/", {
        purchase_order: selectedId,
        received_by: grnReceivedBy,
        lines: Object.entries(grnQuantities)
          .filter(([, quantity]) => Number(quantity) > 0)
          .map(([order_line, quantity_received]) => ({ order_line, quantity_received })),
      }),
    onSuccess: async (receipt) => {
      await apiPost(`/purchasing/goods-receipts/${receipt.id}/confirm/`, {});
      await refreshDetail();
      setDialog(null);
      setGrnQuantities({});
      setGrnReceivedBy("");
    },
  });

  const results = query.data?.results ?? [];
  const order = detail.data;
  const updateLine = (index: number, field: keyof DraftLine, value: string) =>
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, [field]: value } : line)));

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Inventory & Purchase · Purchase Orders"
        title="Purchase Orders"
        description="Ordered materials, expected delivery, goods receipt, and supplier payment status in one place."
        actions={
          hasPermission(user, "purchasing.purchase_order.create") ? (
            <Button onClick={() => setOpen(true)}>
              <Plus data-icon="inline-start" />
              New Purchase Order
            </Button>
          ) : undefined
        }
      />
      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>Purchase Order register</CardTitle>
            <CardDescription>Open an order to submit, cancel, receive goods, or record a supplier payment.</CardDescription>
          </div>
          <div className="flex w-full gap-2 lg:max-w-xl">
            <form className="flex flex-1 gap-2" onSubmit={(event) => event.preventDefault()}>
              <Input aria-label="Search Purchase Orders" placeholder="PO number, supplier…" value={search} onChange={(event) => setSearch(event.target.value)} />
              <Button type="submit" variant="outline"><Search /></Button>
            </form>
            <NativeSelect aria-label="Purchase Order status" value={status} onChange={(event) => setStatus(event.target.value)}>
              <NativeSelectOption value="">All statuses</NativeSelectOption>
              <NativeSelectOption value="DRAFT">Draft</NativeSelectOption>
              <NativeSelectOption value="AWAITING_APPROVAL">Awaiting Approval</NativeSelectOption>
              <NativeSelectOption value="ORDERED">Ordered</NativeSelectOption>
              <NativeSelectOption value="PART_RECEIVED">Part Received</NativeSelectOption>
              <NativeSelectOption value="FULLY_RECEIVED">Fully Received</NativeSelectOption>
              <NativeSelectOption value="CANCELLED">Cancelled</NativeSelectOption>
              <NativeSelectOption value="CLOSED">Closed</NativeSelectOption>
            </NativeSelect>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {query.isPending ? (
            <div className="p-4"><ERPLoadingState rows={7} /></div>
          ) : query.isError ? (
            <div className="p-4"><ERPErrorState message={query.error.message} /></div>
          ) : !results.length ? (
            <div className="p-4"><ERPEmptyState title="No Purchase Orders found" description="Create a Purchase Order directly, or convert an approved requisition." /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>PO / supplier</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Payment</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => setSelectedId(item.id)}>
                      <TableCell>
                        <p className="font-semibold">{item.po_number}</p>
                        <p className="text-xs text-muted-foreground">{item.supplier_name}</p>
                      </TableCell>
                      <TableCell>{money(item.grand_total, item.currency_code)}</TableCell>
                      <TableCell><ERPStatusBadge value={item.status} label={item.status_label} /></TableCell>
                      <TableCell><ERPStatusBadge value={item.payment_status} label={item.payment_status_label} /></TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(item.updated_at)}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" aria-label={`Open ${item.po_number}`}><ArrowUpRight /></Button>
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
            <DialogTitle>New Purchase Order</DialogTitle>
            <DialogDescription>Record the supplier order. Stock updates only after goods receipt is confirmed.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="po-supplier">Supplier</FieldLabel>
              <NativeSelect id="po-supplier" value={form.supplier_id} onChange={(event) => setForm((c) => ({ ...c, supplier_id: event.target.value }))}>
                <NativeSelectOption value="">Choose supplier</NativeSelectOption>
                {suppliers.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>)}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="po-warehouse">Deliver to warehouse</FieldLabel>
              <NativeSelect id="po-warehouse" value={form.warehouse_id} onChange={(event) => setForm((c) => ({ ...c, warehouse_id: event.target.value }))}>
                <NativeSelectOption value="">Choose warehouse</NativeSelectOption>
                {warehouses.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>)}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="po-responsible">Responsible employee</FieldLabel>
              <NativeSelect id="po-responsible" value={form.responsible_employee_id} onChange={(event) => setForm((c) => ({ ...c, responsible_employee_id: event.target.value }))}>
                <NativeSelectOption value="">Choose employee</NativeSelectOption>
                {employees.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.display_name}</NativeSelectOption>)}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="po-currency">Currency</FieldLabel>
              <NativeSelect id="po-currency" value={form.currency_id} onChange={(event) => setForm((c) => ({ ...c, currency_id: event.target.value }))}>
                <NativeSelectOption value="">Choose currency</NativeSelectOption>
                {currencies.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.code}</NativeSelectOption>)}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="po-delivery-date">Expected delivery</FieldLabel>
              <Input id="po-delivery-date" type="date" value={form.expected_delivery_date} onChange={(event) => setForm((c) => ({ ...c, expected_delivery_date: event.target.value }))} />
            </Field>
          </div>
          <div className="mt-2">
            <p className="mb-2 text-sm font-medium">Ordered items</p>
            <div className="grid gap-2">
              {lines.map((line, index) => (
                <div key={index} className="grid grid-cols-[1fr_90px_110px_80px_auto] items-end gap-2">
                  <Field>
                    <FieldLabel htmlFor={`po-line-product-${index}`}>Product</FieldLabel>
                    <NativeSelect id={`po-line-product-${index}`} value={line.product} onChange={(event) => updateLine(index, "product", event.target.value)}>
                      <NativeSelectOption value="">Choose product</NativeSelectOption>
                      {products.data?.results.map((product) => <NativeSelectOption key={product.id} value={product.id}>{product.internal_code}</NativeSelectOption>)}
                    </NativeSelect>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`po-line-qty-${index}`}>Qty</FieldLabel>
                    <Input id={`po-line-qty-${index}`} type="number" min="0.0001" step="0.0001" value={line.quantity} onChange={(event) => updateLine(index, "quantity", event.target.value)} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`po-line-price-${index}`}>Unit price</FieldLabel>
                    <Input id={`po-line-price-${index}`} type="number" min="0" step="0.01" value={line.unit_price} onChange={(event) => updateLine(index, "unit_price", event.target.value)} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`po-line-tax-${index}`}>Tax %</FieldLabel>
                    <Input id={`po-line-tax-${index}`} type="number" min="0" max="100" value={line.tax_percent} onChange={(event) => updateLine(index, "tax_percent", event.target.value)} />
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
          {create.isError ? <ERPErrorState title="Purchase Order could not be saved" message={create.error instanceof ApiError ? create.error.message : "The request could not be completed."} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={create.isPending || !form.supplier_id || !form.warehouse_id || !form.responsible_employee_id || !form.currency_id || !lines.some((line) => line.product)}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Saving…" : "Save Purchase Order"}
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
          ) : order ? (
            <>
              <DialogHeader>
                <DialogTitle>{order.po_number} · {order.supplier_name}</DialogTitle>
                <DialogDescription>{money(order.grand_total, order.currency_code)} · Balance due {money(order.balance_due, order.currency_code)}</DialogDescription>
              </DialogHeader>
              <div className="flex flex-wrap items-center gap-2">
                <ERPStatusBadge value={order.status} label={order.status_label} />
                <ERPStatusBadge value={order.payment_status} label={order.payment_status_label} />
              </div>
              <Tabs defaultValue="lines" className="gap-3">
                <TabsList>
                  <TabsTrigger value="lines">Lines</TabsTrigger>
                  <TabsTrigger value="receipts">Goods receipts</TabsTrigger>
                </TabsList>
                <TabsContent value="lines">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead className="text-right">Ordered</TableHead>
                          <TableHead className="text-right">Received</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {order.lines.map((line) => (
                          <TableRow key={line.id}>
                            <TableCell>
                              <p className="font-medium">{line.product_code}</p>
                              <p className="text-xs text-muted-foreground">{line.product_description}</p>
                            </TableCell>
                            <TableCell className="text-right">{Number(line.quantity).toLocaleString("en-IN")}</TableCell>
                            <TableCell className="text-right">{Number(line.received_quantity).toLocaleString("en-IN")}</TableCell>
                            <TableCell className="text-right">{money(line.total_amount, order.currency_code)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>
                <TabsContent value="receipts">
                  {receipts.isPending ? <ERPLoadingState rows={3} /> : !receipts.data?.results.length ? (
                    <ERPEmptyState title="No goods received yet" description="Record a GRN once material arrives from the supplier." />
                  ) : (
                    <div className="grid gap-2">
                      {receipts.data.results.map((receipt) => (
                        <div key={receipt.id} className="rounded-lg border p-3">
                          <div className="flex justify-between gap-2">
                            <p className="font-medium">{receipt.grn_number}</p>
                            <ERPStatusBadge value={receipt.status} label={receipt.status_label} />
                          </div>
                          <p className="text-xs text-muted-foreground">{receipt.received_by_name} · {formatDateTime(receipt.received_date)}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
              <DialogFooter className="flex-wrap gap-2">
                <Button variant="outline" onClick={() => { setSelectedId(null); setDialog(null); }}>Close</Button>
                {order.status === "DRAFT" && hasPermission(user, "purchasing.purchase_order.submit") ? (
                  <Button onClick={() => submit.mutate(order.id)} disabled={submit.isPending}>{submit.isPending ? "Submitting…" : "Submit"}</Button>
                ) : null}
                {["ORDERED", "PART_RECEIVED", "DELAYED"].includes(order.status) && hasPermission(user, "purchasing.goods_receipt.create") ? (
                  <Button onClick={() => setDialog("grn")}>Record goods receipt</Button>
                ) : null}
                {hasPermission(user, "purchasing.purchase_order.record_payment") ? (
                  <Button variant="outline" onClick={() => setDialog("payment")}>Record payment</Button>
                ) : null}
                {!["FULLY_RECEIVED", "CLOSED", "CANCELLED"].includes(order.status) && hasPermission(user, "purchasing.purchase_order.cancel") ? (
                  <Button variant="destructive" onClick={() => setDialog("cancel")}>Cancel</Button>
                ) : null}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "cancel"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Purchase Order</DialogTitle>
            <DialogDescription>Give a clear business reason so colleagues understand the change.</DialogDescription>
          </DialogHeader>
          <Field><FieldLabel htmlFor="po-cancel-reason">Reason</FieldLabel><Textarea id="po-cancel-reason" value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
          {cancel.isError ? <ERPErrorState message={cancel.error instanceof ApiError ? cancel.error.message : "The request could not be completed."} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Back</Button>
            <Button variant="destructive" disabled={!reason.trim() || cancel.isPending} onClick={() => order && cancel.mutate(order.id)}>
              {cancel.isPending ? "Working…" : "Confirm cancellation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "payment"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record supplier payment</DialogTitle>
            <DialogDescription>Record what was paid and the resulting payment status.</DialogDescription>
          </DialogHeader>
          <Field><FieldLabel htmlFor="po-payment-amount">Amount paid</FieldLabel><Input id="po-payment-amount" type="number" min="0" step="0.01" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} /></Field>
          <Field>
            <FieldLabel htmlFor="po-payment-status">Payment status</FieldLabel>
            <NativeSelect id="po-payment-status" value={paymentStatus} onChange={(event) => setPaymentStatus(event.target.value)}>
              <NativeSelectOption value="PART_PAID">Part Paid</NativeSelectOption>
              <NativeSelectOption value="PAID">Paid</NativeSelectOption>
              <NativeSelectOption value="OVERDUE">Overdue</NativeSelectOption>
              <NativeSelectOption value="ON_HOLD">On Hold</NativeSelectOption>
              <NativeSelectOption value="DISPUTED">Disputed</NativeSelectOption>
            </NativeSelect>
          </Field>
          {recordPayment.isError ? <ERPErrorState message={recordPayment.error instanceof ApiError ? recordPayment.error.message : "The request could not be completed."} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Back</Button>
            <Button disabled={!paymentAmount || recordPayment.isPending} onClick={() => order && recordPayment.mutate(order.id)}>
              {recordPayment.isPending ? "Recording…" : "Record payment"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "grn"} onOpenChange={(value) => !value && setDialog(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Record goods receipt</DialogTitle>
            <DialogDescription>Enter the quantity received per line. Stock updates immediately on confirmation.</DialogDescription>
          </DialogHeader>
          <Field>
            <FieldLabel htmlFor="grn-received-by">Received by</FieldLabel>
            <NativeSelect id="grn-received-by" value={grnReceivedBy} onChange={(event) => setGrnReceivedBy(event.target.value)}>
              <NativeSelectOption value="">Choose employee</NativeSelectOption>
              {employees.data?.results.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.display_name}</NativeSelectOption>)}
            </NativeSelect>
          </Field>
          <div className="grid gap-2">
            {order?.lines.filter((line) => Number(line.pending_quantity) > 0).map((line) => (
              <div key={line.id} className="grid grid-cols-[1fr_120px] items-end gap-2">
                <div>
                  <p className="text-sm font-medium">{line.product_code}</p>
                  <p className="text-xs text-muted-foreground">Pending {Number(line.pending_quantity).toLocaleString("en-IN")}</p>
                </div>
                <Field>
                  <FieldLabel htmlFor={`grn-qty-${line.id}`}>Qty received</FieldLabel>
                  <Input
                    id={`grn-qty-${line.id}`}
                    type="number"
                    min="0"
                    max={line.pending_quantity}
                    step="0.0001"
                    value={grnQuantities[line.id] ?? ""}
                    onChange={(event) => setGrnQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                  />
                </Field>
              </div>
            ))}
          </div>
          {createReceipt.isError ? <ERPErrorState message={createReceipt.error instanceof ApiError ? createReceipt.error.message : "The request could not be completed."} /> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>Back</Button>
            <Button
              disabled={!grnReceivedBy || createReceipt.isPending || !Object.values(grnQuantities).some((v) => Number(v) > 0)}
              onClick={() => createReceipt.mutate()}
            >
              {createReceipt.isPending ? "Recording…" : "Confirm receipt"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
