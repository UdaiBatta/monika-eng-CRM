import {
  ArrowRight,
  ClipboardCheck,
  FileText,
  ShoppingCart,
} from "lucide-react";
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
    title: "Quotations",
    description:
      "Prepare, finalize, share, revise, and record the customer's decision.",
    to: "/app/crm/quotations",
    permission: "crm.quotation.view",
    icon: FileText,
    action: "Open quotations",
  },
  {
    title: "Customer confirmations & POs",
    description:
      "Record the customer's commitment, PO-pending position, and formal purchase order.",
    to: "/app/sales/customer-pos",
    permission: "sales.customer_po.view",
    icon: ShoppingCart,
    action: "Open confirmations & POs",
  },
  {
    title: "Sales Orders",
    description:
      "Turn confirmed commercial work into a controlled, releasable internal order.",
    to: "/app/sales/orders",
    permission: "sales.sales_order.view",
    icon: ClipboardCheck,
    action: "Open Sales Orders",
  },
];

export default function SalesWorkspacePage() {
  const { data: user } = useCurrentUser();
  const visible = registers.filter((item) =>
    hasPermission(user, item.permission),
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <ERPPageHeader
        eyebrow="Commercial CRM"
        title="Quotations & Orders"
        description="One commercial workspace from an approved requirement to the released Sales Order. Open a register only when you need the wider team view."
      />
      {visible.length ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {visible.map((item, index) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.to}
                className={index === 0 ? "border-primary/30" : undefined}
              >
                <CardHeader>
                  <Icon aria-hidden="true" className="text-primary" />
                  <CardTitle className="mt-3">{item.title}</CardTitle>
                  <CardDescription className="leading-6">
                    {item.description}
                  </CardDescription>
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
          title="No commercial registers available"
          description="Your current responsibilities do not include quotations, customer POs, or Sales Orders."
        />
      )}
    </div>
  );
}

