import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import CustomerPOsPage from "./customer-pos-page";
import ProjectPage from "./project-page";
import SalesOrdersPage from "./sales-orders-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  user: {
    id: "user-1",
    email: "sales@monika.local",
    first_name: "Sales",
    last_name: "Employee",
    is_active: true,
    is_staff: false,
    employee: { id: "employee-1", employee_code: "ME-SALES-01", display_name: "Sales Employee", company_id: "company-1" },
    permissions: ["sales.customer_po.view", "sales.customer_po.create", "sales.sales_order.view", "sales.sales_order.create", "sales.sales_order.direct_create", "projects.project.view", "projects.handoff.view", "projects.handoff.take_ownership", "projects.handoff.accept"],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({ ...(await importOriginal<typeof import("@/production/lib/api")>()), apiGet: mocks.apiGet, apiPost: mocks.apiPost }));
vi.mock("@/production/lib/auth", () => ({ useCurrentUser: () => ({ data: mocks.user }), hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)) }));
vi.mock("@/production/lib/realtime", () => ({ useRealtimeEntity: () => [] }));

const pagination = { count: 1, page: 1, page_size: 50, pages: 1, next: null, previous: null };
const orderRevision = { id: "revision-1", revision_number: 0, record_version: 1, status: "RELEASED", status_label: "Released", currency_code: "INR", order_date: "2026-08-19", requested_delivery: null, promised_delivery: null, payment_terms: "30% advance", delivery_terms: "8 weeks", warranty_terms: "12 months", freight_terms: "Extra", installation_terms: "Included", scope: "MCC panel", exclusions: "", customer_notes: "", subtotal: "100000.00", discount_amount: "0.00", tax_amount: "18000.00", grand_total: "118000.00", approval_request: null, revision_reason: "", released_at: "2026-08-19T10:00:00Z", created_at: "2026-08-19T09:00:00Z", updated_at: "2026-08-19T10:00:00Z", lines: [{ id: "line-1", line_number: 1, description: "MCC control panel", quantity: "1.0000", unit_of_measure: "NOS", unit_price: "100000.0000", discount_percent: "0.0000", tax_percent: "18.0000", line_subtotal: "100000.00", discount_amount: "0.00", taxable_amount: "100000.00", tax_amount: "18000.00", total_amount: "118000.00", delivery_text: "", customer_visible_note: "" }] };
const order = { id: "order-1", company: "company-1", financial_year: "2026-27", sales_order_number: "SO-2026-0001", customer: "customer-1", customer_name: "ABC Industries", contact_name: "", site_name: "", accepted_quotation: "quotation-1", quotation_number: "QTN-2026-0001", customer_purchase_order: null, customer_po_number: "", order_mode: "QUOTATION_BASED", order_mode_label: "Quotation based", responsible_name: "Sales Employee", project_required: true, po_pending: true, direct_reason: "", status: "RELEASED", status_label: "Released for Execution", project_id: "project-1", project_number: "PRJ-2026-0001", current_revision: orderRevision, revisions: [orderRevision], created_at: "2026-08-19T09:00:00Z", updated_at: "2026-08-19T10:00:00Z" };
const handoff = { id: "handoff-1", record_version: 1, project_scope_summary: "Supply one MCC panel", technical_requirement_summary: "415V MCC", customer_specifications: "", special_commercial_commitments: "", technical_assumptions: "", open_questions: "", sales_notes: "", assigned_engineer: null, assigned_engineer_name: "", status: "READY_FOR_ENGINEERING", status_label: "Ready for Engineering", submitted_at: "2026-08-19T10:00:00Z", accepted_at: null, clarifications: [] };
const project = { id: "project-1", company: "company-1", project_number: "PRJ-2026-0001", project_name: "ABC Industries — MCC panel", customer_name: "ABC Industries", contact_name: "", site_name: "", customer_project_reference: "", customer_po_reference: "", sales_owner_name: "Sales Employee", project_owner_name: "", engineering_owner_name: "", status: "HANDOFF_PENDING", status_label: "Waiting for Engineering", priority: "NORMAL", priority_label: "Normal", target_completion: null, customer_delivery_commitment: "8 weeks", commercial_change_pending: false, current_commercial_baseline: "SO-2026-0001 Rev 0", previous_commercial_baseline: "", next_action: "Engineering must take ownership and review.", open_clarification_count: 0, record_version: 1, sales_order_detail: order, customer_po_detail: null, engineering_handoff: handoff, documents: [], activity: [], created_at: "2026-08-19T10:00:00Z", updated_at: "2026-08-19T10:00:00Z" };

function renderAt(node: React.ReactNode, path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{node}</MemoryRouter></QueryClientProvider>);
}

describe("Phase 3 sales and project frontend", () => {
  afterEach(() => cleanup());
  beforeEach(() => { mocks.apiGet.mockReset(); mocks.apiPost.mockReset(); });

  it("shows the customer PO register and plain-language entry action", async () => {
    mocks.apiGet.mockResolvedValue({ results: [], pagination: { ...pagination, count: 0 } });
    renderAt(<CustomerPOsPage />, "/app/sales/customer-pos");
    expect(await screen.findByRole("heading", { name: "Customer purchase orders" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record Customer PO" })).toBeInTheDocument();
    expect(screen.getByText("PO can arrive later")).toBeInTheDocument();
  });

  it("creates a quotation-based order from the focused register", async () => {
    mocks.apiGet.mockImplementation((path: string) => path.startsWith("/quotations/") ? Promise.resolve({ results: [{ id: "quotation-1", quotation_number: "QTN-2026-0001", customer_name: "ABC Industries", current_revision: { grand_total: "118000.00", currency_code: "INR" } }], pagination }) : Promise.resolve({ results: [], pagination: { ...pagination, count: 0 } }));
    mocks.apiPost.mockResolvedValue(order);
    const user = userEvent.setup();
    renderAt(<SalesOrdersPage />, "/app/sales/orders");
    await user.click(await screen.findByRole("button", { name: "Create Sales Order" }));
    await user.selectOptions(await screen.findByLabelText("Ready quotation"), "quotation-1");
    await user.click(screen.getByRole("button", { name: "Create draft" }));
    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/sales/orders/from-quotation/", { quotation_id: "quotation-1", project_required: true }));
  });

  it("lets Engineering take an unassigned handoff with one clear action", async () => {
    mocks.apiGet.mockImplementation((path: string) => path === "/projects/project-1/" ? Promise.resolve(project) : Promise.resolve({ results: [], pagination }));
    mocks.apiPost.mockResolvedValue({ ...handoff, status: "ENGINEERING_REVIEWING" });
    const user = userEvent.setup();
    renderAt(<Routes><Route path="/app/projects/:projectId" element={<ProjectPage />} /></Routes>, "/app/projects/project-1");
    await user.click(await screen.findByRole("button", { name: "Take This" }));
    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/projects/project-1/take-ownership/", undefined));
  });
});
