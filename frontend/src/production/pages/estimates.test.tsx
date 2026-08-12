import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import EstimatePage from "./estimate-page";
import EstimatesPage from "./estimates-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
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
      "estimation.estimate.view",
      "estimation.estimate.view_cost",
      "estimation.estimate.view_margin",
      "estimation.estimate.create",
      "estimation.estimate.edit",
      "estimation.estimate.submit",
      "estimation.estimate.revise",
    ],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
  apiPatch: mocks.apiPatch,
  apiDelete: mocks.apiDelete,
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

const line = {
  id: "line-1",
  estimate: "estimate-1",
  line_number: 1,
  category: "MATERIAL",
  description: "Switchgear and enclosure",
  quantity: "2.0000",
  unit_of_measure: "LOT",
  unit_cost: "100000.0000",
  amount: "200000.00",
  source_reference: "Vendor RFQ 101",
  notes: "",
  is_optional: false,
};

const estimate = {
  id: "estimate-1",
  company: "company-1",
  enquiry: "enquiry-1",
  enquiry_number: "ENQ-2026-0001",
  enquiry_subject: "MCC control panel RFQ",
  customer_id: "customer-1",
  customer_code: "CUST-00001",
  customer_name: "ABC Industries Pvt. Ltd.",
  sales_owner_name: "Development Administrator",
  engineering_review: "review-1",
  engineering_review_revision: 1,
  estimate_number: "EST-2026-0001",
  revision_number: 1,
  is_current: true,
  status: "IN_PREPARATION",
  currency: "currency-1",
  currency_code: "INR",
  currency_symbol: "₹",
  pricing_method: "MARKUP",
  markup_percent: "20.0000",
  target_margin_percent: "0.0000",
  manual_selling_price: null,
  total_cost: "200000.00",
  proposed_selling_price: "240000.00",
  gross_margin_amount: "40000.00",
  gross_margin_percent: "16.6667",
  category_totals: { MATERIAL: "200000.00" },
  assumptions: "Customer supplies approved GA.",
  exclusions: "Site cabling excluded.",
  commercial_notes: "",
  technical_reference_summary: "Feasible standard MCC architecture.",
  prepared_by_name: "Development Administrator",
  submitted_at: null,
  submitted_by_name: "",
  approved_at: null,
  approved_by_name: "",
  approval_request: null,
  approval_status: "",
  supersedes: null,
  cost_lines: [line],
  created_at: "2026-08-11T09:00:00Z",
  updated_at: "2026-08-11T10:00:00Z",
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

describe("commercial estimation frontend", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
    mocks.apiPatch.mockReset();
    mocks.apiDelete.mockReset();
  });

  it("renders the controlled estimate register", async () => {
    mocks.apiGet.mockResolvedValue({ results: [estimate], pagination });
    renderAt(<EstimatesPage />, "/app/crm/estimates");

    expect((await screen.findAllByText("EST-2026-0001")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("ABC Industries Pvt. Ltd.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("INR 2,40,000").length).toBeGreaterThan(0);
  });

  it("adds a server-calculated cost line from the Axis workspace", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path.endsWith("/workspace/")) {
        return Promise.resolve({ estimate, enquiry: {}, approvals: [], documents: [], timeline: [] });
      }
      if (path.endsWith("/revisions/")) return Promise.resolve([estimate]);
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPost.mockResolvedValue(line);
    const user = userEvent.setup();
    renderAt(
      <Routes><Route path="/app/crm/estimates/:estimateId" element={<EstimatePage />} /></Routes>,
      "/app/crm/estimates/estimate-1",
    );

    await user.click(await screen.findByRole("button", { name: "Add cost line" }));
    await user.type(screen.getByLabelText("Description"), "Assembly labour");
    await user.type(screen.getByLabelText("Unit cost (INR)"), "1250");
    await user.click(screen.getByRole("button", { name: "Save cost line" }));

    await waitFor(() =>
      expect(mocks.apiPost).toHaveBeenCalledWith(
        "/estimate-cost-lines/",
        expect.objectContaining({
          estimate_id: "estimate-1",
          category: "MATERIAL",
          description: "Assembly labour",
          unit_cost: "1250",
        }),
      ),
    );
  });

  it("saves controlled pricing through the estimate details command", async () => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path.endsWith("/workspace/")) {
        return Promise.resolve({ estimate, enquiry: {}, approvals: [], documents: [], timeline: [] });
      }
      if (path.endsWith("/revisions/")) return Promise.resolve([estimate]);
      return Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } });
    });
    mocks.apiPatch.mockResolvedValue(estimate);
    const user = userEvent.setup();
    renderAt(
      <Routes><Route path="/app/crm/estimates/:estimateId" element={<EstimatePage />} /></Routes>,
      "/app/crm/estimates/estimate-1",
    );

    await user.click(await screen.findByRole("tab", { name: "Pricing & basis" }));
    await user.clear(screen.getByLabelText("Markup %"));
    await user.type(screen.getByLabelText("Markup %"), "25");
    await user.click(screen.getByRole("button", { name: "Save & recalculate" }));

    await waitFor(() =>
      expect(mocks.apiPatch).toHaveBeenCalledWith(
        "/commercial-estimates/estimate-1/details/",
        expect.objectContaining({ pricing_method: "MARKUP", markup_percent: "25" }),
      ),
    );
  });
});
