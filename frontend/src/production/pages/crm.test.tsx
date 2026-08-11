import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import ActivitiesPage from "./activities-page";
import CustomerPage from "./customer-page";
import CustomersPage from "./customers-page";
import EnquiriesPage from "./enquiries-page";
import EnquiryPage from "./enquiry-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  user: {
    id: "user-1",
    email: "admin@monika.local",
    first_name: "Dev",
    last_name: "Admin",
    is_active: true,
    is_staff: true,
    employee: {
      id: "employee-1",
      employee_code: "ME-001",
      display_name: "Development Administrator",
      company_id: "company-1",
    },
    permissions: [
      "crm.customer.view",
      "crm.customer.create",
      "crm.customer.edit",
      "crm.contact.create",
      "crm.activity.view",
      "crm.activity.create",
      "crm.activity.complete",
      "enquiry.enquiry.view",
      "enquiry.enquiry.create",
      "enquiry.enquiry.edit",
      "enquiry.enquiry.assign",
      "enquiry.enquiry.submit_engineering",
      "enquiry.enquiry.mark_lost",
      "enquiry.enquiry.cancel",
    ],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
  apiPatch: mocks.apiPatch,
}));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) =>
    Boolean(user?.permissions.includes(permission)),
}));

function renderAt(node: React.ReactNode, path = "/") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const customer = {
  id: "customer-1",
  company: "company-1",
  company_name: "Monika Engineers",
  customer_code: "CUS-0001",
  legal_name: "ABC Industries Pvt. Ltd.",
  trade_name: "ABC Industries",
  customer_type: "ORGANIZATION",
  gstin: "27ABCDE1234F1Z5",
  pan: "ABCDE1234F",
  cin: "",
  industry: "Industrial automation",
  website: "",
  primary_email: "purchase@abc.test",
  primary_phone: "+91 98765 43210",
  account_manager: "employee-1",
  account_manager_name: "Development Administrator",
  credit_limit: "500000.00",
  payment_term: null,
  default_currency: "currency-1",
  default_tax: null,
  status: "ACTIVE",
  source: "Referral",
  notes: "Priority OEM account",
  primary_contact: {
    id: "contact-1",
    customer: "customer-1",
    display_name: "Asha Rao",
    first_name: "Asha",
    last_name: "Rao",
    title: "Purchase Manager",
    department: "Purchase",
    email: "asha@abc.test",
    phone: "+91 90000 00000",
    alternate_phone: "",
    is_primary: true,
    preferred_contact_method: "EMAIL",
    notes: "",
    is_active: true,
  },
  contacts: [],
  sites: [],
  created_at: "2026-08-01T09:00:00Z",
  updated_at: "2026-08-10T09:00:00Z",
  last_activity_at: "2026-08-10T09:00:00Z",
};

