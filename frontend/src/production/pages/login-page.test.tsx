import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import LoginPage from "./login-page"

const mocks = vi.hoisted(() => ({ apiGet: vi.fn(), apiPost: vi.fn() }))

vi.mock("@/production/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/production/lib/api")>()
  return { ...actual, apiGet: mocks.apiGet, apiPost: mocks.apiPost }
})

vi.mock("@/production/lib/auth", () => ({
  currentUserQueryKey: ["auth", "me"],
  useCurrentUser: () => ({ data: undefined }),
}))

describe("LoginPage", () => {
  beforeEach(() => {
    mocks.apiGet.mockReset()
    mocks.apiPost.mockReset()
  })

  it("submits email and password to the session login endpoint", async () => {
    mocks.apiPost.mockResolvedValue({ id: "1", email: "admin@example.test", permissions: [] })
    mocks.apiGet.mockResolvedValue({ id: "1", email: "admin@example.test", permissions: [] })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const user = userEvent.setup()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.type(screen.getByLabelText("Email or username"), "admin@example.test")
    await user.type(screen.getByLabelText("Password"), "SecurePassword-1")
    await user.click(screen.getByRole("button", { name: "Enter workspace" }))

    expect(mocks.apiPost).toHaveBeenCalledWith("/auth/login/", {
      identifier: "admin@example.test",
      password: "SecurePassword-1",
    })
  })
})
