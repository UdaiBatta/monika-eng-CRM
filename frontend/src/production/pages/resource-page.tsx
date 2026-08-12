import { useMemo, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, FileSpreadsheet, Pencil, Plus, Search, Upload } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldContent, FieldDescription, FieldError, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { ApiError, apiGet, apiPatch, apiPost, apiUpload } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import { resourceConfigs, type ResourceConfig, type ResourceField } from "@/production/lib/resource-config"
import type { FoundationRecord, Paginated } from "@/production/lib/types"

type FormValues = Record<string, unknown>

const permissionGroupLabels: Record<string, string> = {
  "crm.external_enquiry": "Incoming enquiries",
  "crm.customer": "Customers",
  "crm.contact": "Customer contacts",
  "enquiry.enquiry": "Active enquiries",
  "crm.activity": "Follow-ups",
  "engineering.feasibility": "Engineering reviews",
  "estimation.estimate": "Commercial estimates",
  "crm.quotation": "Quotations",
  "documents.document": "Documents",
  "documents.category": "Document categories",
  "approvals.request": "Approval requests",
  "approvals.workflow": "Approval workflows",
  "notifications.notification": "Notifications",
  "organization.company": "Companies",
  "organization.branch": "Branches",
  "organization.department": "Departments",
  "organization.designation": "Designations",
  "organization.employee": "Employees",
  "organization.warehouse": "Warehouses",
  "accounts.user": "User accounts",
  "rbac.role": "Roles",
  "rbac.permission": "Permissions",
  "rbac.assignment": "Role assignments",
  "rbac.override": "Permission overrides",
  "configuration.settings": "Company settings",
  "configuration.feature_flag": "Feature flags",
  "numbering.sequence": "Numbering",
  "audit.event": "Activity history",
  masters: "Foundation masters",
}

function permissionGroupKey(code: string) {
  const parts = code.split(".")
  return parts.length > 2 ? `${parts[0]}.${parts[1]}` : parts[0]
}

function permissionGroupLabel(key: string) {
  return permissionGroupLabels[key] ?? key.replaceAll("_", " ").replaceAll(".", " · ")
}

async function fetchAllRelationOptions(endpoint: string) {
  const separator = endpoint.includes("?") ? "&" : "?"
  const results: FoundationRecord[] = []
  let page = 1
  let pages = 1
  do {
    const response = await apiGet<Paginated<FoundationRecord>>(`${endpoint}${separator}page=${page}&page_size=100`)
    results.push(...response.results)
    pages = response.pagination.pages
    page += 1
  } while (page <= pages)
  return results
}

type PermissionGroup = {
  key: string
  label: string
  permissions: FoundationRecord[]
}

