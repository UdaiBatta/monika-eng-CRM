import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { CurrentUser } from "@/production/lib/types"
import { resourceConfigs } from "@/production/lib/resource-config"
import ResourcePage, { ResourceRecordForm } from "./resource-page"

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
    permissions: ["organization.company.manage"],
  } as CurrentUser,
}))

vi.mock("@/production/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/production/lib/api")>()),
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
  apiUpload: mocks.apiUpload,
}))
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
}))

const pagination = (page = 1, pages = 1) => ({
  count: pages,
  page,
  page_size: 100,
  pages,
  next: page < pages ? "next" : null,
  previous: page > 1 ? "previous" : null,
})

describe("role permission editor", () => {
  afterEach(() => cleanup())
  beforeEach(() => {
    mocks.apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/companies/")) {
        return Promise.resolve({ results: [{ id: "company-1", code: "MEDEV", name: "Monika Engineers" }], pagination: pagination() })
      }
      if (path.startsWith("/permissions/") && path.includes("page=2")) {
        return Promise.resolve({ results: [{ id: "permission-2", code: "crm.customer.create", name: "Create customers" }], pagination: pagination(2, 2) })
      }
      if (path.startsWith("/permissions/")) {
        return Promise.resolve({ results: [{ id: "permission-1", code: "crm.customer.view", name: "View customers" }], pagination: pagination(1, 2) })
      }
      return Promise.resolve({ results: [], pagination: pagination() })
    })
    mocks.apiPost.mockResolvedValue({ id: "role-1", code: "SALES", name: "Sales" })
  })

  it("loads every permission page and submits section selections", async () => {
    const actor = userEvent.setup()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <ResourceRecordForm config={resourceConfigs.roles} onSuccess={vi.fn()} />
      </QueryClientProvider>,
    )

    await actor.click(await screen.findByRole("checkbox", { name: "Select all Customers" }))
    expect(screen.getByRole("checkbox", { name: "View customers" })).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "Create customers" })).toBeChecked()
    expect(mocks.apiGet).toHaveBeenCalledWith(expect.stringContaining("page=2"))

    await actor.selectOptions(screen.getByLabelText("Company"), "company-1")
    await actor.type(screen.getByLabelText("Code"), "SALES")
    await actor.type(screen.getByLabelText("Name"), "Sales")
    await actor.click(screen.getByRole("button", { name: "Save role" }))

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith(
      "/roles/",
      expect.objectContaining({
        company: "company-1",
        code: "SALES",
        name: "Sales",
        permission_ids: ["permission-1", "permission-2"],
      }),
    ))
  })

  it("restores selected permissions while editing", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <ResourceRecordForm
          config={resourceConfigs.roles}
          record={{ id: "role-1", permission_details: [{ id: "permission-2", code: "crm.customer.create", name: "Create customers" }] }}
          onSuccess={vi.fn()}
        />
      </QueryClientProvider>,
    )

    expect(await screen.findByRole("checkbox", { name: "Create customers" })).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "View customers" })).not.toBeChecked()
    expect(screen.getAllByText("1 of 2 selected")).toHaveLength(2)
  })
})

describe("spreadsheet imports for organization registers", () => {
  afterEach(() => cleanup())
  beforeEach(() => {
    mocks.apiGet.mockResolvedValue({
      results: [],
      pagination: { count: 0, page: 1, page_size: 25, pages: 1, next: null, previous: null },
    })
    mocks.apiUpload.mockResolvedValue({ imported: 1 })
  })

  it("enables imports for every existing organization register", () => {
    for (const key of ["companies", "branches", "departments", "designations", "warehouses", "employees"]) {
      expect(resourceConfigs[key].importTemplate).toBeDefined()
    }
  })

  it("uploads a company spreadsheet through the shared import dialog", async () => {
    const actor = userEvent.setup()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter><ResourcePage resourceKey="companies" /></MemoryRouter>
      </QueryClientProvider>,
    )

    await actor.click(await screen.findByRole("button", { name: "Import Excel / CSV" }))
    expect(screen.getByRole("dialog", { name: "Import previous companies" })).toBeInTheDocument()
    expect(screen.getByText(/Google Sheets/)).toBeInTheDocument()
    const upload = screen.getByLabelText("CSV or Excel file")
    await actor.upload(upload, new File(["code,name\nOLD,Old Company\n"], "companies.csv", { type: "text/csv" }))
    await actor.click(screen.getByRole("button", { name: "Import data" }))

    await waitFor(() => expect(mocks.apiUpload).toHaveBeenCalledWith(
      "/companies/import-history/",
      expect.any(FormData),
    ))
  })
})
