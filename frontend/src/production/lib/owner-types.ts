import type { Identifier, Paginated } from "./types"

export type OwnerWorkSummary = {
  work_type: string
  label: string
  open: number
  unassigned: number
}

export type OwnerOverview = {
  company: { id: Identifier; name: string; code: string }
  people: { active_employees: number; active_accounts: number; roles: number }
  work: { open: number; unassigned: number; by_type: OwnerWorkSummary[] }
  attention: { data_quality: number; pending_approvals: number }
  recent_admin_activity: Array<{
    id: Identifier
    summary: string
    actor: string
    occurred_at: string
  }>
}

export type OwnerWorkItem = {
  work_type: string
  work_type_label: string
  id: Identifier
  reference: string
  title: string
  status: string
  status_code: string
  assigned_to: Identifier | null
  assigned_to_name: string
  updated_at: string
  action_url: string
}

export type OwnerWorkResponse = Paginated<OwnerWorkItem>

export type OwnerEmployee = {
  id: Identifier
  employee_code: string
  display_name: string
}

export type OwnerFeature = {
  key: string
  name: string
  description: string
  implemented: boolean
  status: "Enabled" | "Disabled" | "Not available yet"
  is_enabled: boolean
  record_version: number | null
  action_url: string
}

export type DataQualityIssue = {
  type: string
  severity: "problem" | "attention" | "review"
  count: number
  message: string
  recommended_action: string
  action_url: string
}

export type SystemHealth = {
  checked_at: string
  services: Array<{
    name: string
    status: "Available" | "Unavailable" | "Configured" | "Unknown" | "Not configured"
    detail: string
  }>
}

export type AccessExplanation = {
  allowed: boolean
  permission: string
  permission_name: string
  reason: string
  scope: Record<string, string>
  roles: Array<{ name: string; scope: string }>
  overrides: Array<{ effect: "ALLOW" | "DENY"; scope: string; reason: string }>
}
