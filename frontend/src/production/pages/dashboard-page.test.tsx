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
    permissions: ["crm.external_enquiry.review", "crm.quotation.view"],
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
});
