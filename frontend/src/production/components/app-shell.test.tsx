import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import AppShell from "./app-shell";

const user = {
  id: "user-1",
  email: "admin@monika.local",
  first_name: "Development",
  last_name: "Administrator",
  is_active: true,
  is_staff: true,
  employee: { id: "employee-1", employee_code: "ME-001", display_name: "Development Administrator", company_id: "company-1" },
  permissions: [
    "crm.quotation.view",
    "organization.warehouse.view",
    "configuration.settings.view",
  ],
} as CurrentUser;

vi.mock("@/production/lib/auth", () => ({
  currentUserQueryKey: ["current-user"],
  useCurrentUser: () => ({ data: user }),
  hasPermission: (currentUser: CurrentUser | undefined, permission: string) => Boolean(currentUser?.permissions.includes(permission)),
}));
vi.mock("@/production/lib/realtime", () => ({
  RealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
  useRealtime: () => ({ status: "live" }),
}));
vi.mock("@/production/components/notification-center", () => ({ default: () => null }));

describe("mobile application navigation", () => {
  afterEach(() => cleanup());

  it("closes after opening the quotations register", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const actor = userEvent.setup();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/app"]}>
          <Routes>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<p>Workspace opened</p>} />
              <Route path="crm/quotations" element={<p>Quotation register opened</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await actor.click(screen.getByRole("button", { name: "Open navigation" }));
    await actor.click(screen.getByRole("link", { name: "Quotations" }));

    expect(await screen.findByText("Quotation register opened")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Application navigation" })).not.toBeInTheDocument());
  });

  it("keeps advanced administration out of the daily sidebar", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/app"]}>
          <Routes>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<p>Workspace opened</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Quotations" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Inventory & workshop" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tools & settings" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Numbering" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Roles" })).not.toBeInTheDocument();
  });
});
