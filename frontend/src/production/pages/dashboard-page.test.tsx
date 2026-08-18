import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import DashboardPage from "./dashboard-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  user: {
    id: "user-1",
    email: "admin@monika.local",
    first_name: "Development",
    last_name: "Administrator",
    is_active: true,
    is_staff: true,
    employee: { id: "employee-1", employee_code: "ME-001", display_name: "Development Administrator", company_id: "company-1" },
    roles: [{ name: "Sales", scope: "Company" }],
    permissions: [
      "crm.external_enquiry.review",
      "crm.customer.view",
      "crm.customer.edit",
      "crm.activity.edit",
      "enquiry.enquiry.view",
      "enquiry.enquiry.edit",
      "crm.quotation.view",
      "crm.quotation.change",
      "sales.customer_po.view",
      "sales.customer_po.create",
      "sales.sales_order.view",
      "sales.sales_order.submit",
      "projects.project.view",
      "projects.handoff.view",
      "projects.handoff.submit",
    ],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", () => ({ apiGet: mocks.apiGet }));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
}));

describe("dashboard work queue links", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.apiGet.mockImplementation((path: string) => path === "/health/"
      ? Promise.resolve({ status: "ok", database: "ok", cache: "ok" })
      : Promise.resolve({ results: [], pagination: { count: 0, page: 1, page_size: 1, pages: 1, next: null, previous: null } }));
  });

  it("opens the intended filtered register for each personal queue", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><DashboardPage /></MemoryRouter></QueryClientProvider>);

    const unassignedCard = (await screen.findByText("Unassigned enquiries")).closest('[data-slot="card"]');
    const mineCard = screen.getByText("My enquiries").closest('[data-slot="card"]');
    const quotationsCard = screen.getByText("My quotations").closest('[data-slot="card"]');
    expect((await within(unassignedCard as HTMLElement).findByRole("button", { name: "Open register" })).closest("a")).toHaveAttribute("href", "/app/crm/incoming-enquiries?queue=unassigned");
    expect((await within(mineCard as HTMLElement).findByRole("button", { name: "Open register" })).closest("a")).toHaveAttribute("href", "/app/crm/incoming-enquiries?queue=mine");
    expect((await within(quotationsCard as HTMLElement).findByRole("button", { name: "Open register" })).closest("a")).toHaveAttribute("href", "/app/crm/quotations?queue=mine");
  });

  it("shows sales work without administrator or engineering panels", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><DashboardPage /></MemoryRouter></QueryClientProvider>);

    expect(await screen.findByText("Sales workspace")).toBeInTheDocument();
    expect(screen.getByText("Review and claim enquiries")).toBeInTheDocument();
    expect(screen.queryByText("Foundation readiness")).not.toBeInTheDocument();
    expect(screen.queryByText("Django API")).not.toBeInTheDocument();
    expect(screen.queryByText("Engineering canvas")).not.toBeInTheDocument();
    expect(screen.queryByText("Unassigned Engineering")).not.toBeInTheDocument();
    expect(screen.queryByText("My Engineering work")).not.toBeInTheDocument();
    expect(screen.queryByText("Access posture")).not.toBeInTheDocument();
    expect(screen.getByText("Your daily sales flow")).toBeInTheDocument();
    expect(screen.getByText("Your access")).toBeInTheDocument();
    expect(screen.getByText("Manager-controlled actions")).toBeInTheDocument();
    expect(screen.getByText(/Approval, release, cancellation/)).toBeInTheDocument();
  });
});
