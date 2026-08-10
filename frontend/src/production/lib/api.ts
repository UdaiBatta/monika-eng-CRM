export type ApiErrorBody = {
  error?: {
    status?: number
    code?: string
    message?: string
    details?: unknown
  }
}

export class ApiError extends Error {
  status: number
  details: unknown

  constructor(status: number, message: string, details?: unknown) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.details = details
  }
}

function cookie(name: string) {
  const item = document.cookie.split("; ").find((value) => value.startsWith(`${name}=`))
  return item ? decodeURIComponent(item.split("=")[1]) : undefined
}

async function ensureCsrfToken() {
  if (!cookie("csrftoken")) {
    const response = await fetch("/api/v1/auth/csrf/", { credentials: "include" })
    if (!response.ok) throw new ApiError(response.status, "Could not establish a secure session.")
  }
  return cookie("csrftoken")
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase()
  const unsafe = !["GET", "HEAD", "OPTIONS"].includes(method)
  const csrfToken = unsafe ? await ensureCsrfToken() : undefined
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...init.headers,
    },
  })

  if (response.status === 204) return undefined as T
  const body = (await response.json().catch(() => ({}))) as ApiErrorBody | T
  if (!response.ok) {
    const error = (body as ApiErrorBody).error
    throw new ApiError(response.status, error?.message ?? "The request could not be completed.", error?.details)
  }
  return body as T
}

export function apiGet<T>(path: string) {
  return apiRequest<T>(path)
}

export function apiPost<T>(path: string, body?: unknown) {
  return apiRequest<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) })
}

export function apiPatch<T>(path: string, body: unknown) {
  return apiRequest<T>(path, { method: "PATCH", body: JSON.stringify(body) })
}
