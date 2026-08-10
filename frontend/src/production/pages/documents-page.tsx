import { useMemo, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FileText, LockKeyhole, Search, ShieldCheck, Upload } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { apiGet, apiUpload } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { ERPDocument, FoundationRecord, Paginated } from "@/production/lib/types"
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPPermissionState,
  ERPStatusBadge,
  formatBytes,
  formatDateTime,
} from "@/production/components/shared"

const allowedExtensions = ["pdf", "png", "jpg", "jpeg", "csv", "docx", "xlsx"]
const maxUploadBytes = 50 * 1024 * 1024

type Category = FoundationRecord & {
  name: string
  code: string
  is_active: boolean
  allowed_extensions: string[]
  max_upload_size_mb: number | null
}

function validateFile(file: File | null, category?: Category) {
  if (!file) return "Choose a file to upload."
  const extension = file.name.split(".").pop()?.toLowerCase() ?? ""
  const allowed = category?.allowed_extensions?.length ? category.allowed_extensions : allowedExtensions
  if (!allowed.includes(extension)) return `Choose a permitted file type: ${allowed.join(", ").toUpperCase()}.`
  const maximum = (category?.max_upload_size_mb ?? 50) * 1024 * 1024
  if (file.size > Math.min(maximum, maxUploadBytes)) return `The file must be ${Math.min(maximum, maxUploadBytes) / 1024 / 1024} MB or smaller.`
  return ""
}

