import { ArrowRight, ClipboardList, Inbox } from "lucide-react";
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

export default function EnquiryWorkspacePage() {
  const { data: user } = useCurrentUser();
  const areas = [
    {
      title: "New enquiries",
      description:
        "Review website, email, phone, WhatsApp, TradeIndia, and manually received requests before they enter the CRM.",
      to: "/app/crm/incoming-enquiries",
      permission: "crm.external_enquiry.view",
      icon: Inbox,
      action: "Review new enquiries",
    },
    {
      title: "Enquiry register",
      description:
        "Find qualified customer requests, Workshop progress, due dates, and the next commercial step.",
      to: "/app/crm/enquiries",
      permission: "enquiry.enquiry.view",
      icon: ClipboardList,
      action: "Open enquiry register",
    },
  ].filter((item) => hasPermission(user, item.permission));

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <ERPPageHeader
        eyebrow="Sales · Daily work"
        title="Enquiries"
        description="Start with requests that need review, or find an existing enquiry without having to know which internal record type it uses."
      />
      {areas.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {areas.map((item, index) => {
            const Icon = item.icon;
            return (
              <Card key={item.to} className={index === 0 ? "border-primary/30" : undefined}>
                <CardHeader>
                  <Icon aria-hidden="true" className="text-primary" />
                  <CardTitle className="mt-3">{item.title}</CardTitle>
                  <CardDescription className="leading-6">{item.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button className="w-full justify-between" variant={index === 0 ? "default" : "outline"} nativeButton={false} render={<Link to={item.to} />}>
                    {item.action}<ArrowRight data-icon="inline-end" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <ERPEmptyState title="No enquiry responsibility assigned" description="Ask your manager if you should be able to review or work on enquiries." />
      )}
    </div>
  );
}

