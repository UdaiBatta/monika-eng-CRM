import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/production/lib/api";
import type { CurrentUser } from "@/production/lib/types";
import QuotationPage from "./quotation-page";
import QuotationsPage from "./quotations-page";

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
    employee: { id: "employee-1", employee_code: "ME-001", display_name: "Development Administrator", company_id: "company-1" },
    permissions: ["crm.quotation.view", "crm.quotation.create", "crm.quotation.quick_create", "crm.quotation.change", "crm.quotation.finalize", "crm.quotation.send", "crm.quotation.negotiate", "crm.quotation.confirm", "crm.quotation.ready_for_sales_order", "crm.quotation.generate_document"],
    features: ["quick_quotation"],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
}));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
  hasFeature: (user: CurrentUser | undefined, feature: string) => Boolean(user?.features?.includes(feature)),
}));
vi.mock("@/production/lib/realtime", () => ({ useRealtimeEntity: () => [] }));

const pagination = { count: 1, page: 1, page_size: 25, pages: 1, next: null, previous: null };
const revision = {
  id: "revision-1",
  revision_number: 1,
  record_version: 3,
  status: "DRAFT",
  currency: "currency-1",
  currency_code: "INR",
  issue_date: "2026-08-11",
  valid_until: "2026-09-10",
  introduction: "Thank you for the opportunity.",
  scope: "MCC control panel",
  inclusions: "Panel assembly",
  exclusions: "Site cabling",
  assumptions: "Approved drawings",
  payment_terms: "30% advance",
  delivery_terms: "8 weeks",
  warranty_terms: "12 months",
  freight_terms: "Extra",
  customer_notes: "",
  subtotal: "250000.00",
  discount_amount: "0.00",
  taxable_amount: "250000.00",
  tax_amount: "45000.00",
  grand_total: "295000.00",
  frozen_at: null,
  frozen_reason: "",
  approval_request: null,
  sent_at: null,
  lines: [{ id: "line-1", line_number: 1, item_code: "MCC-01", description: "MCC control panel", quantity: "1.0000", unit_of_measure: "LOT", unit_price: "250000.0000", discount_percent: "0.0000", tax_percent: "18.0000", line_subtotal: "250000.00", discount_amount: "0.00", taxable_amount: "250000.00", tax_amount: "45000.00", total_amount: "295000.00", is_optional: false, notes: "" }],
  communications: [],
  negotiations: [],
  generated_documents: [],
};
const quotation = {
  id: "quotation-1",
  company: "company-1",
  quotation_number: "QUO-2026-0001",
  customer: "customer-1",
  customer_name: "ABC Industries Pvt. Ltd.",
  customer_code: "CUST-0001",
  customer_contact: null,
  enquiry: "enquiry-1",
  enquiry_number: "ENQ-2026-0001",
  estimate: "estimate-1",
  estimate_number: "EST-2026-0001",
  path: "STANDARD",
  path_label: "Standard quotation",
  quick_reason: "",
  status: "DRAFT",
  status_label: "Draft",
  owner: "employee-1",
  owner_name: "Development Administrator",
  current_revision: revision,
  commercial_confirmation: null,
  created_at: "2026-08-11T09:00:00Z",
  updated_at: "2026-08-11T10:00:00Z",
};
const approvedEstimate = {
  id: "estimate-1",
  customer_id: "customer-1",
  customer_name: "ABC Industries Pvt. Ltd.",
  enquiry: "enquiry-1",
  enquiry_number: "ENQ-2026-0001",
  estimate_number: "EST-2026-0001",
  proposed_selling_price: "250000.00",
  currency_code: "INR",
};

function renderAt(node: React.ReactNode, path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{node}</MemoryRouter></QueryClientProvider>);
}