function PermissionPicker({
  options,
  value,
  onChange,
  isLoading,
  error,
}: {
  options: FoundationRecord[]
  value: string[]
  onChange: (value: string[]) => void
  isLoading: boolean
  error?: Error | null
}) {
  const [search, setSearch] = useState("")
  const selected = useMemo(() => new Set(value), [value])
  const groups = useMemo(() => {
    const query = search.trim().toLowerCase()
    const grouped = new Map<string, PermissionGroup>()
    for (const permission of options) {
      const code = String(permission.code ?? "")
      const name = String(permission.name ?? "")
      if (query && !`${code} ${name}`.toLowerCase().includes(query)) continue
      const key = permissionGroupKey(code)
      const group = grouped.get(key) ?? { key, label: permissionGroupLabel(key), permissions: [] }
      group.permissions.push(permission)
      grouped.set(key, group)
    }
    return Array.from(grouped.values()).sort((left, right) => left.label.localeCompare(right.label))
  }, [options, search])
  const visibleIds = groups.flatMap((group) => group.permissions.map((permission) => String(permission.id)))

  function togglePermission(id: string, checked: boolean) {
    const next = new Set(value)
    if (checked) next.add(id)
    else next.delete(id)
    onChange(Array.from(next))
  }

  function toggleGroup(group: PermissionGroup) {
    const ids = group.permissions.map((permission) => String(permission.id))
    const allSelected = ids.every((id) => selected.has(id))
    const next = new Set(value)
    for (const id of ids) {
      if (allSelected) next.delete(id)
      else next.add(id)
    }
    onChange(Array.from(next))
  }

  function selectVisible() {
    onChange(Array.from(new Set([...value, ...visibleIds])))
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />
  if (error) return <Alert variant="destructive"><AlertTitle>Could not load permissions</AlertTitle><AlertDescription>{error.message}</AlertDescription></Alert>

  return (
    <FieldSet>
      <FieldLegend>Permissions</FieldLegend>
      <FieldDescription>Select individual actions or use a section checkbox to select the whole responsibility area.</FieldDescription>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Field className="flex-1">
          <FieldLabel htmlFor="permission-search" className="sr-only">Search permissions</FieldLabel>
          <Input id="permission-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search permissions" />
        </Field>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{value.length} of {options.length} selected</Badge>
          <Button type="button" variant="outline" size="sm" onClick={selectVisible} disabled={!visibleIds.length}>Select visible</Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => onChange([])} disabled={!value.length}>Clear all</Button>
        </div>
      </div>
      {groups.length ? (
        <div className="grid items-start gap-4 lg:grid-cols-2">
          {groups.map((group) => {
            const ids = group.permissions.map((permission) => String(permission.id))
            const selectedCount = ids.filter((id) => selected.has(id)).length
            const groupChecked = selectedCount === ids.length ? true : selectedCount ? "indeterminate" : false
            return (
              <FieldSet key={group.key} className="rounded-lg border p-4">
                <FieldLegend className="sr-only">{group.label}</FieldLegend>
                <Field orientation="horizontal">
                  <Checkbox
                    id={`permission-group-${group.key}`}
                    aria-label={`Select all ${group.label}`}
                    checked={groupChecked}
                    onCheckedChange={() => toggleGroup(group)}
                  />
                  <FieldContent>
                    <FieldLabel htmlFor={`permission-group-${group.key}`}>{group.label}</FieldLabel>
                    <FieldDescription>{selectedCount} of {ids.length} selected</FieldDescription>
                  </FieldContent>
                </Field>
                <FieldGroup data-slot="checkbox-group" className="gap-3">
                  {group.permissions.map((permission) => {
                    const id = String(permission.id)
                    return (
                      <Field key={id} orientation="horizontal">
                        <Checkbox
                          id={`permission-${id}`}
                          checked={selected.has(id)}
                          onCheckedChange={(checked) => togglePermission(id, checked === true)}
                        />
                        <FieldContent>
                          <FieldLabel htmlFor={`permission-${id}`}>{String(permission.name)}</FieldLabel>
                          <FieldDescription>{String(permission.code)}</FieldDescription>
                        </FieldContent>
                      </Field>
                    )
                  })}
                </FieldGroup>
              </FieldSet>
            )
          })}
        </div>
      ) : (
        <Empty><EmptyHeader><EmptyTitle>No permissions found</EmptyTitle><EmptyDescription>Try a different search term.</EmptyDescription></EmptyHeader></Empty>
      )}
    </FieldSet>
  )
}

function recordValue(record: FoundationRecord | undefined, field: ResourceField) {
  if (!record) return field.defaultValue ?? (field.type === "boolean" ? false : field.type === "multi-relation" ? [] : "")
  if (field.name === "permission_ids") {
    return ((record.permission_details as FoundationRecord[] | undefined) ?? []).map((item) => String(item.id))
  }
  const value = record[field.name]
  return value ?? (field.type === "boolean" ? false : field.type === "multi-relation" ? [] : "")
}

function relationLabel(record: FoundationRecord, fields: string[]) {
  return fields.map((field) => record[field]).filter(Boolean).join(" · ") || String(record.id)
}

