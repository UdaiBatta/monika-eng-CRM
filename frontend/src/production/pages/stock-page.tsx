import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ClipboardList, Package, Plus } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPPageHeader, formatDateTime } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  LowStockRow,
  MovementType,
  Product,
  StockCondition,
  StockItem,
  StockLocation,
  StockMovement,
} from "@/production/lib/inventory-types";
import type { Paginated } from "@/production/lib/types";

const CONDITIONS: StockCondition[] = ["AVAILABLE", "RESERVED", "DAMAGED", "REPAIR_HELD", "DEMO", "IN_TRANSIT"];
const MOVEMENT_TYPES: { value: MovementType; label: string; needsFrom: boolean; needsTo: boolean }[] = [
  { value: "INWARD", label: "Inward (goods received)", needsFrom: false, needsTo: true },
  { value: "OUTWARD", label: "Outward (dispatch/consumption)", needsFrom: true, needsTo: false },
  { value: "TRANSFER", label: "Transfer between locations", needsFrom: true, needsTo: true },
  { value: "ADJUSTMENT", label: "Adjustment (cycle count/damage)", needsFrom: false, needsTo: false },
  { value: "RETURN", label: "Return to stock", needsFrom: false, needsTo: true },
];

type MovementForm = {
  movement_type: MovementType;
  product: string;
  quantity: string;
  from_location: string;
  from_condition: StockCondition | "";
  to_location: string;
  to_condition: StockCondition | "";
  reason: string;
};

const emptyForm: MovementForm = {
  movement_type: "INWARD",
  product: "",
  quantity: "1",
  from_location: "",
  from_condition: "",
  to_location: "",
  to_condition: "AVAILABLE",
  reason: "",
};

