import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowLeft,
  Download,
  FileClock,
  FileText,
  Link2,
  LockKeyhole,
  RotateCcw,
  Send,
  Upload,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  apiDownload,
  apiGet,
  apiPost,
  apiUpload,
} from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type {
  ApprovalRequest,
  DocumentVersion,
  ERPDocument,
  Paginated,
} from "@/production/lib/types";
import {
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPPermissionState,
  ERPStatusBadge,
  formatBytes,
  formatDateTime,
} from "@/production/components/shared";

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium">{children}</dd>
    </div>
  );
}

type ActiveWorkflow = {
  id: string;
  name: string;
  description: string;
  current_version: string | null;
};

function ApprovalDialog({
  document,
  open,
  onOpenChange,
}: {
  document: ERPDocument;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const [workflowId, setWorkflowId] = useState("");
  const [comment, setComment] = useState("");
  const workflows = useQuery({
    queryKey: ["approval-workflows", "document", document.company],
    queryFn: () =>
      apiGet<Paginated<ActiveWorkflow>>(
        `/approval-workflows/?company=${document.company}&entity_type=document&is_active=true&page_size=100`,
      ),
    enabled: open,
  });
  const activeWorkflows =
    workflows.data?.results.filter((workflow) => workflow.current_version) ??
    [];
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<ApprovalRequest>("/approvals/requests/", {
        workflow_id: workflowId,
        entity_type: "document",
        entity_id: document.id,
        supporting_document_ids: [document.id],
        submission_comment: comment,
      }),
    onSuccess: (request) => {
      toast.success("Document submitted for approval.");
      onOpenChange(false);
      navigate(`/app/approvals/${request.id}`);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Submit for approval</DialogTitle>
          <DialogDescription>
            Choose the approved route for this document. The current version
            will be linked as supporting information.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup className="my-4">
          <Field>
            <FieldLabel htmlFor="approval-workflow">
              Approval workflow
            </FieldLabel>
            <NativeSelect
              id="approval-workflow"
              className="w-full"
              value={workflowId}
              onChange={(event) => setWorkflowId(event.target.value)}
              disabled={workflows.isPending}
            >
              <NativeSelectOption value="">
                {workflows.isPending ? "Loading workflows…" : "Choose workflow"}
              </NativeSelectOption>
              {activeWorkflows.map((workflow) => (
                <NativeSelectOption key={workflow.id} value={workflow.id}>
                  {workflow.name}
                </NativeSelectOption>
              ))}
            </NativeSelect>
            {!workflows.isPending && !activeWorkflows.length ? (
              <FieldError>
                No active document workflow is available. Ask an administrator
                to configure one.
              </FieldError>
            ) : null}
          </Field>
          <Field>
            <FieldLabel htmlFor="approval-comment">
              Message to approver
            </FieldLabel>
            <Textarea
              id="approval-comment"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="What should the approver review?"
            />
          </Field>
          {mutation.isError ? (
            <FieldError>{mutation.error.message}</FieldError>
          ) : null}
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!workflowId || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <Send data-icon="inline-start" />
            )}
            {mutation.isPending ? "Submitting…" : "Submit for approval"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function VersionDialog({
  document,
  open,
  onOpenChange,
}: {
  document: ERPDocument;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a file.");
      const extension = file.name.split(".").pop()?.toLowerCase();
      if (
        !extension ||
        !["pdf", "png", "jpg", "jpeg", "csv", "docx", "xlsx"].includes(
          extension,
        )
      ) {
        setError("Choose a permitted PDF, Office, image, or CSV file.");
        throw new Error("Invalid file");
      }
      if (file.size > 50 * 1024 * 1024) {
        setError("The file must be 50 MB or smaller.");
        throw new Error("File too large");
      }
      const body = new FormData();
      body.append("file", file);
      body.append("notes", notes);
      return apiUpload<DocumentVersion>(
        `/documents/${document.id}/versions/`,
        body,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", document.id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("New document version added.");
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp sm:max-w-lg">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Add new version</DialogTitle>
            <DialogDescription>
              The current file remains in history. This upload becomes the
              latest controlled version.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="my-5">
            <Field data-invalid={Boolean(error)}>
              <FieldLabel htmlFor="new-version-file">File</FieldLabel>
              <Input
                ref={inputRef}
                id="new-version-file"
                type="file"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setError("");
                }}
                required
              />
              <FieldError>{error}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="version-notes">Version notes</FieldLabel>
              <Textarea
                id="version-notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="What changed in this version?"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!file || mutation.isPending}>
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Upload data-icon="inline-start" />
              )}
              {mutation.isPending ? "Uploading…" : "Add version"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function StateDialog({
  document,
  mode,
  open,
  onOpenChange,
}: {
  document: ERPDocument;
  mode: "archive" | "restore";
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      apiPost<ERPDocument>(
        `/documents/${document.id}/${mode}/`,
        mode === "archive" ? { reason } : undefined,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", document.id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success(
        mode === "archive" ? "Document archived." : "Document restored.",
      );
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="axis-erp">
        <DialogHeader>
          <DialogTitle>
            {mode === "archive"
              ? "Archive this document?"
              : "Restore this document?"}
          </DialogTitle>
          <DialogDescription>
            {mode === "archive"
              ? "The file remains in history and can be restored by an authorized user."
              : "The document will return to the active register."}
          </DialogDescription>
        </DialogHeader>
        {mode === "archive" ? (
          <Field className="my-2">
            <FieldLabel htmlFor="archive-reason">Reason</FieldLabel>
            <Textarea
              id="archive-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
            />
          </Field>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={mode === "archive" ? "destructive" : "default"}
            disabled={
              mutation.isPending || (mode === "archive" && !reason.trim())
            }
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : mode === "archive" ? (
              <Archive data-icon="inline-start" />
            ) : (
              <RotateCcw data-icon="inline-start" />
            )}
            {mode === "archive" ? "Archive document" : "Restore document"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const { data: user } = useCurrentUser();
  const [versionOpen, setVersionOpen] = useState(false);
  const [stateOpen, setStateOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const canView = hasPermission(user, "documents.document.view");
  const canDownload = hasPermission(user, "documents.document.download");
  const canVersion = hasPermission(user, "documents.document.version_add");
  const query = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => apiGet<ERPDocument>(`/documents/${documentId}/`),
    enabled: canView,
  });
  const download = useMutation({
    mutationFn: ({
      version,
      current = false,
    }: {
      version: DocumentVersion;
      current?: boolean;
    }) =>
      apiDownload(
        current
          ? `/documents/${documentId}/download/`
          : `/documents/${documentId}/versions/${version.id}/download/`,
        version.safe_display_filename,
      ),
    onError: (error) => toast.error(error.message),
  });

  if (!canView) return <ERPPermissionState />;
  if (query.isPending) return <ERPLoadingState rows={8} />;
  if (query.isError)
    return query.error instanceof ApiError && query.error.status === 403 ? (
      <ERPPermissionState />
    ) : (
      <ERPErrorState message={query.error.message} />
    );
  const document = query.data;
  const canArchive =
    document.status === "ACTIVE" &&
    hasPermission(user, "documents.document.archive");
  const canRestore =
    document.status === "ARCHIVED" &&
    hasPermission(user, "documents.document.restore");
  const canSubmit =
    document.status === "ACTIVE" &&
    hasPermission(user, "approvals.request.submit");
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-5">
      <Button
        variant="ghost"
        className="w-fit"
        render={<Link to="/app/documents" />}
        nativeButton={false}
      >
        <ArrowLeft data-icon="inline-start" />
        Back to documents
      </Button>
      <ERPPageHeader
        eyebrow={`${document.category_name} · Version ${document.current_version?.version_number ?? "—"}`}
        title={document.title}
        description={
          document.description ||
          "Controlled document record with permanent version history."
        }
        actions={
          <>
            {canDownload && document.current_version ? (
              <Button
                variant="outline"
                onClick={() =>
                  download.mutate({
                    version: document.current_version!,
                    current: true,
                  })
                }
              >
                <Download data-icon="inline-start" />
                Download
              </Button>
            ) : null}
            {canSubmit ? (
              <Button variant="outline" onClick={() => setApprovalOpen(true)}>
                <Send data-icon="inline-start" />
                Submit for approval
              </Button>
            ) : null}
            {canVersion && document.status === "ACTIVE" ? (
              <Button onClick={() => setVersionOpen(true)}>
                <Upload data-icon="inline-start" />
                Add new version
              </Button>
            ) : null}
            {canArchive || canRestore ? (
              <Button
                variant={canArchive ? "destructive" : "outline"}
                onClick={() => setStateOpen(true)}
              >
                {canArchive ? (
                  <Archive data-icon="inline-start" />
                ) : (
                  <RotateCcw data-icon="inline-start" />
                )}
                {canArchive ? "Archive" : "Restore"}
              </Button>
            ) : null}
          </>
        }
      />
      <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Document details</CardTitle>
                <CardDescription>
                  Current controlled-file information
                </CardDescription>
              </div>
              <ERPStatusBadge value={document.status} />
            </div>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              <Detail label="Category">{document.category_name}</Detail>
              <Detail label="Current version">
                Version {document.current_version?.version_number ?? "—"}
              </Detail>
              <Detail label="Uploaded by">{document.created_by_name}</Detail>
              <Detail label="Uploaded date">
                {formatDateTime(document.created_at)}
              </Detail>
              <Detail label="File type">
                {document.current_version?.file_extension.toUpperCase() ?? "—"}
              </Detail>
              <Detail label="File size">
                {formatBytes(document.current_version?.size_bytes)}
              </Detail>
              <Detail label="Confidentiality">
                {document.is_confidential ? (
                  <span className="flex items-center gap-2">
                    <LockKeyhole className="text-primary" />
                    Confidential
                  </span>
                ) : (
                  "Standard access"
                )}
              </Detail>
              <Detail label="Validation state">
                Type checked · Not malware scanned
              </Detail>
              <Detail label="Document number">
                {document.document_number || "Not assigned"}
              </Detail>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Related records</CardTitle>
            <CardDescription>Controlled links to ERP records</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {document.links.length ? (
              document.links.map((link) => (
                <div
                  key={link.id}
                  className="flex items-start gap-3 rounded-lg border p-3"
                >
                  <Link2 className="mt-0.5 text-primary" />
                  <div>
                    <p className="font-medium">{link.entity_reference}</p>
                    <p className="text-xs text-muted-foreground">
                      {link.relationship_type.replaceAll("_", " ")} ·{" "}
                      {link.entity_type.replaceAll("_", " ")}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">
                This document is not linked to another record yet.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
      <Card>
        <CardHeader>
          <div className="flex items-start gap-3">
            <span className="grid size-10 place-items-center rounded-md bg-primary/10 text-primary">
              <FileClock />
            </span>
            <div>
              <CardTitle>Version history</CardTitle>
              <CardDescription>
                Earlier files remain available and auditable.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version</TableHead>
                <TableHead>Filename</TableHead>
                <TableHead>Uploaded by</TableHead>
                <TableHead>Uploaded at</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>File state</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {document.versions.map((version) => (
                <TableRow key={version.id}>
                  <TableCell>
                    <Badge
                      variant={
                        version.id === document.current_version?.id
                          ? "default"
                          : "outline"
                      }
                    >
                      Version {version.version_number}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <FileText className="text-primary" />
                      {version.safe_display_filename}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {formatBytes(version.size_bytes)}
                    </span>
                  </TableCell>
                  <TableCell>{version.uploaded_by_name}</TableCell>
                  <TableCell>{formatDateTime(version.uploaded_at)}</TableCell>
                  <TableCell>{version.notes || "—"}</TableCell>
                  <TableCell>
                    {version.scan_status === "NOT_SCANNED"
                      ? "Not malware scanned"
                      : version.scan_status.replaceAll("_", " ")}
                  </TableCell>
                  <TableCell>
                    {canDownload ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => download.mutate({ version })}
                      >
                        <Download data-icon="inline-start" />
                        Download
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      {document.status === "ARCHIVED" ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
          <p className="font-semibold">
            Archived {formatDateTime(document.archived_at)}
          </p>
          <p className="mt-1 text-muted-foreground">
            {document.archive_reason}
          </p>
        </div>
      ) : null}
      <VersionDialog
        document={document}
        open={versionOpen}
        onOpenChange={setVersionOpen}
      />
      <StateDialog
        document={document}
        mode={canArchive ? "archive" : "restore"}
        open={stateOpen}
        onOpenChange={setStateOpen}
      />
      <ApprovalDialog
        document={document}
        open={approvalOpen}
        onOpenChange={setApprovalOpen}
      />
    </div>
  );
}
