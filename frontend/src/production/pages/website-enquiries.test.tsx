import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import WebsiteEnquiriesPage from "./website-enquiries-page";
import WebsiteEnquiryPage from "./website-enquiry-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  user: {
    id: "user-1",
    email: "admin@monika.local",
    first_name: "Development",
    last_name: "Administrator",
    is_active: true,
    is_staff: true,
    employee: {
      id: "employee-1",
      employee_code: "ME-001",
      display_name: "Development Administrator",
      company_id: "company-1",
    },
    permissions: [
      "crm.external_enquiry.view",
      "crm.external_enquiry.review",
      "crm.external_enquiry.assign",
      "crm.external_enquiry.convert",
      "crm.external_enquiry.reject",
      "crm.external_enquiry.mark_spam",
      "crm.customer.view",
      "crm.contact.view",
    ],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
}));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) =>
    Boolean(user?.permissions.includes(permission)),
}));

const pagination = {
  count: 1,
  page: 1,
  page_size: 25,
  pages: 1,
  next: null,
  previous: null,
};

const submission = {
  id: "submission-1",
  company: "company-1",
  external_submission_id: "WEB-2026-1001",
  channel: "WEBSITE",
  source_type: "PRODUCT_QUOTE",
  received_at: "2026-08-11T09:00:00Z",
  submitted_at: "2026-08-11T08:59:00Z",
  person_name: "Asha Rao",
  company_name: "ABC Industries Pvt. Ltd.",
  email: "asha@abc.test",
  phone: "+91 90000 00000",
  subject: "MCC control panel RFQ",
  message: "Please quote a 12-feeder MCC panel with drawings.",
  product_reference: "MCC-12",
  product_name: "MCC control panel",
  product_url: "https://monikaengineers.co.in/products/mcc",
  source_page_url: "https://monikaengineers.co.in/contact",
  referrer_url: "https://google.com/",
  utm_source: "google",
  utm_medium: "organic",
  utm_campaign: "",
  spam_status: "LIKELY_VALID",
  spam_score: null,
  review_status: "POSSIBLE_DUPLICATE",
  duplicate_status: "POSSIBLE",
  matched_customer: "customer-1",
  matched_customer_name: "ABC Industries Pvt. Ltd.",
  matched_contact: "contact-1",
  matched_contact_name: "Asha Rao",
  converted_customer: null,
  converted_customer_name: "",
  converted_contact: null,
  converted_contact_name: "",
  converted_enquiry: null,
  converted_enquiry_number: "",
  assigned_to: "employee-1",
  assigned_to_name: "Development Administrator",
  priority: "HIGH",
  reviewed_at: null,
  converted_at: null,
  rejection_reason: "",
  attachments: [],
  created_at: "2026-08-11T09:00:00Z",
  updated_at: "2026-08-11T09:00:00Z",
};

function renderAt(node: React.ReactNode, path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("secure website enquiry frontend", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
  });

  it("renders the responsive review inbox from the internal API", async () => {
    mocks.apiGet.mockResolvedValue({ results: [submission], pagination });
    renderAt(<WebsiteEnquiriesPage />, "/app/crm/website-enquiries");

    expect(screen.getByText("Website enquiry inbox")).toBeInTheDocument();
    expect((await screen.findAllByText("ABC Industries Pvt. Ltd.")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("MCC control panel RFQ").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Possible duplicate").length).toBeGreaterThan(0);
    expect(mocks.apiGet).toHaveBeenCalledWith(expect.stringContaining("/external-enquiries/?"));
  });

  it("converts a reviewed website RFQ using selected CRM records", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path === "/external-enquiries/submission-1/") return Promise.resolve(submission);
      if (path.endsWith("/candidates/")) {
        return Promise.resolve({
          customers: [{ id: "customer-1", customer_code: "CUS-0001", legal_name: "ABC Industries Pvt. Ltd.", status: "ACTIVE", reasons: ["Email matches"] }],
          contacts: [{ id: "contact-1", display_name: "Asha Rao", customer_id: "customer-1", customer_code: "CUS-0001", customer_name: "ABC Industries Pvt. Ltd.", reasons: ["Email matches"] }],
        });
      }
      if (path.startsWith("/employees/")) return Promise.resolve({ results: [mocks.user.employee], pagination });
      if (path.startsWith("/customers/")) return Promise.resolve({ results: [{ id: "customer-1", legal_name: "ABC Industries Pvt. Ltd.", customer_code: "CUS-0001" }], pagination });
      if (path.startsWith("/customer-contacts/")) return Promise.resolve({ results: [{ id: "contact-1", display_name: "Asha Rao", email: "asha@abc.test", phone: "" }], pagination });
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPost.mockResolvedValue({
      ...submission,
      review_status: "CONVERTED",
      converted_enquiry: "enquiry-1",
      converted_enquiry_number: "ENQ-2026-0002",
    });
    const user = userEvent.setup();
    renderAt(
      <Routes>
        <Route path="/app/crm/website-enquiries/:submissionId" element={<WebsiteEnquiryPage />} />
      </Routes>,
      "/app/crm/website-enquiries/submission-1",
    );

    await user.click(await screen.findByRole("tab", { name: "CRM conversion" }));
    await user.click(screen.getByRole("button", { name: /Convert to CRM enquiry/i }));

    await waitFor(() =>
      expect(mocks.apiPost).toHaveBeenCalledWith(
        "/external-enquiries/submission-1/convert/",
        expect.objectContaining({
          customer_id: "customer-1",
          contact_id: "contact-1",
          responsible_salesperson_id: "employee-1",
        }),
      ),
    );
  });
});
