import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppShell from "./app-shell";

const mocks = vi.hoisted(() => ({
  permissions: [] as string[],
}));

vi.mock("@/production/lib/auth", () => ({
  currentUserQueryKey: ["current-user"],
  useCurrentUser: () => ({ data: { first_name: "Test", permissions: mocks.permissions } }),
  hasPermission: (user: { permissions: string[] } | undefined, permission: string) =>
    Boolean(user?.permissions.includes(permission)),
}));
vi.mock("@/production/lib/realtime", () => ({
  RealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
  useRealtime: () => ({ status: "live" }),
}));
vi.mock("@/production/components/notification-center", () => ({ default: () => null }));

function renderShell(permissions: string[]) {
  mocks.permissions = permissions;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/app"]}>
        <Routes><Route path="/app" element={<AppShell />}><Route index element={<p>Work</p>} /></Route></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("responsibility-based navigation", () => {
  afterEach(cleanup);

  it("keeps Sales focused on customers and commercial work", () => {
    renderShell(["enquiry.enquiry.view", "crm.customer.view", "crm.quotation.view", "crm.activity.view", "documents.document.view"]);
    expect(screen.getByRole("link", { name: "Enquiries" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Customers" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Quotations & Orders" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "My Workshop Work" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Owner Centre" })).not.toBeInTheDocument();
  });

  it("keeps Workshop focused on practical review and projects", () => {
    renderShell(["engineering.feasibility.view", "projects.project.view", "documents.document.view"]);
    expect(screen.getByRole("link", { name: "My Workshop Work" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Projects" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Documents" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Quotations & Orders" })).not.toBeInTheDocument();
  });

  it("gives the Owner an administrative entry point", () => {
    renderShell(["system.owner_control.view", "approvals.request.view", "rbac.role.view"]);
    expect(screen.getByRole("link", { name: "Owner Centre" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Approvals" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tools & settings" })).toBeInTheDocument();
  });
});