function cleanValues(config: ResourceConfig, values: FormValues) {
  return Object.fromEntries(config.fields.map((field) => {
    const value = values[field.name]
    if (field.type === "number") return [field.name, value === "" ? null : Number(value)]
    if (field.type === "relation") return [field.name, value || null]
    if (field.type === "multi-relation") return [field.name, Array.isArray(value) ? value : []]
    return [field.name, value]
  }))
}

function errorMessages(error: unknown) {
  if (!(error instanceof ApiError) || !error.details || typeof error.details !== "object") return {}
  return error.details as Record<string, string[] | string>
}

function csvCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`
}

function downloadImportTemplate(config: ResourceConfig) {
  if (!config.importTemplate) return
  const rows = [config.importTemplate.headers, config.importTemplate.example]
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n")
  const url = URL.createObjectURL(new Blob([`\uFEFF${csv}\r\n`], { type: "text/csv;charset=utf-8" }))
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `monika-${config.key}-import-template.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

export function ResourceRecordForm({
  config,
  record,
  onSuccess,
  submitLabel,
}: {
  config: ResourceConfig
  record?: FoundationRecord
  onSuccess: (record: FoundationRecord) => void
  submitLabel?: string
}) {
  const queryClient = useQueryClient()
  const relationFields = config.fields.filter((field) => field.relation)
  const relationQueries = useQueries({
    queries: relationFields.map((field) => ({
      queryKey: ["options", field.relation?.endpoint],
      queryFn: () => fetchAllRelationOptions(String(field.relation?.endpoint)),
      staleTime: 60_000,
    })),
  })
  const defaultValues = useMemo(
    () => Object.fromEntries(config.fields.map((field) => [field.name, recordValue(record, field)])),
    [config, record],
  )
  const form = useForm<FormValues>({ defaultValues })
  const mutation = useMutation({
    mutationFn: (values: FormValues) => record
      ? apiPatch<FoundationRecord>(`${config.endpoint}${record.id}/`, cleanValues(config, values))
      : apiPost<FoundationRecord>(config.endpoint, cleanValues(config, values)),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["resource", config.key] })
      toast.success(`${config.singular[0].toUpperCase()}${config.singular.slice(1)} saved.`)
      onSuccess(saved)
    },
  })
  const serverErrors = errorMessages(mutation.error)

  return (
    <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <FieldGroup>
        {mutation.error ? (
          <Alert variant="destructive">
            <AlertTitle>Could not save {config.singular}</AlertTitle>
            <AlertDescription>{mutation.error.message}</AlertDescription>
          </Alert>
        ) : null}
        {config.fields.map((field) => {
          const fieldError = form.formState.errors[field.name]?.message
          const apiFieldError = serverErrors[field.name]
          const error = fieldError || (Array.isArray(apiFieldError) ? apiFieldError[0] : apiFieldError)
          const relationIndex = relationFields.indexOf(field)
          const relationQuery = relationIndex >= 0 ? relationQueries[relationIndex] : undefined
          const relationOptions = relationQuery?.data ?? []

          if (field.type === "boolean") {
            return (
              <Controller
                key={field.name}
                name={field.name}
                control={form.control}
                render={({ field: controlled }) => (
                  <Field orientation="horizontal">
                    <div className="flex-1">
                      <FieldLabel htmlFor={field.name}>{field.label}</FieldLabel>
                      {field.help ? <FieldDescription>{field.help}</FieldDescription> : null}
                    </div>
                    <Switch id={field.name} checked={Boolean(controlled.value)} onCheckedChange={controlled.onChange} />
                  </Field>
                )}
              />
            )
          }

          if (field.name === "permission_ids" && field.type === "multi-relation") {
            return (
              <Field key={field.name} data-invalid={Boolean(error)}>
                <Controller
                  name={field.name}
                  control={form.control}
                  render={({ field: controlled }) => (
                    <PermissionPicker
                      options={relationOptions}
                      value={Array.isArray(controlled.value) ? controlled.value as string[] : []}
                      onChange={controlled.onChange}
                      isLoading={Boolean(relationQuery?.isPending)}
                      error={relationQuery?.error}
                    />
                  )}
                />
                <FieldError>{error}</FieldError>
              </Field>
            )
          }

          if (field.type === "select" || field.type === "relation" || field.type === "multi-relation") {
            return (
              <Field key={field.name} data-invalid={Boolean(error)}>
                <FieldLabel htmlFor={field.name}>{field.label}</FieldLabel>
                <Controller
                  name={field.name}
                  control={form.control}
                  rules={{ required: field.required ? `${field.label} is required.` : false }}
                  render={({ field: controlled }) => (
                    <NativeSelect
                      id={field.name}
                      className="w-full"
                      multiple={field.type === "multi-relation"}
                      value={field.type === "multi-relation" ? (controlled.value as string[]) : String(controlled.value ?? "")}
                      onChange={(event) => controlled.onChange(
                        field.type === "multi-relation"
                          ? Array.from(event.currentTarget.selectedOptions, (option) => option.value)
                          : event.currentTarget.value,
                      )}
                      aria-invalid={Boolean(error)}
                    >
                      {field.type !== "multi-relation" ? <NativeSelectOption value="">Select {field.label.toLowerCase()}</NativeSelectOption> : null}
                      {(field.options ?? []).map((option) => <NativeSelectOption key={option.value} value={option.value}>{option.label}</NativeSelectOption>)}
                      {relationOptions.map((option) => (
                        <NativeSelectOption key={String(option.id)} value={String(option.id)}>
                          {relationLabel(option, field.relation?.labelFields ?? [])}
                        </NativeSelectOption>
                      ))}
                    </NativeSelect>
                  )}
                />
                {field.help ? <FieldDescription>{field.help}</FieldDescription> : null}
                <FieldError>{error}</FieldError>
              </Field>
            )
          }

          if (field.type === "textarea") {
            return (
              <Field key={field.name} data-invalid={Boolean(error)}>
                <FieldLabel htmlFor={field.name}>{field.label}</FieldLabel>
                <Textarea id={field.name} placeholder={field.placeholder} aria-invalid={Boolean(error)} {...form.register(field.name, { required: field.required ? `${field.label} is required.` : false })} />
                {field.help ? <FieldDescription>{field.help}</FieldDescription> : null}
                <FieldError>{error}</FieldError>
              </Field>
            )
          }

          return (
            <Field key={field.name} data-invalid={Boolean(error)}>
              <FieldLabel htmlFor={field.name}>{field.label}</FieldLabel>
              <Input
                id={field.name}
                type={field.type === "number" ? "number" : field.type === "date" ? "date" : field.type === "email" ? "email" : "text"}
                step={field.type === "number" ? "any" : undefined}
                placeholder={field.placeholder}
                aria-invalid={Boolean(error)}
                {...form.register(field.name, { required: field.required ? `${field.label} is required.` : false })}
              />
              {field.help ? <FieldDescription>{field.help}</FieldDescription> : null}
              <FieldError>{error}</FieldError>
            </Field>
          )
        })}
        <Button type="submit" size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
          {mutation.isPending ? "Saving…" : submitLabel ?? `Save ${config.singular}`}
        </Button>
      </FieldGroup>
    </form>
  )
}

