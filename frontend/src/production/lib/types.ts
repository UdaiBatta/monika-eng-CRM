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
