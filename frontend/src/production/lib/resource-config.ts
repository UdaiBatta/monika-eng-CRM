export type StaticOption = { value: string; label: string }

export type ResourceField = {
  name: string
  label: string
  type?: "text" | "email" | "number" | "date" | "textarea" | "boolean" | "select" | "relation" | "multi-relation"
  required?: boolean
  placeholder?: string
  help?: string
  options?: StaticOption[]
  relation?: {
    endpoint: string
    labelFields: string[]
  }
  defaultValue?: unknown
}

export type ResourceColumn = {
  key: string
  label: string
}

export type ResourceConfig = {
  key: string
  endpoint: string
  title: string
  description: string
  singular: string
  viewPermission: string
  managePermission: string
  columns: ResourceColumn[]
  fields: ResourceField[]
  searchPlaceholder?: string
  dedicatedEmployeeRoutes?: boolean
}

const activeField: ResourceField = { name: "is_active", label: "Active", type: "boolean", defaultValue: true }
const companyRelation = { endpoint: "/companies/", labelFields: ["code", "name"] }
const branchRelation = { endpoint: "/branches/", labelFields: ["code", "name"] }
const departmentRelation = { endpoint: "/departments/", labelFields: ["code", "name"] }
const designationRelation = { endpoint: "/designations/", labelFields: ["code", "name"] }