function displayValue(value: unknown) {
  if (typeof value === "boolean") return <Badge variant={value ? "default" : "outline"}>{value ? "Yes" : "No"}</Badge>
  if (value === null || value === undefined || value === "") return <span className="text-muted-foreground">—</span>
  const text = String(value)
  if (["ACTIVE", "ALLOW", "ENABLED"].includes(text)) return <Badge>{text.replaceAll("_", " ")}</Badge>
  if (["INACTIVE", "DENY"].includes(text)) return <Badge variant="destructive">{text}</Badge>
  return text.replaceAll("_", " ")
}

export default function ResourcePage({ resourceKey }: { resourceKey: string }) {
  const config = resourceConfigs[resourceKey]
  const { data: user } = useCurrentUser()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [ordering, setOrdering] = useState("")
  const [formRecord, setFormRecord] = useState<FoundationRecord | null | undefined>(undefined)
  const [importOpen, setImportOpen] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const canManage = hasPermission(user, config.managePermission)
  const query = useQuery({
    queryKey: ["resource", config.key, page, search, ordering],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page) })
      if (search) params.set("search", search)
      if (ordering) params.set("ordering", ordering)
      return apiGet<Paginated<FoundationRecord>>(`${config.endpoint}?${params}`)
    },
  })
  const bulkImport = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData()
      body.append("file", file)
      return apiUpload<{ imported: number }>(`${config.endpoint}import-history/`, body)
    },
    onSuccess: async ({ imported }) => {
      await queryClient.invalidateQueries({ queryKey: ["resource", config.key] })
      setImportOpen(false)
      setImportFile(null)
      toast.success(`${imported} ${imported === 1 ? config.singular : config.title.toLowerCase()} imported.`)
    },
  })

  function openCreate() {
    if (config.dedicatedEmployeeRoutes) navigate("/app/employees/new")
    else setFormRecord(null)
  }

  function openRecord(record: FoundationRecord) {
    if (config.dedicatedEmployeeRoutes) navigate(`/app/employees/${record.id}`)
    else setFormRecord(record)
  }

  function changeOrdering(key: string) {
    setOrdering((current) => current === key ? `-${key}` : key)
    setPage(1)
  }

  function closeImport() {
    setImportOpen(false)
    setImportFile(null)
    bulkImport.reset()
  }

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div><h2 className="text-2xl font-semibold tracking-tight">{config.title}</h2><p className="mt-1 max-w-3xl text-sm text-muted-foreground">{config.description}</p></div>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            {config.importTemplate ? <Button variant="outline" onClick={() => setImportOpen(true)}><Upload data-icon="inline-start" />Import Excel / CSV</Button> : null}
            <Button onClick={openCreate}><Plus data-icon="inline-start" />New {config.singular}</Button>
          </div>
        ) : null}
      </div>

      <Card>
        <CardHeader className="gap-4 md:flex-row md:items-end md:justify-between">
          <div><CardTitle>Register</CardTitle><CardDescription>{query.data?.pagination.count ?? 0} records</CardDescription></div>
          <form
            className="flex w-full max-w-md gap-2"
            onSubmit={(event) => { event.preventDefault(); setSearch(searchInput); setPage(1) }}
          >
            <Field>
              <FieldLabel htmlFor={`${config.key}-search`} className="sr-only">Search {config.title}</FieldLabel>
              <Input id={`${config.key}-search`} value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={config.searchPlaceholder ?? `Search ${config.title.toLowerCase()}`} />
            </Field>
            <Button type="submit" variant="outline"><Search data-icon="inline-start" />Search</Button>
          </form>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <div className="flex flex-col gap-3">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} className="h-11 w-full" />)}</div>
          ) : query.isError ? (
            <Alert variant="destructive"><AlertTitle>Could not load register</AlertTitle><AlertDescription>{query.error.message}</AlertDescription></Alert>
          ) : query.data.results.length === 0 ? (
            <Empty>
              <EmptyHeader><EmptyMedia variant="icon"><Search /></EmptyMedia><EmptyTitle>No {config.title.toLowerCase()} found</EmptyTitle><EmptyDescription>Adjust the search or create the first record when permitted.</EmptyDescription></EmptyHeader>
              {canManage ? <EmptyContent><Button onClick={openCreate}><Plus data-icon="inline-start" />New {config.singular}</Button></EmptyContent> : null}
            </Empty>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader><TableRow>
                  {config.columns.map((column) => (
                    <TableHead key={column.key}>
                      <Button variant="ghost" size="sm" onClick={() => changeOrdering(column.key)}>
                        {column.label}
                        {ordering.replace("-", "") === column.key ? (ordering.startsWith("-") ? <ArrowDown data-icon="inline-end" /> : <ArrowUp data-icon="inline-end" />) : null}
                      </Button>
                    </TableHead>
                  ))}
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow></TableHeader>
                <TableBody>{query.data.results.map((record) => (
                  <TableRow key={String(record.id)}>
                    {config.columns.map((column) => <TableCell key={column.key}>{displayValue(record[column.key])}</TableCell>)}
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => openRecord(record)}>
                        {canManage && !config.dedicatedEmployeeRoutes ? <Pencil data-icon="inline-start" /> : null}
                        {config.dedicatedEmployeeRoutes ? "Open" : canManage ? "Edit" : "View"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </div>
          )}

          {query.data && query.data.pagination.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <span className="mr-2 text-sm text-muted-foreground">Page {page} of {query.data.pagination.pages}</span>
              <Button aria-label="Previous page" variant="outline" size="icon" disabled={!query.data.pagination.previous} onClick={() => setPage((value) => value - 1)}><ChevronLeft /></Button>
              <Button aria-label="Next page" variant="outline" size="icon" disabled={!query.data.pagination.next} onClick={() => setPage((value) => value + 1)}><ChevronRight /></Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Sheet open={formRecord !== undefined} onOpenChange={(open) => { if (!open) setFormRecord(undefined) }}>
        <SheetContent
          className={cn(
            "axis-erp w-full overflow-x-hidden overflow-y-auto",
            config.key === "roles"
              ? "data-[side=right]:w-[92vw] data-[side=right]:sm:max-w-5xl"
              : "data-[side=right]:sm:max-w-xl",
          )}
        >
          <SheetHeader>
            <SheetTitle>{formRecord ? `Edit ${config.singular}` : `New ${config.singular}`}</SheetTitle>
            <SheetDescription>{config.description}</SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {formRecord !== undefined ? (
              <ResourceRecordForm
                key={formRecord?.id ? String(formRecord.id) : "new"}
                config={config}
                record={formRecord ?? undefined}
                onSuccess={() => setFormRecord(undefined)}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>

      {config.importTemplate ? (
        <Dialog open={importOpen} onOpenChange={(open) => { if (open) setImportOpen(true); else closeImport() }}>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>Import previous {config.title.toLowerCase()}</DialogTitle>
              <DialogDescription>Upload Excel or CSV data exported from your current spreadsheet or Google Sheets.</DialogDescription>
            </DialogHeader>
            <Alert>
              <FileSpreadsheet />
              <AlertTitle>Safe, all-or-nothing import</AlertTitle>
              <AlertDescription>Up to 500 rows and 5 MB. If any row is invalid or already exists, nothing from the file is imported.</AlertDescription>
            </Alert>
            <Field>
              <FieldLabel htmlFor={`${config.key}-import-file`}>CSV or Excel file</FieldLabel>
              <Input id={`${config.key}-import-file`} type="file" accept=".csv,.xlsx" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} />
              <FieldDescription>Required columns: {config.importTemplate.required.join(", ")}.</FieldDescription>
            </Field>
            {config.importTemplate.note ? <p className="text-sm text-muted-foreground">{config.importTemplate.note}</p> : null}
            <Button variant="outline" className="justify-self-start" onClick={() => downloadImportTemplate(config)}><Download data-icon="inline-start" />Download CSV template</Button>
            {bulkImport.isError ? <Alert variant="destructive"><AlertTitle>Data could not be imported</AlertTitle><AlertDescription>{bulkImport.error.message}</AlertDescription></Alert> : null}
            <DialogFooter>
              <Button variant="outline" onClick={closeImport}>Cancel</Button>
              <Button onClick={() => importFile && bulkImport.mutate(importFile)} disabled={!importFile || bulkImport.isPending}>
                {bulkImport.isPending ? <Spinner data-icon="inline-start" /> : <Upload data-icon="inline-start" />}
                {bulkImport.isPending ? "Importing…" : "Import data"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  )
}