export default function StockPage() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<MovementForm>(emptyForm);

  const itemsQuery = useQuery({
    queryKey: ["stock-items"],
    queryFn: () => apiGet<Paginated<StockItem>>("/inventory/stock-items/?page_size=200&ordering=product__description"),
  });
  const movementsQuery = useQuery({
    queryKey: ["stock-movements"],
    queryFn: () => apiGet<Paginated<StockMovement>>("/inventory/stock-movements/?page_size=100&ordering=-created_at"),
  });
  const lowStockQuery = useQuery({
    queryKey: ["low-stock"],
    queryFn: () => apiGet<LowStockRow[]>("/inventory/products/low-stock/"),
  });
  const productsQuery = useQuery({
    queryKey: ["products-for-movement"],
    queryFn: () => apiGet<Paginated<Product>>("/inventory/products/?page_size=500&is_active=true"),
    enabled: dialogOpen,
  });
  const locationsQuery = useQuery({
    queryKey: ["stock-locations-for-movement"],
    queryFn: () => apiGet<Paginated<StockLocation>>("/inventory/stock-locations/?page_size=500"),
    enabled: dialogOpen,
  });

  const canManage = hasPermission(user, "inventory.stock.manage");

  const record = useMutation({
    mutationFn: () =>
      apiPost("/inventory/stock-movements/record/", {
        movement_type: form.movement_type,
        product: form.product,
        quantity: form.quantity,
        from_location: form.from_location || undefined,
        from_condition: form.from_condition || undefined,
        to_location: form.to_location || undefined,
        to_condition: form.to_condition || undefined,
        reason: form.reason,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["stock-items"] }),
        queryClient.invalidateQueries({ queryKey: ["stock-movements"] }),
        queryClient.invalidateQueries({ queryKey: ["low-stock"] }),
      ]);
      setDialogOpen(false);
      setForm(emptyForm);
    },
  });

  const selectedType = MOVEMENT_TYPES.find((type) => type.value === form.movement_type) ?? MOVEMENT_TYPES[0];
  const canSubmit =
    form.product &&
    Number(form.quantity) > 0 &&
    (!selectedType.needsFrom || (form.from_location && form.from_condition)) &&
    (!selectedType.needsTo || (form.to_location && form.to_condition)) &&
    (form.movement_type !== "ADJUSTMENT" || form.reason.trim());

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Inventory & Purchase · Stock"
        title="Stock register"
        description="Current balances by warehouse and condition, the movement ledger behind them, and parts due for reorder."
        actions={
          canManage ? (
            <Button onClick={() => setDialogOpen(true)}>
              <Plus data-icon="inline-start" />
              Record movement
            </Button>
          ) : undefined
        }
      />
      {record.isError ? (
        <ERPErrorState title="Movement could not be recorded" message={record.error instanceof ApiError ? record.error.message : "The request could not be completed."} />
      ) : null}

      <Tabs defaultValue="balances" className="gap-4">
        <TabsList className="h-auto w-full justify-start overflow-x-auto">
          <TabsTrigger value="balances">
            <Package data-icon="inline-start" />
            Stock balances
          </TabsTrigger>
          <TabsTrigger value="movements">
            <ClipboardList data-icon="inline-start" />
            Movement history
          </TabsTrigger>
          <TabsTrigger value="low-stock">
            <AlertTriangle data-icon="inline-start" />
            Low stock{lowStockQuery.data?.length ? ` (${lowStockQuery.data.length})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="balances" className="mt-0">
          <Card>
            <CardHeader>
              <CardTitle>Balances by location and condition</CardTitle>
              <CardDescription>Only movements change these figures — balances are never edited directly.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {itemsQuery.isPending ? (
                <div className="p-4"><ERPLoadingState rows={6} /></div>
              ) : itemsQuery.isError ? (
                <div className="p-4"><ERPErrorState message={itemsQuery.error.message} /></div>
              ) : !itemsQuery.data?.results.length ? (
                <div className="p-4"><ERPEmptyState title="No stock recorded yet" description="Record an inward movement or import opening balances to get started." /></div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>Location</TableHead>
                        <TableHead>Condition</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {itemsQuery.data.results.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>
                            <p className="font-medium">{item.product_code}</p>
                            <p className="text-xs text-muted-foreground">{item.product_description}</p>
                          </TableCell>
                          <TableCell>{item.location_label}</TableCell>
                          <TableCell>{item.condition_label}</TableCell>
                          <TableCell className="text-right font-semibold">{Number(item.quantity).toLocaleString("en-IN")}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="movements" className="mt-0">
          <Card>
            <CardHeader>
              <CardTitle>Movement ledger</CardTitle>
              <CardDescription>Every inward, outward, reservation, transfer, and adjustment — permanent and immutable.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {movementsQuery.isPending ? (
                <div className="p-4"><ERPLoadingState rows={6} /></div>
              ) : movementsQuery.isError ? (
                <div className="p-4"><ERPErrorState message={movementsQuery.error.message} /></div>
              ) : !movementsQuery.data?.results.length ? (
                <div className="p-4"><ERPEmptyState title="No movements yet" description="Movements appear here as soon as stock is recorded." /></div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Movement</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Product</TableHead>
                        <TableHead>From → To</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead>By</TableHead>
                        <TableHead>When</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {movementsQuery.data.results.map((movement) => (
                        <TableRow key={movement.id}>
                          <TableCell className="font-medium">{movement.movement_number}</TableCell>
                          <TableCell>{movement.movement_type_label}</TableCell>
                          <TableCell>{movement.product_code}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {movement.from_location_label ? `${movement.from_location_label} (${movement.from_condition})` : "—"}
                            {" → "}
                            {movement.to_location_label ? `${movement.to_location_label} (${movement.to_condition})` : "—"}
                          </TableCell>
                          <TableCell className="text-right">{Number(movement.quantity).toLocaleString("en-IN")}</TableCell>
                          <TableCell>{movement.created_by_name || "—"}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatDateTime(movement.created_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="low-stock" className="mt-0">
          <Card>
            <CardHeader>
              <CardTitle>Products at or below reorder level</CardTitle>
              <CardDescription>Compares available stock against each product's configured reorder level.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {lowStockQuery.isPending ? (
                <div className="p-4"><ERPLoadingState rows={4} /></div>
              ) : lowStockQuery.isError ? (
                <div className="p-4"><ERPErrorState message={lowStockQuery.error.message} /></div>
              ) : !lowStockQuery.data?.length ? (
                <div className="p-4"><ERPEmptyState title="Nothing is low on stock" description="All products with a reorder level are above it." /></div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead className="text-right">Available</TableHead>
                        <TableHead className="text-right">Reorder level</TableHead>
                        <TableHead className="text-right">Suggested reorder qty</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {lowStockQuery.data.map((row) => (
                        <TableRow key={row.product_id}>
                          <TableCell>
                            <p className="font-medium">{row.internal_code}</p>
                            <p className="text-xs text-muted-foreground">{row.description}</p>
                          </TableCell>
                          <TableCell className="text-right font-semibold text-status-warning">{row.available_quantity}</TableCell>
                          <TableCell className="text-right">{row.reorder_level}</TableCell>
                          <TableCell className="text-right">{row.reorder_quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={(value) => { setDialogOpen(value); if (!value) setForm(emptyForm); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record stock movement</DialogTitle>
            <DialogDescription>Every balance change goes through a movement — this keeps the stock ledger auditable.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="movement-type">Movement type</FieldLabel>
              <NativeSelect
                id="movement-type"
                value={form.movement_type}
                onChange={(event) => setForm((current) => ({ ...current, movement_type: event.target.value as MovementType }))}
              >
                {MOVEMENT_TYPES.map((type) => (
                  <NativeSelectOption key={type.value} value={type.value}>{type.label}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="movement-product">Product</FieldLabel>
              <NativeSelect
                id="movement-product"
                value={form.product}
                onChange={(event) => setForm((current) => ({ ...current, product: event.target.value }))}
              >
                <NativeSelectOption value="">Choose product</NativeSelectOption>
                {productsQuery.data?.results.map((product) => (
                  <NativeSelectOption key={product.id} value={product.id}>{product.internal_code} · {product.description}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="movement-quantity">Quantity</FieldLabel>
              <Input
                id="movement-quantity"
                type="number"
                min="0.0001"
                step="0.0001"
                value={form.quantity}
                onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))}
              />
            </Field>
            {selectedType.needsFrom ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="movement-from-location">From location</FieldLabel>
                  <NativeSelect
                    id="movement-from-location"
                    value={form.from_location}
                    onChange={(event) => setForm((current) => ({ ...current, from_location: event.target.value }))}
                  >
                    <NativeSelectOption value="">Choose location</NativeSelectOption>
                    {locationsQuery.data?.results.map((location) => (
                      <NativeSelectOption key={location.id} value={location.id}>{location.warehouse_name}{location.bin_code ? ` · ${location.bin_code}` : ""}</NativeSelectOption>
                    ))}
                  </NativeSelect>
                </Field>
                <Field>
                  <FieldLabel htmlFor="movement-from-condition">From condition</FieldLabel>
                  <NativeSelect
                    id="movement-from-condition"
                    value={form.from_condition}
                    onChange={(event) => setForm((current) => ({ ...current, from_condition: event.target.value as StockCondition }))}
                  >
                    <NativeSelectOption value="">Choose condition</NativeSelectOption>
                    {CONDITIONS.map((condition) => (
                      <NativeSelectOption key={condition} value={condition}>{condition.replaceAll("_", " ")}</NativeSelectOption>
                    ))}
                  </NativeSelect>
                </Field>
              </div>
            ) : null}
            {selectedType.needsTo || form.movement_type === "ADJUSTMENT" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="movement-to-location">To location</FieldLabel>
                  <NativeSelect
                    id="movement-to-location"
                    value={form.to_location}
                    onChange={(event) => setForm((current) => ({ ...current, to_location: event.target.value }))}
                  >
                    <NativeSelectOption value="">Choose location</NativeSelectOption>
                    {locationsQuery.data?.results.map((location) => (
                      <NativeSelectOption key={location.id} value={location.id}>{location.warehouse_name}{location.bin_code ? ` · ${location.bin_code}` : ""}</NativeSelectOption>
                    ))}
                  </NativeSelect>
                </Field>
                <Field>
                  <FieldLabel htmlFor="movement-to-condition">To condition</FieldLabel>
                  <NativeSelect
                    id="movement-to-condition"
                    value={form.to_condition}
                    onChange={(event) => setForm((current) => ({ ...current, to_condition: event.target.value as StockCondition }))}
                  >
                    <NativeSelectOption value="">Choose condition</NativeSelectOption>
                    {CONDITIONS.map((condition) => (
                      <NativeSelectOption key={condition} value={condition}>{condition.replaceAll("_", " ")}</NativeSelectOption>
                    ))}
                  </NativeSelect>
                </Field>
              </div>
            ) : null}
            {form.movement_type === "ADJUSTMENT" ? (
              <Alert>
                <AlertTriangle />
                <AlertTitle>Reason required</AlertTitle>
                <AlertDescription>Adjustments must state why the balance changed (e.g. cycle count, damage found).</AlertDescription>
              </Alert>
            ) : null}
            <Field>
              <FieldLabel htmlFor="movement-reason">Reason{form.movement_type === "ADJUSTMENT" ? "" : " (optional)"}</FieldLabel>
              <Textarea id="movement-reason" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button disabled={!canSubmit || record.isPending} onClick={() => record.mutate()}>
              {record.isPending ? "Recording…" : "Record movement"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