export const resourceConfigs: Record<string, ResourceConfig> = {
  employees: {
    key: "employees", endpoint: "/employees/", title: "Employee register", singular: "employee",
    description: "People, reporting lines, employment state, and optional user-account linkage.",
    viewPermission: "organization.employee.view", managePermission: "organization.employee.manage",
    dedicatedEmployeeRoutes: true,
    searchPlaceholder: "Search code, name, email or phone",
    columns: [
      { key: "employee_code", label: "Employee code" }, { key: "display_name", label: "Employee" },
      { key: "company_name", label: "Company" }, { key: "department_name", label: "Department" },
      { key: "designation_name", label: "Designation" }, { key: "employment_status", label: "Status" },
    ],
    fields: [
      { name: "user", label: "User account", type: "relation", relation: { endpoint: "/users/", labelFields: ["email"] }, help: "Optional. Employee and sign-in account remain separate records." },
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation },
      { name: "department", label: "Department", type: "relation", relation: departmentRelation },
      { name: "designation", label: "Designation", type: "relation", relation: designationRelation },
      { name: "reporting_manager", label: "Reporting manager", type: "relation", relation: { endpoint: "/employees/", labelFields: ["employee_code", "display_name"] } },
      { name: "employee_code", label: "Employee code", required: true },
      { name: "first_name", label: "First name", required: true },
      { name: "last_name", label: "Last name" },
      { name: "company_email", label: "Company email", type: "email" },
      { name: "phone", label: "Phone" },
      { name: "joining_date", label: "Joining date", type: "date", required: true },
      { name: "employment_type", label: "Employment type", type: "select", required: true, options: [
        { value: "PERMANENT", label: "Permanent" }, { value: "CONTRACT", label: "Contract" },
        { value: "TRAINEE", label: "Trainee" }, { value: "CONSULTANT", label: "Consultant" },
      ] },
      { name: "employment_status", label: "Employment status", type: "select", defaultValue: "ACTIVE", options: [
        { value: "ACTIVE", label: "Active" }, { value: "NOTICE", label: "Notice period" }, { value: "INACTIVE", label: "Inactive" },
      ] },
    ],
  },
  companies: {
    key: "companies", endpoint: "/companies/", title: "Companies", singular: "company",
    description: "Legal entities and organization boundaries.",
    viewPermission: "organization.company.view", managePermission: "organization.company.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "legal_name", label: "Legal name" }, { key: "gstin", label: "GSTIN" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true },
      { name: "legal_name", label: "Legal name" }, { name: "gstin", label: "GSTIN" }, { name: "pan", label: "PAN" },
      { name: "timezone", label: "Timezone", defaultValue: "Asia/Kolkata", required: true }, activeField,
    ],
  },
  branches: {
    key: "branches", endpoint: "/branches/", title: "Branches", singular: "branch",
    description: "Physical and administrative operating locations.", viewPermission: "organization.branch.view", managePermission: "organization.branch.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Branch" }, { key: "company_name", label: "Company" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true },
      { name: "address", label: "Address", type: "textarea" }, activeField,
    ],
  },
  departments: {
    key: "departments", endpoint: "/departments/", title: "Departments", singular: "department",
    description: "Company and optional branch-aligned organization units.", viewPermission: "organization.department.view", managePermission: "organization.department.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Department" }, { key: "company_name", label: "Company" }, { key: "branch_name", label: "Branch" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation },
      { name: "parent", label: "Parent department", type: "relation", relation: departmentRelation },
      { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, activeField,
    ],
  },
  designations: {
    key: "designations", endpoint: "/designations/", title: "Designations", singular: "designation",
    description: "Company-specific job titles and responsibility markers.", viewPermission: "organization.designation.view", managePermission: "organization.designation.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Designation" }, { key: "company_name", label: "Company" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "company", label: "Company", type: "relation", relation: companyRelation, required: true }, { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, activeField],
  },
  warehouses: {
    key: "warehouses", endpoint: "/warehouses/", title: "Warehouses", singular: "warehouse",
    description: "Branch-bound storage and inventory responsibility scopes.", viewPermission: "organization.warehouse.view", managePermission: "organization.warehouse.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Warehouse" }, { key: "company_name", label: "Company" }, { key: "branch_name", label: "Branch" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation, required: true },
      { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true },
      { name: "address", label: "Address", type: "textarea" }, activeField,
    ],
  },
  roles: {
    key: "roles", endpoint: "/roles/", title: "Roles", singular: "role",
    description: "Company-owned roles composed from the permission catalogue.", viewPermission: "rbac.role.view", managePermission: "rbac.role.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Role" }, { key: "company_name", label: "Company" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true },
      { name: "description", label: "Description", type: "textarea" },
      { name: "permission_ids", label: "Permissions", type: "multi-relation", relation: { endpoint: "/permissions/", labelFields: ["code", "name"] }, help: "Permissions aggregate across all active assignments." },
      activeField,
    ],
  },
  permissions: {
    key: "permissions", endpoint: "/permissions/", title: "Permission catalogue", singular: "permission",
    description: "Stable capability codes consumed by the API and interface.", viewPermission: "rbac.permission.view", managePermission: "rbac.permission.manage",
    columns: [{ key: "code", label: "Permission code" }, { key: "name", label: "Name" }, { key: "description", label: "Description" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "description", label: "Description", type: "textarea" }, activeField],
  },
  "role-assignments": {
    key: "role-assignments", endpoint: "/role-assignments/", title: "Role assignments", singular: "assignment",
    description: "Attach roles to users at company, branch, department, warehouse, or self scope.", viewPermission: "rbac.assignment.view", managePermission: "rbac.assignment.manage",
    columns: [{ key: "user_email", label: "User" }, { key: "role_name", label: "Role" }, { key: "scope_type", label: "Scope" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "user", label: "User", type: "relation", relation: { endpoint: "/users/", labelFields: ["email"] }, required: true },
      { name: "role", label: "Role", type: "relation", relation: { endpoint: "/roles/", labelFields: ["code", "name"] }, required: true },
      { name: "scope_type", label: "Scope type", type: "select", required: true, options: ["COMPANY", "BRANCH", "DEPARTMENT", "WAREHOUSE", "SELF"].map((value) => ({ value, label: value.replace("_", " ") })) },
      { name: "company", label: "Company", type: "relation", relation: companyRelation },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation },
      { name: "department", label: "Department", type: "relation", relation: departmentRelation },
      { name: "warehouse", label: "Warehouse", type: "relation", relation: { endpoint: "/warehouses/", labelFields: ["code", "name"] } },
      activeField,
    ],
  },
  "permission-overrides": {
    key: "permission-overrides", endpoint: "/permission-overrides/", title: "Permission overrides", singular: "override",
    description: "Explicit per-user allow or deny rules. Deny always wins.", viewPermission: "rbac.override.view", managePermission: "rbac.override.manage",
    columns: [{ key: "user_email", label: "User" }, { key: "permission_code", label: "Permission" }, { key: "effect", label: "Effect" }, { key: "scope_type", label: "Scope" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "user", label: "User", type: "relation", relation: { endpoint: "/users/", labelFields: ["email"] }, required: true },
      { name: "permission", label: "Permission", type: "relation", relation: { endpoint: "/permissions/", labelFields: ["code", "name"] }, required: true },
      { name: "effect", label: "Effect", type: "select", required: true, options: [{ value: "ALLOW", label: "Allow" }, { value: "DENY", label: "Deny" }] },
      { name: "scope_type", label: "Scope type", type: "select", required: true, options: ["COMPANY", "BRANCH", "DEPARTMENT", "WAREHOUSE", "SELF"].map((value) => ({ value, label: value })) },
      { name: "company", label: "Company", type: "relation", relation: companyRelation },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation },
      { name: "department", label: "Department", type: "relation", relation: departmentRelation },
      { name: "warehouse", label: "Warehouse", type: "relation", relation: { endpoint: "/warehouses/", labelFields: ["code", "name"] } },
      { name: "reason", label: "Reason" }, activeField,
    ],
  },
  "company-settings": {
    key: "company-settings", endpoint: "/company-settings/", title: "Company settings", singular: "settings record",
    description: "India-safe defaults, formats, currency, timezone, and financial year rules.", viewPermission: "configuration.settings.view", managePermission: "configuration.settings.manage",
    columns: [{ key: "company_name", label: "Company" }, { key: "currency_code", label: "Currency" }, { key: "timezone", label: "Timezone" }, { key: "financial_year_start_month", label: "FY start month" }, { key: "date_format", label: "Date format" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "default_currency", label: "Default currency", type: "relation", relation: { endpoint: "/currencies/", labelFields: ["code", "name"] } },
      { name: "timezone", label: "Timezone", defaultValue: "Asia/Kolkata", required: true },
      { name: "country_code", label: "Country code", defaultValue: "IN", required: true },
      { name: "financial_year_start_month", label: "Financial year start month", type: "number", defaultValue: 4, required: true },
      { name: "date_format", label: "Date format", defaultValue: "DD-MM-YYYY", required: true },
      { name: "number_format", label: "Number format", defaultValue: "en-IN", required: true },
      { name: "document_footer", label: "Document footer", type: "textarea" },
    ],
  },
  "feature-flags": {
    key: "feature-flags", endpoint: "/feature-flags/", title: "Feature flags", singular: "feature flag",
    description: "Company-scoped release gates for controlled rollout.", viewPermission: "configuration.feature_flag.view", managePermission: "configuration.feature_flag.manage",
    columns: [{ key: "key", label: "Feature key" }, { key: "company_name", label: "Company" }, { key: "description", label: "Description" }, { key: "is_enabled", label: "Enabled" }],
    fields: [{ name: "company", label: "Company", type: "relation", relation: companyRelation, required: true }, { name: "key", label: "Key", required: true }, { name: "description", label: "Description" }, { name: "is_enabled", label: "Enabled", type: "boolean" }],
  },
  "document-sequences": {
    key: "document-sequences", endpoint: "/document-sequences/", title: "Document numbering", singular: "sequence",
    description: "PostgreSQL-locked, financial-year-aware sequence allocation with non-consuming preview.", viewPermission: "numbering.sequence.view", managePermission: "numbering.sequence.manage",
    columns: [{ key: "code", label: "Code" }, { key: "company_name", label: "Company" }, { key: "branch_name", label: "Branch" }, { key: "financial_year", label: "Financial year" }, { key: "preview", label: "Next preview" }, { key: "next_number", label: "Next counter" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "branch", label: "Branch", type: "relation", relation: branchRelation },
      { name: "code", label: "Document code", required: true }, { name: "financial_year", label: "Financial year", placeholder: "2026-27", required: true },
      { name: "template", label: "Template", defaultValue: "{company}/{code}/{fy}/{number}", required: true, help: "Allowed: {company}, {branch}, {code}, {fy}, {year}, {number}. Preview never consumes a number." },
      { name: "next_number", label: "Next number", type: "number", defaultValue: 1, required: true },
      { name: "padding", label: "Padding", type: "number", defaultValue: 5, required: true },
      { name: "reset_behavior", label: "Reset behavior", type: "select", defaultValue: "FINANCIAL_YEAR", options: [{ value: "FINANCIAL_YEAR", label: "Financial year" }, { value: "NEVER", label: "Never" }] }, activeField,
    ],
  },
  "document-categories": {
    key: "document-categories", endpoint: "/document-categories/", title: "Document categories", singular: "document category",
    description: "Company-owned file categories with explicit extensions, confidentiality defaults, and upload-size limits.",
    viewPermission: "documents.category.view", managePermission: "documents.category.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Category" }, { key: "company_name", label: "Company" }, { key: "max_upload_size_mb", label: "Max MB" }, { key: "default_confidential", label: "Confidential by default" }, { key: "is_active", label: "Active" }],
    fields: [
      { name: "company", label: "Company", type: "relation", relation: companyRelation, required: true },
      { name: "code", label: "Code", required: true },
      { name: "name", label: "Name", required: true },
      { name: "description", label: "Description", type: "textarea" },
      { name: "allowed_extensions", label: "Allowed file types", type: "multi-relation", required: true, options: ["pdf", "png", "jpg", "jpeg", "csv", "docx", "xlsx"].map((value) => ({ value, label: value.toUpperCase() })), help: "Select only the file types needed for this category." },
      { name: "max_upload_size_mb", label: "Maximum upload size (MB)", type: "number", defaultValue: 50 },
      { name: "default_confidential", label: "Confidential by default", type: "boolean" },
      activeField,
    ],
  },
  currencies: {
    key: "currencies", endpoint: "/currencies/", title: "Currencies", singular: "currency", description: "Currency codes and precision.",
    viewPermission: "masters.view", managePermission: "masters.manage", columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "symbol", label: "Symbol" }, { key: "decimal_places", label: "Decimals" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "symbol", label: "Symbol", required: true }, { name: "decimal_places", label: "Decimal places", type: "number", defaultValue: 2, required: true }, activeField],
  },
  "units-of-measure": {
    key: "units-of-measure", endpoint: "/units-of-measure/", title: "Units of measure", singular: "unit",
    description: "Reusable measurement units and precision.", viewPermission: "masters.view", managePermission: "masters.manage",
    columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "category", label: "Category" }, { key: "decimal_places", label: "Decimals" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "category", label: "Category" }, { name: "decimal_places", label: "Decimal places", type: "number", defaultValue: 3, required: true }, activeField],
  },
  "tax-rates": {
    key: "tax-rates", endpoint: "/tax-rates/", title: "Tax rates", singular: "tax rate", description: "Versioned company tax percentages and validity dates.",
    viewPermission: "masters.view", managePermission: "masters.manage", columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "company_name", label: "Company" }, { key: "rate_percent", label: "Rate %" }, { key: "valid_from", label: "Valid from" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "company", label: "Company", type: "relation", relation: companyRelation, required: true }, { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "rate_percent", label: "Rate percent", type: "number", required: true }, { name: "valid_from", label: "Valid from", type: "date", required: true }, { name: "valid_to", label: "Valid to", type: "date" }, activeField],
  },
  "payment-terms": {
    key: "payment-terms", endpoint: "/payment-terms/", title: "Payment terms", singular: "payment term", description: "Company payment windows.",
    viewPermission: "masters.view", managePermission: "masters.manage", columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "company_name", label: "Company" }, { key: "due_days", label: "Due days" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "company", label: "Company", type: "relation", relation: companyRelation, required: true }, { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "due_days", label: "Due days", type: "number", defaultValue: 0, required: true }, activeField],
  },
  "delivery-terms": {
    key: "delivery-terms", endpoint: "/delivery-terms/", title: "Delivery terms", singular: "delivery term", description: "Company delivery conditions.",
    viewPermission: "masters.view", managePermission: "masters.manage", columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "company_name", label: "Company" }, { key: "description", label: "Description" }, { key: "is_active", label: "Active" }],
    fields: [{ name: "company", label: "Company", type: "relation", relation: companyRelation, required: true }, { name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "description", label: "Description", type: "textarea" }, activeField],
  },
}
