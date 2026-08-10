import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import ERPNotificationBell from "@/production/components/notification-center"
import type { ApprovalRequest, AuditEvent, CurrentUser, ERPDocument } from "@/production/lib/types"
import ApprovalDetailPage from "./approval-detail-page"
import { ERPApprovalList } from "./approvals-page"
import { ERPAuditChangeView } from "./activity-history-page"
import { ERPDocumentList } from "./documents-page"
import DocumentsPage from "./documents-page"
import DocumentDetailPage from "./document-detail-page"

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiUpload: vi.fn(),
  apiDownload: vi.fn(),
  user: {
    id: "user-1",
    email: "engineer@example.test",
    first_name: "Test",
    last_name: "Engineer",
    is_active: true,
    is_staff: false,
    employee: null,
    permissions: [] as string[],
  } as CurrentUser,
}))

vi.mock("@/production/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/production/lib/api")>()
  return {
    ...actual,
    apiGet: mocks.apiGet,
    apiPost: mocks.apiPost,
    apiUpload: mocks.apiUpload,
    apiDownload: mocks.apiDownload,
  }
})

vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: mocks.user }),
  hasPermission: (user: CurrentUser | undefined, code: string) => Boolean(user?.permissions.includes(code)),
}))

function renderApp(node: React.ReactNode, path = "/") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={[path]}>{node}</MemoryRouter></QueryClientProvider>)
}

const document: ERPDocument = {
  id: "doc-1",
  company: "company-1",
  company_name: "Monika Engineers",
  document_number: "DOC-001",
  title: "Control Panel GA Drawing",
  description: "General arrangement",
  category: "category-1",
  category_name: "Engineering drawing",
  status: "ACTIVE",
  created_by_name: "Test Engineer",
  is_confidential: true,
  current_version: {
    id: "version-2",
    version_number: 2,
    safe_display_filename: "drawing-r2.pdf",
    original_filename: "drawing-r2.pdf",
    mime_type: "application/pdf",
    file_extension: "pdf",
    size_bytes: 2048,
    checksum_sha256: "abc",
    uploaded_by_name: "Test Engineer",
    uploaded_at: "2026-08-10T10:00:00Z",
    notes: "Approved revision",
    scan_status: "NOT_SCANNED",
  },
  versions: [],
  links: [],
  archived_at: null,
  archive_reason: "",
  created_at: "2026-08-10T09:00:00Z",
  updated_at: "2026-08-10T10:00:00Z",
}

const approval: ApprovalRequest = {
  id: "approval-1",
  company: "company-1",
  workflow_name: "Drawing review",
  workflow_version_number: 1,
  entity_type: "document",
  entity_id: "doc-1",
  entity_reference: "Control Panel GA Drawing",
  requested_by: "requester-1",
  requested_by_name: "Design Engineer",
  requested_at: "2026-08-10T09:00:00Z",
  status: "IN_PROGRESS",
  status_label: "In progress",
  current_step_name: "Engineering approval",
  completed_at: null,
  submission_comment: "Please verify dimensions.",
  snapshot_metadata: {},
  steps: [{
    id: "step-1",
    sequence: 1,
    step_name: "Engineering approval",
    status: "OPEN",
    opened_at: "2026-08-10T09:00:00Z",
    decided_at: null,
    assignments: [{ id: "assignment-1", approver: "user-1", approver_name: "Test Engineer", status: "PENDING" }],
    decisions: [],
  }],
}

