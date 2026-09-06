import { afterEach, describe, expect, it, vi } from "vitest"

import { apiGet, apiPost } from "./api"

afterEach(() => {
  vi.restoreAllMocks()
  document.cookie = "csrftoken=; Max-Age=0; path=/"
})

describe("api client", () => {
  it("sends same-origin credentials and a CSRF token for mutations", async () => {
    document.cookie = "csrftoken=secure-test-token; path=/"
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "1" }), { status: 200, headers: { "Content-Type": "application/json" } }),
    )

    await apiPost("/employees/", { first_name: "Test" })

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/employees/", expect.objectContaining({
      method: "POST",
      credentials: "include",
      headers: expect.objectContaining({ "X-CSRFToken": "secure-test-token" }),
    }))
  })

  it("normalizes the backend error envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { status: 403, message: "Permission denied.", details: {} } }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    )

    await expect(apiGet("/employees/")).rejects.toEqual(expect.objectContaining({
      status: 403,
      message: "Permission denied.",
    }))
  })

  it("explains a non-JSON CSRF rejection", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("<html>CSRF verification failed</html>", {
        status: 403,
        headers: { "Content-Type": "text/html" },
      }),
    )

    await expect(apiGet("/employees/")).rejects.toEqual(expect.objectContaining({
      status: 403,
      message: "The secure session was rejected. Close and reopen the app, then try again.",
    }))
  })
})
