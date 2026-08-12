import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { CurrentUser } from "@/production/lib/types"
import { resourceConfigs } from "@/production/lib/resource-config"
import ResourcePage from "./resource-page"

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
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
  apiUpload: mocks.apiUpload,
}))
vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, permission: string) => Boolean(user?.permissions.includes(permission)),
}))

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