describe("Phase 1 shared-service frontend", () => {
  afterEach(() => cleanup())

  beforeEach(() => {
    mocks.apiGet.mockReset()
    mocks.apiPost.mockReset()
    mocks.apiUpload.mockReset()
    mocks.apiDownload.mockReset()
    mocks.user.permissions = [
      "documents.document.view",
      "documents.document.upload",
      "documents.document.download",
      "approvals.request.view",
      "approvals.request.approve",
      "notifications.notification.view",
      "audit.event.view",
    ]
  })

  it("shows the unread notification indicator and marks an opened item read", async () => {
    mocks.apiGet.mockImplementation((path: string) => path.includes("unread-count")
      ? Promise.resolve({ count: 1 })
      : Promise.resolve({ results: [{ id: "notification-1", company: "company-1", notification_type: "APPROVAL_REQUIRED", severity: "ACTION_REQUIRED", severity_label: "Action required", title: "Needs your approval", message: "DRAW-001 is ready for review.", entity_type: "approval_request", entity_id: "approval-1", action_url: "/app/approvals/approval-1", read_at: null, archived_at: null, created_at: "2026-08-10T10:00:00Z" }], pagination: { count: 1, page: 1, page_size: 25, pages: 1, next: null, previous: null } }))
    mocks.apiPost.mockResolvedValue({})
    const user = userEvent.setup()
    renderApp(<ERPNotificationBell />)

    await user.click(await screen.findByRole("button", { name: "Notifications, 1 unread" }))
    await user.click(await screen.findByRole("button", { name: /Needs your approval/ }))

    expect(mocks.apiPost).toHaveBeenCalledWith("/notifications/notification-1/read/")
  })

  it("validates an unsafe document extension before upload", async () => {
    mocks.apiGet.mockImplementation((path: string) => path.startsWith("/documents/")
      ? Promise.resolve({ results: [], pagination: { count: 0, page: 1, page_size: 25, pages: 0, next: null, previous: null } })
      : Promise.resolve({ results: [{ id: "category-1", code: "DRAW", name: "Drawings", is_active: true, allowed_extensions: ["pdf"], max_upload_size_mb: 50 }], pagination: { count: 1, page: 1, page_size: 25, pages: 1, next: null, previous: null } }))
    const user = userEvent.setup({ applyAccept: false })
    renderApp(<DocumentsPage />)
    await user.click((await screen.findAllByRole("button", { name: "Upload document" }))[0])
    await user.upload(screen.getByLabelText("File"), new File(["binary"], "malware.exe", { type: "application/octet-stream" }))
    await user.selectOptions(screen.getByLabelText("Category"), "category-1")
    await user.click(screen.getByRole("button", { name: "Upload" }))

    expect(await screen.findByText(/Choose a permitted file type/)).toBeInTheDocument()
    expect(mocks.apiUpload).not.toHaveBeenCalled()
  })

  it("renders business-friendly document version information", () => {
    render(<ERPDocumentList documents={[document]} onOpen={() => undefined} />)
    expect(screen.getAllByText(/Version 2/).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Control Panel GA Drawing").length).toBeGreaterThan(0)
    expect(screen.getAllByText(/2 KB/).length).toBeGreaterThan(0)
  })

  it("submits a document through an active approval workflow", async () => {
    mocks.user.permissions.push("approvals.request.submit")
    mocks.apiGet.mockImplementation((path: string) => path.startsWith("/approval-workflows/")
      ? Promise.resolve({ results: [{ id: "workflow-1", name: "Drawing review", description: "", current_version: "version-1" }], pagination: { count: 1, page: 1, page_size: 100, pages: 1, next: null, previous: null } })
      : Promise.resolve(document))
    mocks.apiPost.mockResolvedValue(approval)
    const user = userEvent.setup()
    renderApp(<Routes><Route path="/app/documents/:documentId" element={<DocumentDetailPage />} /><Route path="/app/approvals/:approvalId" element={<div>Approval opened</div>} /></Routes>, "/app/documents/doc-1")

    await user.click(await screen.findByRole("button", { name: "Submit for approval" }))
    await user.selectOptions(screen.getByLabelText("Approval workflow"), "workflow-1")
    await user.type(screen.getByLabelText("Message to approver"), "Please verify dimensions.")
    await user.click(screen.getByRole("button", { name: "Submit for approval" }))

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/approvals/requests/", expect.objectContaining({ workflow_id: "workflow-1", supporting_document_ids: ["doc-1"] })))
  })

  it("renders an approval queue item and deliberate approval confirmation", async () => {
    const user = userEvent.setup()
    const onOpen = vi.fn()
    const { unmount } = render(<ERPApprovalList items={[approval]} onOpen={onOpen} />)
    await user.click(screen.getByRole("button", { name: /Control Panel GA Drawing/ }))
    expect(onOpen).toHaveBeenCalledWith(approval)
    unmount()

    mocks.apiGet.mockImplementation((path: string) => path.includes("supporting-documents") ? Promise.resolve([]) : Promise.resolve(approval))
    renderApp(<Routes><Route path="/app/approvals/:approvalId" element={<ApprovalDetailPage />} /></Routes>, "/app/approvals/approval-1")
    await user.click(await screen.findByRole("button", { name: "Approve" }))
    expect(await screen.findByText("Approve this request?")).toBeInTheDocument()
    expect(screen.getByText("Your decision is recorded permanently and may complete or advance the workflow.")).toBeInTheDocument()
  })

  it("lets a workflow administrator reassign a pending approval", async () => {
    mocks.user.permissions.push("approvals.workflow.manage")
    mocks.apiGet.mockImplementation((path: string) => path.includes("supporting-documents")
      ? Promise.resolve([])
      : path.startsWith("/employees/")
        ? Promise.resolve({ results: [{ id: "employee-2", user: "user-2", display_name: "Replacement Engineer", employee_code: "ME-002", employment_status: "ACTIVE" }], pagination: { count: 1, page: 1, page_size: 100, pages: 1, next: null, previous: null } })
        : Promise.resolve(approval))
    mocks.apiPost.mockResolvedValue(approval)
    const user = userEvent.setup()
    renderApp(<Routes><Route path="/app/approvals/:approvalId" element={<ApprovalDetailPage />} /></Routes>, "/app/approvals/approval-1")

    await user.click(await screen.findByRole("button", { name: "Reassign" }))
    await user.selectOptions(screen.getByLabelText("New approver"), "user-2")
    await user.type(screen.getByLabelText("Reason"), "Current approver is on leave.")
    await user.click(screen.getByRole("button", { name: "Reassign approval" }))

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledWith("/approvals/requests/approval-1/reassign/", { assignment_id: "assignment-1", approver_id: "user-2", reason: "Current approver is on leave." }))
  })

  it("shows a permission state and hides document actions when access is absent", () => {
    mocks.user.permissions = []
    renderApp(<Routes><Route path="/app/approvals/:approvalId" element={<ApprovalDetailPage />} /></Routes>, "/app/approvals/approval-1")
    expect(screen.getByText("Access restricted")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument()
  })

  it("renders audit changes as readable before and after values", () => {
    const changes: AuditEvent["changes"] = { quantity: { old: 10, new: 12 } }
    render(<ERPAuditChangeView changes={changes} />)
    expect(screen.getByText("Before")).toBeInTheDocument()
    expect(screen.getByText("10")).toBeInTheDocument()
    expect(screen.getByText("After")).toBeInTheDocument()
    expect(screen.getByText("12")).toBeInTheDocument()
  })

  it("keeps a stable loading state while document data is pending", async () => {
    mocks.apiGet.mockReturnValue(new Promise(() => undefined))
    renderApp(<DocumentsPage />)
    await waitFor(() => expect(screen.getByLabelText("Loading")).toBeInTheDocument())
  })
})