function ERPDocumentUpload({ onUploaded }: { onUploaded: (document: ERPDocument) => void }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [notes, setNotes] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const categories = useQuery({
    queryKey: ["document-categories", "active"],
    queryFn: () => apiGet<Paginated<Category>>("/document-categories/?is_active=true&page_size=100"),
    enabled: open,
  })
  const selectedCategory = categories.data?.results.find((category) => category.id === categoryId)
  const mutation = useMutation({
    mutationFn: () => {
      const error = validateFile(file, selectedCategory)
      setFileError(error)
      if (error || !file) throw new Error(error)
      const body = new FormData()
      body.append("title", title)
      body.append("category", categoryId)
      body.append("notes", notes)
      body.append("file", file)
      return apiUpload<ERPDocument>("/documents/", body)
    },
    onSuccess: (document) => {
      toast.success("Document uploaded successfully.")
      setOpen(false)
      onUploaded(document)
    },
  })

  function chooseFile(nextFile: File | null) {
    setFile(nextFile)
    setFileError(validateFile(nextFile, selectedCategory))
    if (nextFile && !title) setTitle(nextFile.name.replace(/\.[^.]+$/, ""))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button><Upload data-icon="inline-start" />Upload document</Button></DialogTrigger>
      <DialogContent className="axis-erp sm:max-w-xl">
        <form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
          <DialogHeader>
            <DialogTitle>Upload document</DialogTitle>
            <DialogDescription>Add a private file to the controlled document register.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="my-5">
            {mutation.isError && !fileError ? (
              <Alert variant="destructive"><AlertTitle>Upload failed</AlertTitle><AlertDescription>Please try again. If the problem continues, contact your administrator.</AlertDescription></Alert>
            ) : null}
            <Field data-invalid={Boolean(fileError)}>
              <FieldLabel htmlFor="document-file">File</FieldLabel>
              <button
                type="button"
                className="flex min-h-28 w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/30 px-4 text-center transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => inputRef.current?.click()}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files[0] ?? null) }}
              >
                <Upload aria-hidden="true" className="text-primary" />
                <span className="font-medium">{file?.name ?? "Choose file or drag it here"}</span>
                <span className="text-xs text-muted-foreground">PDF, Office files, images or CSV · up to 50 MB</span>
              </button>
              <Input ref={inputRef} id="document-file" type="file" className="sr-only" accept={allowedExtensions.map((item) => `.${item}`).join(",")} onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
              <FieldError>{fileError}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="document-title">Document title</FieldLabel>
              <Input id="document-title" value={title} onChange={(event) => setTitle(event.target.value)} required />
            </Field>
            <Field>
              <FieldLabel htmlFor="document-category">Category</FieldLabel>
              <NativeSelect id="document-category" className="w-full" value={categoryId} onChange={(event) => { setCategoryId(event.target.value); setFileError(validateFile(file, categories.data?.results.find((item) => item.id === event.target.value))) }} required>
                <NativeSelectOption value="">Choose category</NativeSelectOption>
                {categories.data?.results.map((category) => <NativeSelectOption key={category.id} value={category.id}>{category.name}</NativeSelectOption>)}
              </NativeSelect>
              {categories.data?.results.length === 0 ? <FieldDescription>No active category is available. Ask an administrator to configure one.</FieldDescription> : null}
            </Field>
            <Field>
              <FieldLabel htmlFor="document-note">Optional note</FieldLabel>
              <Textarea id="document-note" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Revision purpose or helpful context" />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending || !title || !categoryId || !file}>
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : <Upload data-icon="inline-start" />}
              {mutation.isPending ? "Uploading…" : "Upload"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function ERPDocumentList({ documents, onOpen }: { documents: ERPDocument[]; onOpen: (document: ERPDocument) => void }) {
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <Table>
          <TableHeader><TableRow><TableHead>Document</TableHead><TableHead>Category</TableHead><TableHead>Current version</TableHead><TableHead>Uploaded by</TableHead><TableHead>Updated</TableHead><TableHead>Status</TableHead><TableHead /></TableRow></TableHeader>
          <TableBody>{documents.map((document) => (
            <TableRow key={document.id}>
              <TableCell><div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-md bg-primary/10 text-primary"><FileText /></span><div><p className="font-medium">{document.title}</p><p className="text-xs text-muted-foreground">{document.document_number || document.current_version?.safe_display_filename}</p></div></div></TableCell>
              <TableCell>{document.category_name}</TableCell>
              <TableCell>Version {document.current_version?.version_number ?? "—"} · {formatBytes(document.current_version?.size_bytes)}</TableCell>
              <TableCell>{document.created_by_name}</TableCell>
              <TableCell>{formatDateTime(document.updated_at)}</TableCell>
              <TableCell><ERPStatusBadge value={document.status} /></TableCell>
              <TableCell className="text-right"><Button variant="ghost" size="sm" onClick={() => onOpen(document)}>Open</Button></TableCell>
            </TableRow>
          ))}</TableBody>
        </Table>
      </div>
      <div className="grid gap-3 md:hidden">{documents.map((document) => (
        <button key={document.id} type="button" onClick={() => onOpen(document)} className="rounded-lg border bg-card p-4 text-left shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{document.title}</p><p className="mt-1 text-xs text-muted-foreground">{document.category_name} · Version {document.current_version?.version_number}</p></div><ERPStatusBadge value={document.status} /></div>
          <p className="mt-3 text-xs text-muted-foreground">Updated {formatDateTime(document.updated_at)}</p>
        </button>
      ))}</div>
    </>
  )
}

export default function DocumentsPage() {
  const { data: user } = useCurrentUser()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const canView = hasPermission(user, "documents.document.view")
  const canUpload = hasPermission(user, "documents.document.upload")
  const query = useQuery({
    queryKey: ["documents", search, status],
    queryFn: () => {
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      if (status) params.set("status", status)
      return apiGet<Paginated<ERPDocument>>(`/documents/?${params}`)
    },
    enabled: canView,
  })
  const documents = useMemo(() => query.data?.results ?? [], [query.data])

  if (!canView) return <ERPPermissionState />
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <ERPPageHeader eyebrow="Shared services" title="Documents" description="Private engineering and business files with controlled access, complete version history, and meaningful activity records." actions={canUpload ? <ERPDocumentUpload onUploaded={(document) => { queryClient.invalidateQueries({ queryKey: ["documents"] }); navigate(`/app/documents/${document.id}`) }} /> : undefined} />
      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border bg-card p-4"><p className="text-xs uppercase tracking-wider text-muted-foreground">Available documents</p><p className="mt-1 text-2xl font-semibold">{query.data?.pagination.count ?? "—"}</p></div>
        <div className="rounded-lg border bg-card p-4"><p className="text-xs uppercase tracking-wider text-muted-foreground">Private by design</p><p className="mt-1 flex items-center gap-2 font-semibold"><ShieldCheck className="text-primary" />Backend authorized</p></div>
        <div className="rounded-lg border bg-card p-4"><p className="text-xs uppercase tracking-wider text-muted-foreground">Public file links</p><p className="mt-1 flex items-center gap-2 font-semibold"><LockKeyhole className="text-primary" />None</p></div>
      </section>
      <section className="rounded-xl border bg-card shadow-xs">
        <form className="flex flex-col gap-3 border-b p-4 sm:flex-row" onSubmit={(event) => { event.preventDefault(); setSearch(searchInput) }}>
          <div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input aria-label="Search documents" className="pl-9" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search title, number or filename" /></div>
          <NativeSelect aria-label="Filter by status" className="w-full sm:w-44" value={status} onChange={(event) => setStatus(event.target.value)}><NativeSelectOption value="">All statuses</NativeSelectOption><NativeSelectOption value="ACTIVE">Active</NativeSelectOption><NativeSelectOption value="ARCHIVED">Archived</NativeSelectOption></NativeSelect>
          <Button variant="outline" type="submit">Search</Button>
        </form>
        <div className="p-4">
          {query.isPending ? <ERPLoadingState /> : query.isError ? <ERPErrorState message={query.error.message} /> : documents.length === 0 ? <ERPEmptyState title="No documents yet" description={canUpload ? "Upload the first controlled document." : "No documents are available."} action={canUpload ? <ERPDocumentUpload onUploaded={(document) => navigate(`/app/documents/${document.id}`)} /> : undefined} /> : <ERPDocumentList documents={documents} onOpen={(document) => navigate(`/app/documents/${document.id}`)} />}
        </div>
      </section>
      <p className="text-xs text-muted-foreground"><Badge variant="outline">Scanning status</Badge> Files are validated for type and size. Malware scanning is not yet enabled, so the system does not claim files are virus checked.</p>
    </div>
  )
}
