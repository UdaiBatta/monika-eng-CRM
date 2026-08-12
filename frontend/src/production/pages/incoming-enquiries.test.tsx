import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import IncomingEnquiriesPage from "./incoming-enquiries-page";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiUpload: vi.fn(),
  user: {
    id: "user-1",
    email: "admin@monika.local",
    first_name: "Development",
    last_name: "Administrator",
    is_active: true,
    is_staff: true,
    employee: { id: "employee-1", employee_code: "ME-001", display_name: "Development Administrator", company_id: "company-1" },
    permissions: ["crm.external_enquiry.review"],
  } as CurrentUser,
}));

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
  apiUpload: mocks.apiUpload,
}));
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
}));

describe("incoming enquiry queues and history import", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
    mocks.apiUpload.mockReset();
    mocks.apiGet.mockResolvedValue({ results: [], pagination: { count: 0, page: 1, page_size: 25, pages: 1, next: null, previous: null } });
  });

  it("loads the dashboard-selected queue and uploads a CSV import", async () => {
    mocks.apiUpload.mockResolvedValue({ imported: 1, possible_duplicates: 0 });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const user = userEvent.setup();
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/app/crm/incoming-enquiries?queue=unassigned"]}><IncomingEnquiriesPage /></MemoryRouter></QueryClientProvider>);

    expect(await screen.findByRole("combobox", { name: "Ownership queue" })).toHaveValue("unassigned");
    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalledWith(expect.stringContaining("queue=unassigned")));
    await user.click(screen.getByRole("button", { name: "Import Excel / CSV" }));
    const file = new File(["received_at,channel,person_name,subject,message\n2025-01-01,PHONE,Ravi,Old enquiry,Call back"], "history.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("CSV or Excel file"), file);
    await user.click(screen.getByRole("button", { name: "Import data" }));

    await waitFor(() => expect(mocks.apiUpload).toHaveBeenCalledWith("/external-enquiries/import-history/", expect.any(FormData)));
    expect(screen.queryByRole("dialog", { name: "Import previous enquiries" })).not.toBeInTheDocument();
  });
});
