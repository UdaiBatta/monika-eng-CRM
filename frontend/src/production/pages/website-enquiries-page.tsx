import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Building2,
  Clock3,
  Globe2,
  Mail,
  Search,
  ShieldCheck,
  UserRoundCheck,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatDateTime,
} from "@/production/components/shared";
import { apiGet } from "@/production/lib/api";
import type { ExternalEnquirySubmission } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

function sourceLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (letter) => letter.toUpperCase());
}

function SubmissionIdentity({ item }: { item: ExternalEnquirySubmission }) {
  return (
    <div className="min-w-0">
      <p className="truncate font-medium">{item.company_name || item.person_name}</p>
      <p className="truncate text-xs text-muted-foreground">
        {item.person_name}
        {item.email ? ` · ${item.email}` : item.phone ? ` · ${item.phone}` : ""}
      </p>
    </div>
  );
}

export default function WebsiteEnquiriesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [priority, setPriority] = useState("");
  const params = useMemo(() => {
    const next = new URLSearchParams({
      page: String(page),
      page_size: "25",
      ordering: "-received_at",
    });
    if (search) next.set("search", search);
    if (status) next.set("review_status", status);
    if (source) next.set("source_type", source);
    if (priority) next.set("priority", priority);
    return next;
  }, [page, priority, search, source, status]);
  const query = useQuery({
    queryKey: ["website-enquiries", params.toString()],
    queryFn: () =>
      apiGet<Paginated<ExternalEnquirySubmission>>(
        `/external-enquiries/?${params}`,
      ),
  });
  const visible = query.data?.results ?? [];
  const newCount = visible.filter((item) => item.review_status === "NEW").length;
  const duplicateCount = visible.filter(
    (item) => item.duplicate_status === "POSSIBLE",
  ).length;
  const assignedCount = visible.filter((item) => item.assigned_to).length;

  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM · Digital intake"
        title="Website enquiry inbox"
        description="A secure review queue for contact forms and product RFQs received from monikaengineers.co.in before they enter the controlled CRM workflow."
        actions={
          <Badge variant="outline" className="gap-2 px-3 py-2 text-xs">
            <ShieldCheck className="size-4 text-status-success" />
            Signed integration active
          </Badge>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="overflow-hidden border-primary/30">
          <CardContent className="relative p-4">
            <Globe2 className="absolute right-4 top-4 size-8 text-primary/20" />
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Total received
            </p>
            <p className="mt-2 text-2xl font-semibold">
              {query.data?.pagination.count ?? 0}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Current filtered queue</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              New on this page
            </p>
            <p className="mt-2 text-2xl font-semibold text-status-info">{newCount}</p>
            <p className="mt-1 text-xs text-muted-foreground">Awaiting first review</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Possible duplicates
            </p>
            <p className="mt-2 text-2xl font-semibold text-status-warning">
              {duplicateCount}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Customer match review</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Assigned on this page
            </p>
            <p className="mt-2 text-2xl font-semibold">{assignedCount}</p>
            <p className="mt-1 text-xs text-muted-foreground">Owned by a sales user</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <CardTitle>Incoming requests</CardTitle>
            <CardDescription>
              Review identity, provenance, duplicate signals, and ownership before conversion.
            </CardDescription>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-2 xl:max-w-4xl xl:grid-cols-[minmax(250px,1fr)_180px_170px_140px]">
            <form
              className="flex gap-2 sm:col-span-2 xl:col-span-1"
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(searchInput);
                setPage(1);
              }}
            >
              <Field>
                <FieldLabel htmlFor="website-enquiry-search" className="sr-only">
                  Search website enquiries
                </FieldLabel>
                <Input
                  id="website-enquiry-search"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Company, person, email, subject…"
                />
              </Field>
              <Button type="submit" variant="outline">
                <Search data-icon="inline-start" />
                Search
              </Button>
            </form>
            <Field>
              <FieldLabel htmlFor="website-status" className="sr-only">
                Review status
              </FieldLabel>
              <NativeSelect
                id="website-status"
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All review states</NativeSelectOption>
                <NativeSelectOption value="NEW">New</NativeSelectOption>
                <NativeSelectOption value="NEEDS_REVIEW">Needs review</NativeSelectOption>
                <NativeSelectOption value="POSSIBLE_DUPLICATE">Possible duplicate</NativeSelectOption>
                <NativeSelectOption value="CONVERTED">Converted</NativeSelectOption>
                <NativeSelectOption value="REJECTED">Rejected</NativeSelectOption>
                <NativeSelectOption value="SPAM">Spam</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="website-source" className="sr-only">
                Source type
              </FieldLabel>
              <NativeSelect
                id="website-source"
                value={source}
                onChange={(event) => {
                  setSource(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All source types</NativeSelectOption>
                <NativeSelectOption value="CONTACT_FORM">Contact form</NativeSelectOption>
                <NativeSelectOption value="PRODUCT_QUOTE">Product RFQ</NativeSelectOption>
                <NativeSelectOption value="CAMPAIGN">Campaign</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="website-priority" className="sr-only">
                Priority
              </FieldLabel>
              <NativeSelect
                id="website-priority"
                value={priority}
                onChange={(event) => {
                  setPriority(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All priorities</NativeSelectOption>
                <NativeSelectOption value="URGENT">Urgent</NativeSelectOption>
                <NativeSelectOption value="HIGH">High</NativeSelectOption>
                <NativeSelectOption value="NORMAL">Normal</NativeSelectOption>
                <NativeSelectOption value="LOW">Low</NativeSelectOption>
              </NativeSelect>
            </Field>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <ERPLoadingState rows={8} />
          ) : query.isError ? (
            <ERPErrorState message={query.error.message} />
          ) : !visible.length ? (
            <ERPEmptyState
              title="No website enquiries found"
              description="New signed website submissions will appear here for controlled CRM review."
            />
          ) : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Received</TableHead>
                      <TableHead>Person / company</TableHead>
                      <TableHead>Request</TableHead>
                      <TableHead>Review</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Owner</TableHead>
                      <TableHead><span className="sr-only">Open</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visible.map((item) => (
                      <TableRow
                        key={item.id}
                        className="cursor-pointer"
                        onClick={() => navigate(`/app/crm/website-enquiries/${item.id}`)}
                      >
                        <TableCell className="whitespace-nowrap">
                          <p className="font-medium">{formatDateTime(item.received_at)}</p>
                          <p className="text-xs text-muted-foreground">
                            {sourceLabel(item.source_type)}
                          </p>
                        </TableCell>
                        <TableCell><SubmissionIdentity item={item} /></TableCell>
                        <TableCell className="max-w-sm">
                          <p className="truncate font-medium">{item.subject}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {item.product_name || item.message}
                          </p>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col items-start gap-1">
                            <ERPStatusBadge value={item.review_status} />
                            {item.duplicate_status === "POSSIBLE" ? (
                              <Badge variant="outline" className="text-[10px] text-status-warning">
                                Possible match
                              </Badge>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell><ERPStatusBadge value={item.priority} /></TableCell>
                        <TableCell>{item.assigned_to_name || "Unassigned"}</TableCell>
                        <TableCell>
                          <Button
                            aria-label={`Review ${item.external_submission_id}`}
                            variant="ghost"
                            size="icon"
                          >
                            <ArrowUpRight />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="grid gap-3 md:hidden">
                {visible.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => navigate(`/app/crm/website-enquiries/${item.id}`)}
                    className="rounded-lg border p-4 text-left transition-colors hover:border-primary/40 hover:bg-muted/40"
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <SubmissionIdentity item={item} />
                      <ERPStatusBadge value={item.review_status} />
                    </div>
                    <p className="font-medium">{item.subject}</p>
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><Clock3 className="size-3" />{formatDateTime(item.received_at)}</span>
                      <span className="flex items-center gap-1"><Mail className="size-3" />{sourceLabel(item.source_type)}</span>
                      <span className="flex items-center gap-1"><UserRoundCheck className="size-3" />{item.assigned_to_name || "Unassigned"}</span>
                      {item.company_name ? <span className="flex items-center gap-1"><Building2 className="size-3" />{item.company_name}</span> : null}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {query.data && query.data.pagination.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-3">
              <Button
                variant="outline"
                disabled={!query.data.pagination.previous}
                onClick={() => setPage((value) => value - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {query.data.pagination.pages}
              </span>
              <Button
                variant="outline"
                disabled={!query.data.pagination.next}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