describe("quotation frontend", () => {
  afterEach(() => cleanup());
  beforeEach(() => { mocks.apiGet.mockReset(); mocks.apiPost.mockReset(); mocks.user.features = ["quick_quotation"]; });

  it("renders the Axis register and creates a standard quotation from an approved estimate", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/quotations/?")) return Promise.resolve({ results: [quotation], pagination });
      if (path.startsWith("/commercial-estimates/")) return Promise.resolve({ results: [approvedEstimate], pagination });
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPost.mockResolvedValue(quotation);
    const user = userEvent.setup();
    renderAt(<QuotationsPage />, "/app/crm/quotations");

    expect((await screen.findAllByText("QUO-2026-0001")).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "New quotation" }));
    await user.selectOptions(await screen.findByLabelText("Approved current estimate"), "estimate-1");
    await user.click(screen.getByRole("button", { name: "Create draft" }));

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/quotations/", { path: "STANDARD", customer_id: "customer-1", enquiry_id: "enquiry-1", estimate_id: "estimate-1" }));
  });

  it("allows a prospect customer through the permission-gated quick path", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/customers/")) return Promise.resolve({ results: [{ id: "customer-1", customer_code: "CUST-0001", legal_name: "ABC Industries Pvt. Ltd.", status: "PROSPECT" }], pagination });
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPost.mockResolvedValue({ ...quotation, path: "QUICK", estimate: null, enquiry: null });
    const user = userEvent.setup();
    renderAt(<QuotationsPage />, "/app/crm/quotations");

    await user.click(await screen.findByRole("button", { name: "New quotation" }));
    await user.click(screen.getByRole("button", { name: /Quick Direct commercial offer/ }));
    await user.selectOptions(await screen.findByLabelText("Customer"), "customer-1");
    await user.type(screen.getByLabelText("Why is the quick path appropriate?"), "Standard replacement item with agreed pricing.");
    await user.type(screen.getByLabelText("Offer description"), "Replacement contactor");
    await user.clear(screen.getByLabelText("Unit price"));
    await user.type(screen.getByLabelText("Unit price"), "15000");
    await user.click(screen.getByRole("button", { name: "Create draft" }));

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/quotations/", expect.objectContaining({ path: "QUICK", customer_id: "customer-1", quick_reason: "Standard replacement item with agreed pricing." })));
  });

  it("honours the Owner feature control even when the user has quick-quotation permission", async () => {
    mocks.user.features = [];
    mocks.apiGet.mockResolvedValue({ results: [], pagination: { ...pagination, count: 0 } });
    const user = userEvent.setup();
    renderAt(<QuotationsPage />, "/app/crm/quotations");

    await user.click(await screen.findByRole("button", { name: "New quotation" }));

    expect(screen.getByRole("button", { name: /Quick Disabled by the Owner/ })).toBeDisabled();
    expect(screen.getByText("Disabled by the Owner; use an approved estimate.")).toBeInTheDocument();
  });

  it("saves a versioned quotation draft through the focused builder", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path === "/quotations/quotation-1/") return Promise.resolve(quotation);
      if (path.endsWith("/compare/")) return Promise.resolve([]);
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPost.mockResolvedValue(revision);
    const user = userEvent.setup();
    renderAt(<Routes><Route path="/app/crm/quotations/:quotationId" element={<QuotationPage />} /></Routes>, "/app/crm/quotations/quotation-1");

    await screen.findByText("QUO-2026-0001");
    const scope = screen.getByLabelText("Scope");
    await user.clear(scope);
    await user.type(scope, "Revised MCC panel scope");
    await user.click(screen.getByRole("button", { name: "Save version 3" }));

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/quotation-revisions/revision-1/update-draft/", expect.objectContaining({ record_version: 3, scope: "Revised MCC panel scope" })));
  });

  it("shows a friendly refresh action on an optimistic-lock conflict", async () => {
    mocks.apiGet.mockImplementation((path: string) => path.endsWith("/compare/") ? Promise.resolve([]) : Promise.resolve(quotation));
    mocks.apiPost.mockRejectedValue(new ApiError(409, "This record was changed by another user."));
    const user = userEvent.setup();
    renderAt(<Routes><Route path="/app/crm/quotations/:quotationId" element={<QuotationPage />} /></Routes>, "/app/crm/quotations/quotation-1");

    await user.click(await screen.findByRole("button", { name: "Save version 3" }));
    expect(await screen.findByText("A newer version is available")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load latest version" })).toBeInTheDocument();
  });
});
