import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PackageCheck, PackageMinus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { ERPErrorState } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { StockLocation } from "@/production/lib/inventory-types";
import type { SalesOrderLine } from "@/production/lib/sales-types";
import type { Paginated } from "@/production/lib/types";

type PendingAction = { line: SalesOrderLine; kind: "reserve" | "release" };

export function StockReservationCard({ orderId, lines }: { orderId: string; lines: SalesOrderLine[] }) {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [locationId, setLocationId] = useState("");

  const productLines = lines.filter((line) => line.product);
  const locationsQuery = useQuery({
    queryKey: ["stock-locations-for-reservation"],
    queryFn: () => apiGet<Paginated<StockLocation>>("/inventory/stock-locations/?page_size=500"),
    enabled: Boolean(pending),
  });

  const mutate = useMutation({
    mutationFn: ({ line, kind }: PendingAction) =>
      apiPost(`/inventory/sales-order-lines/${line.id}/${kind}/`, { location: locationId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sales-order", orderId] });
      await queryClient.invalidateQueries({ queryKey: ["stock-items"] });
      setPending(null);
      setLocationId("");
    },
  });

  const canReserve = hasPermission(user, "inventory.stock.reserve");
  if (!productLines.length || !canReserve) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PackageCheck className="text-primary" />
          Stock reservation
        </CardTitle>
        <CardDescription>Reserve stock against a line's linked product so it cannot be promised twice.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {mutate.isError ? (
          <ERPErrorState title="Reservation could not be completed" message={mutate.error instanceof ApiError ? mutate.error.message : "The request could not be completed."} />
        ) : null}
        {productLines.map((line) => (
          <div key={line.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3">
            <div>
              <p className="font-medium">{line.product_code} · {line.description}</p>
              <p className="text-xs text-muted-foreground">Quantity {Number(line.quantity).toLocaleString("en-IN")}</p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setPending({ line, kind: "reserve" })}>
                <PackageCheck data-icon="inline-start" />
                Reserve stock
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setPending({ line, kind: "release" })}>
                <PackageMinus data-icon="inline-start" />
                Release
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
      <Dialog open={Boolean(pending)} onOpenChange={(value) => !value && setPending(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{pending?.kind === "release" ? "Release reservation" : "Reserve stock"}</DialogTitle>
            <DialogDescription>Choose the warehouse location to move stock against for this line.</DialogDescription>
          </DialogHeader>
          <Field>
            <FieldLabel htmlFor="reservation-location">Location</FieldLabel>
            <NativeSelect id="reservation-location" value={locationId} onChange={(event) => setLocationId(event.target.value)}>
              <NativeSelectOption value="">Choose location</NativeSelectOption>
              {locationsQuery.data?.results.map((location) => (
                <NativeSelectOption key={location.id} value={location.id}>
                  {location.warehouse_name}{location.bin_code ? ` · ${location.bin_code}` : ""}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>Cancel</Button>
            <Button disabled={!locationId || mutate.isPending || !pending} onClick={() => pending && mutate.mutate(pending)}>
              {mutate.isPending ? "Working…" : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
