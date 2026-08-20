import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import MyWorkPage from "./my-work-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  user: {
    first_name: "Neha",
    employee: { display_name: "Neha Kulkarni" },
    permissions: ["crm.quotation.view"],
  },
}));

vi.mock("@/production/lib/api", () => ({ apiGet: mocks.apiGet }));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: typeof mocks.user | undefined, permission: string) =>
    Boolean(user?.permissions.includes(permission)),
}));

describe("My Work", () => {
  afterEach(() => {
    cleanup();
    mocks.apiGet.mockReset();
  });

  it("loads only permitted real work and keeps urgent work out of the ordinary list", async () => {
    mocks.apiGet.mockResolvedValue({
      results: [
        {
          id: "quote-1",
          quotation_number: "QT-2026-0042",
          customer_name: "ABC Industries",
          status: "DRAFT",
          status_label: "Draft",
          current_revision: { valid_until: "2026-08-19" },
        },
      ],
      pagination: { count: 1 },
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter><MyWorkPage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Needs Attention")).toBeInTheDocument();
    expect(screen.getByText("QT-2026-0042")).toBeInTheDocument();
    expect(screen.getByText("Everything open needs attention")).toBeInTheDocument();
    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalledTimes(1));
    expect(mocks.apiGet).toHaveBeenCalledWith(expect.stringContaining("/quotations/?queue=mine"));
  });
});