describe("Phase 2 commercial CRM frontend", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
    mocks.apiPatch.mockReset();
  });

  it("renders the searchable customer register from the API", async () => {
    mocks.apiGet.mockResolvedValue({
      results: [customer],
      pagination: {
        count: 1,
        page: 1,
        page_size: 25,
        pages: 1,
        next: null,
        previous: null,
      },
    });
    renderAt(<CustomersPage />);
    expect(
      await screen.findByText("ABC Industries Pvt. Ltd."),
    ).toBeInTheDocument();
    expect(screen.getByText("CUS-0001 · ABC Industries")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New customer" }),
    ).toBeInTheDocument();
    expect(mocks.apiGet).toHaveBeenCalledWith(
      expect.stringContaining("/customers/?"),
    );
  });

  it("shows the seven required Customer 360 tabs and live account metrics", async () => {
    mocks.apiGet.mockResolvedValue({
      customer,
      overview: {
        open_follow_ups: 2,
        open_enquiries: 3,
        won_enquiries: 1,
        lost_enquiries: 0,
        last_contact: null,
        next_follow_up: null,
      },
      recent_activities: [],
      open_follow_ups: [],
      recent_enquiries: [],
      recent_documents: [],
      timeline: [
        {
          kind: "BUSINESS_CHANGE",
          occurred_at: "2026-08-10T09:00:00Z",
          summary: "Customer activated",
          actor_name: "Development Administrator",
        },
      ],
    });
    renderAt(
      <Routes>
        <Route
          path="/app/crm/customers/:customerId"
          element={<CustomerPage />}
        />
      </Routes>,
      "/app/crm/customers/customer-1",
    );
    expect(await screen.findByText("Customer 360")).toBeInTheDocument();
    for (const name of [
      "Overview",
      "Contacts",
      "Sites",
      "Enquiries",
      "Activities",
      "Documents",
      "History",
    ]) {
      expect(
        screen.getByRole("tab", { name: new RegExp(name) }),
      ).toBeInTheDocument();
    }
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New enquiry" }),
    ).toBeInTheDocument();
  });

  it("completes an open follow-up through its explicit command endpoint", async () => {
    mocks.apiGet.mockResolvedValue({
      results: [
        {
          id: "activity-1",
          company: "company-1",
          customer: "customer-1",
          customer_code: "CUS-0001",
          customer_name: "ABC Industries Pvt. Ltd.",
          enquiry: null,
          contact: null,
          contact_name: "",
          activity_type: "FOLLOW_UP",
          subject: "Confirm drawing receipt",
          description: "",
          activity_date: "2026-08-10T09:00:00Z",
          next_follow_up_at: "2026-08-11T09:00:00Z",
          follow_up_owner: "employee-1",
          follow_up_owner_name: "Development Administrator",
          priority: "HIGH",
          status: "OPEN",
          is_overdue: false,
          created_by_name: "Development Administrator",
        },
      ],
      pagination: {
        count: 1,
        page: 1,
        page_size: 25,
        pages: 1,
        next: null,
        previous: null,
      },
    });
    mocks.apiPost.mockResolvedValue({});
    const user = userEvent.setup();
    renderAt(<ActivitiesPage />);
    await user.click(
      await screen.findByRole("button", {
        name: "Complete Confirm drawing receipt",
      }),
    );
    await waitFor(() =>
      expect(mocks.apiPost).toHaveBeenCalledWith(
        "/crm-activities/activity-1/complete/",
        {},
      ),
    );
  });

  it("renders the operational enquiry register with customer and due-date context", async () => {
    mocks.apiGet.mockResolvedValue({
      results: [{ id: "enquiry-1", enquiry_number: "ENQ-0001", subject: "MCC control panel", status: "UNDER_REVIEW", customer_reference: "RFQ-431", due_date: "2026-08-20", responsible_salesperson_name: "Development Administrator", customer: "customer-1", customer_code: "CUS-0001", customer_name: "ABC Industries Pvt. Ltd.", priority: "HIGH", estimated_value: "1875000.00", currency_code: "INR", is_overdue: false, created_at: "2026-08-10T09:00:00Z", updated_at: "2026-08-10T09:00:00Z" }],
      pagination: { count: 1, page: 1, page_size: 25, pages: 1, next: null, previous: null },
    });
    renderAt(<EnquiriesPage />);
    expect(await screen.findByText("MCC control panel")).toBeInTheDocument();
    expect(screen.getByText("ABC Industries Pvt. Ltd.")).toBeInTheDocument();
    expect(screen.getByText(/INR 18,75,000/)).toBeInTheDocument();
    expect(screen.getByText("Ready for Estimation")).toBeInTheDocument();
  });

  it("uses the explicit engineering command and keeps future stages disabled", async () => {
    mocks.apiGet.mockResolvedValue({
      enquiry: { id: "enquiry-1", enquiry_number: "ENQ-0001", subject: "MCC control panel", status: "UNDER_REVIEW", customer_reference: "RFQ-431", due_date: "2026-08-20", responsible_salesperson_name: "Development Administrator", customer: "customer-1", customer_code: "CUS-0001", customer_name: "ABC Industries Pvt. Ltd.", priority: "HIGH", estimated_value: "1875000.00", currency_code: "INR", is_overdue: false, created_at: "2026-08-10T09:00:00Z", updated_at: "2026-08-10T09:00:00Z", company: "company-1", company_name: "Monika Engineers", customer_contact: null, customer_contact_name: "", customer_site: null, customer_site_name: "", source: "Email", received_date: "2026-08-10", description: "Panel design and manufacture", responsible_salesperson: "employee-1", currency: "currency-1", lost_reason: "", cancellation_reason: "", competitor: "", customer_feedback: "", closed_at: null, requirements: [], items: [] },
      next_follow_up: null, activities: [], documents: [], timeline: [], engineering_review: null,
    });
    mocks.apiPost.mockResolvedValue({});
    const user = userEvent.setup();
    renderAt(<Routes><Route path="/app/crm/enquiries/:enquiryId" element={<EnquiryPage />} /></Routes>, "/app/crm/enquiries/enquiry-1");
    await user.click(await screen.findByRole("button", { name: "Send to engineering" }));
    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/enquiries/enquiry-1/send-to-engineering/", {}));
    expect(screen.getByText("Estimation · not built")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Estimation/ })).not.toBeInTheDocument();
  });
});
