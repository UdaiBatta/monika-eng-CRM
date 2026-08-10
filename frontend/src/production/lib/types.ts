export type Identifier = string

export type Paginated<T> = {
  results: T[]
  pagination: {
    page: number
    page_size: number
    pages: number
    count: number
    next: string | null
    previous: string | null
  }
}

export type EmployeeSummary = {
  id: Identifier
  employee_code: string
  display_name: string
  company_id: Identifier
  branch_id?: Identifier | null
  department_id?: Identifier | null
  designation_id?: Identifier | null
}

export type CurrentUser = {
  id: Identifier
  email: string
  username?: string | null
  first_name: string
  last_name: string
  is_active: boolean
  is_staff: boolean
  employee: EmployeeSummary | null
  permissions: string[]
}

export type FoundationRecord = Record<string, unknown> & { id: Identifier }

export type DocumentVersion = {
  id: Identifier
  version_number: number
  safe_display_filename: string
  original_filename: string
  mime_type: string
  file_extension: string
  size_bytes: number
  checksum_sha256: string
  uploaded_by_name: string
  uploaded_at: string
  notes: string
  scan_status: "NOT_SCANNED" | "PENDING_SCAN" | "CLEAN" | "QUARANTINED" | "FAILED_SCAN"
}

export type DocumentLink = {
  id: Identifier
  entity_type: string
  entity_id: string
  entity_reference: string
  relationship_type: string
  linked_at: string
}

export type ERPDocument = {
  id: Identifier
  company: Identifier
  company_name: string
  document_number: string
  title: string
  description: string
  category: Identifier
  category_name: string
  status: "ACTIVE" | "ARCHIVED"
  created_by_name: string
  is_confidential: boolean
  current_version: DocumentVersion | null
  versions: DocumentVersion[]
  links: DocumentLink[]
  archived_at: string | null
  archive_reason: string
  created_at: string
  updated_at: string
}

export type ApprovalAssignment = {
  id: Identifier
  approver: Identifier | null
  approver_name: string
  status: string
}

export type ApprovalDecision = {
  id: Identifier
  assignment: Identifier
  decided_by_name: string
  decision: string
  comment: string
  decided_at: string
}

export type ApprovalStep = {
  id: Identifier
  sequence: number
  step_name: string
  status: string
  opened_at: string | null
  decided_at: string | null
  assignments: ApprovalAssignment[]
  decisions: ApprovalDecision[]
}

export type ApprovalRequest = {
  id: Identifier
  company: Identifier
  workflow_name: string
  workflow_version_number: number
  entity_type: string
  entity_id: string
  entity_reference: string
  requested_by: Identifier | null
  requested_by_name: string
  requested_at: string
  status: string
  status_label: string
  current_step_name: string | null
  completed_at: string | null
  submission_comment: string
  snapshot_metadata: Record<string, unknown>
  steps: ApprovalStep[]
}

export type ERPNotification = {
  id: Identifier
  company: Identifier
  notification_type: string
  severity: string
  severity_label: string
  title: string
  message: string
  entity_type: string
  entity_id: string
  action_url: string
  read_at: string | null
  archived_at: string | null
  created_at: string
}

export type AuditEvent = {
  id: Identifier
  actor_name: string
  action: string
  action_label: string
  module: string
  entity_type: string
  entity_id: string
  entity_reference: string
  summary: string
  changes: Record<string, { old?: unknown; new?: unknown }>
  occurred_at: string
}
