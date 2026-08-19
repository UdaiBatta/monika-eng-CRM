import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { CurrentUser } from "@/production/lib/types"
import OwnerAccessPage from "./owner-access-page"
import OwnerFeaturesPage from "./owner-features-page"
import OwnerWorkPage from "./owner-work-page"

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  user: {
    id: "owner-1",
    email: "owner@monika.local",
    first_name: "Business",
    last_name: "Owner",
    is_active: true,
    is_staff: false,
    employee: { id: "employee-owner", employee_code: "ME-001", display_name: "Business Owner", company_id: "company-1" },
    permissions: ["system.owner_control.view", "system.work.reassign", "system.access_explanation.view", "configuration.feature_flag.view", "configuration.feature_flag.manage"],
  } as CurrentUser,
}))

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
}))
vi.mock("@/production/lib/auth", () => ({
  currentUserQueryKey: ["auth", "me"],
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
}))

const pagination = { count: 1, page: 1, page_size: 25, pages: 1, next: null, previous: null }

function renderOwner(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>)
}

describe("Owner Control Centre", () => {
  afterEach(() => cleanup())
  beforeEach(() => { mocks.apiGet.mockReset(); mocks.apiPost.mockReset() })

  it("requires a reason and record version before changing an implemented feature", async () => {
    const features = [
      { key: "quick_quotation", name: "Quick quotation", description: "Direct offer path", implemented: true, status: "Enabled", is_enabled: true, record_version: 4, action_url: "/app/crm/quotations" },
      { key: "inventory_transactions", name: "Inventory transactions", description: "Stock ledger", implemented: false, status: "Not available yet", is_enabled: false, record_version: null, action_url: "" },
    ]
    mocks.apiGet.mockResolvedValue({ features })
    mocks.apiPost.mockResolvedValue({ features: [{ ...features[0], status: "Disabled", is_enabled: false, record_version: 5 }, features[1]] })
    const actor = userEvent.setup()
    renderOwner(<OwnerFeaturesPage />)

    await actor.click(await screen.findByRole("switch", { name: "Disable Quick quotation" }))
    expect(screen.getByRole("dialog", { name: "Disable Quick quotation" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Confirm change" })).toBeDisabled()
    await actor.type(screen.getByLabelText("Why is this changing?"), "Use approved estimates during pricing review")
    await actor.click(screen.getByRole("button", { name: "Confirm change" }))

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/owner/change-feature/", {
      key: "quick_quotation", is_enabled: false, reason: "Use approved estimates during pricing review", record_version: 4,
    }))
    expect(screen.getByText("Not available yet")).toBeInTheDocument()
  })

  it("explains a denied action in business language", async () => {
    mocks.apiGet.mockImplementation((path: string) => path.startsWith("/users/")
      ? Promise.resolve({ results: [{ id: "sales-1", email: "sales@monika.local", first_name: "Sales" }], pagination })
      : Promise.resolve({ results: [{ id: "permission-1", code: "crm.quotation.confirm", name: "Confirm quotation" }], pagination }))
    mocks.apiPost.mockResolvedValue({
      allowed: false,
      permission: "crm.quotation.confirm",
      permission_name: "Confirm quotation",
      reason: "Denied by a direct Deny override. Deny takes priority.",
      scope: { company_id: "company-1" },
      roles: [{ name: "Sales", scope: "Company" }],
      overrides: [{ effect: "DENY", scope: "Company", reason: "Approval separation" }],
    })
    const actor = userEvent.setup()
    renderOwner(<OwnerAccessPage />)

    await screen.findByRole("option", { name: "sales@monika.local · Sales" })
    await actor.selectOptions(screen.getByLabelText("Whose access?"), "sales-1")
    await actor.selectOptions(screen.getByLabelText("Which action?"), "crm.quotation.confirm")
    await actor.click(screen.getByRole("button", { name: "Explain access" }))

    expect(await screen.findByText("Denied by a direct Deny override. Deny takes priority.")).toBeInTheDocument()
    expect(screen.getByText("Approval separation")).toBeInTheDocument()
  })

  it("reassigns selected work only after an active employee and reason are supplied", async () => {
    const work = { work_type: "incoming_enquiry", work_type_label: "Incoming enquiry", id: "work-1", reference: "WEB-001", title: "Panel enquiry", status: "New", status_code: "NEW", assigned_to: null, assigned_to_name: "Unassigned", updated_at: "2026-08-19T10:00:00Z", action_url: "/app/crm/incoming-enquiries/work-1" }
    mocks.apiGet.mockImplementation((path: string) => path.startsWith("/owner/work-items/")
      ? Promise.resolve({ results: [work], pagination })
      : Promise.resolve([{ id: "employee-2", employee_code: "ME-002", display_name: "Sales Person" }]))
    mocks.apiPost.mockResolvedValue({ reassigned: 1 })
    const actor = userEvent.setup()
    renderOwner(<OwnerWorkPage />)

    await actor.click(await screen.findByRole("checkbox", { name: "Select WEB-001" }))
    await actor.click(screen.getByRole("button", { name: "Reassign selected (1)" }))
    await actor.selectOptions(screen.getByLabelText("New responsible employee"), "employee-2")
    await actor.type(screen.getByLabelText("Why is this work moving?"), "Covering planned leave")
    await actor.click(screen.getByRole("button", { name: "Confirm reassignment" }))

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/owner/reassign-work/", {
      items: [{ work_type: "incoming_enquiry", id: "work-1" }],
      employee_id: "employee-2",
      reason: "Covering planned leave",
    }))
  })
})
