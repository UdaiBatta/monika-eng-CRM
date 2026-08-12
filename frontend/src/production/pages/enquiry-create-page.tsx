import { useNavigate, useSearchParams } from "react-router-dom";

import { Card, CardContent } from "@/components/ui/card";
import { EnquiryForm } from "@/production/components/enquiry-forms";
import { ERPPageHeader } from "@/production/components/shared";

export default function EnquiryCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM / Enquiries"
        title="New enquiry / RFQ"
        description="Capture the customer request as a controlled draft, then complete its requirements and item lines in the enquiry workspace."
      />
      <Card>
        <CardContent className="p-5 sm:p-6">
          <EnquiryForm
            initialCustomerId={searchParams.get("customer") ?? ""}
            onSaved={(saved) =>
              navigate(`/app/crm/enquiries/${saved.id}`, { replace: true })
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
