import { ArrowRight, Boxes, ClipboardList, PackageSearch, Tags, Truck, Warehouse } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ERPEmptyState, ERPPageHeader } from "@/production/components/shared";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";

const registers = [
  {
    title: "Stock register",
    description:
      "Current balances by warehouse and condition, the movement ledger, and low-stock alerts.",
    to: "/app/inventory/stock",
    permission: "inventory.stock.view",
    icon: Warehouse,
    action: "Open stock register",
  },
  {
    title: "Products",
    description:
      "Brand, part number, specification, alternates, warranty, and reorder settings.",
    to: "/app/inventory/products",
    permission: "inventory.product.view",
    icon: Boxes,
    action: "Open products",
  },
  {
    title: "Suppliers",
    description: "Vendors who supply the parts and materials stocked and sold.",
    to: "/app/inventory/suppliers",
    permission: "inventory.supplier.view",
    icon: Truck,
    action: "Open suppliers",
  },
  {
    title: "Product categories",
    description: "Groupings used to organise the product catalogue.",
    to: "/app/inventory/product-categories",
    permission: "inventory.product.view",
    icon: Tags,
    action: "Open categories",
  },
  {
    title: "Purchase Requisitions",
    description: "What stores or workshop need to buy, before it becomes a Purchase Order.",
    to: "/app/purchasing/requisitions",
    permission: "purchasing.requisition.view",
    icon: ClipboardList,
    action: "Open requisitions",
  },
  {
    title: "Purchase Orders",
    description: "Ordered materials, expected delivery, goods receipt, and supplier payment status.",
    to: "/app/purchasing/orders",
    permission: "purchasing.purchase_order.view",
    icon: PackageSearch,
    action: "Open Purchase Orders",
  },
];

export default function InventoryWorkspacePage() {
  const { data: user } = useCurrentUser();
  const visible = registers.filter((item) => hasPermission(user, item.permission));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <ERPPageHeader
        eyebrow="Inventory & Purchase"
        title="Inventory"
        description="Stock balances, movements, products, and suppliers in one place."
      />
      {visible.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {visible.map((item, index) => {
            const Icon = item.icon;
            return (
              <Card key={item.to} className={index === 0 ? "border-primary/30" : undefined}>
                <CardHeader>
                  <Icon aria-hidden="true" className="text-primary" />
                  <CardTitle className="mt-3">{item.title}</CardTitle>
                  <CardDescription className="leading-6">{item.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    className="w-full justify-between"
                    variant={index === 0 ? "default" : "outline"}
                    nativeButton={false}
                    render={<Link to={item.to} />}
                  >
                    {item.action}
                    <ArrowRight data-icon="inline-end" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <ERPEmptyState
          title="No inventory registers available"
          description="Your current responsibilities do not include products, suppliers, or stock."
        />
      )}
    </div>
  );
}
