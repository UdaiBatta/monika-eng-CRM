import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  ClipboardList,
  Plus,
  Search,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EnquiryForm } from "@/production/components/enquiry-forms";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
} from "@/production/components/shared";
import SpreadsheetImport from "@/production/components/spreadsheet-import";
import { apiGet } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { Enquiry } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

const enquiryImport = {
  headers: [
    "company_code",
    "customer_code",
    "subject",
    "customer_reference",
    "received_date",
    "due_date",
    "priority",
    "responsible_salesperson_code",
    "estimated_value",
    "currency_code",
    "source",
    "description",
  ],
  required: [
    "company_code",
    "customer_code",
    "subject",
    "received_date",
    "responsible_salesperson_code",
  ],
  example: [
    "ME",
    "CUS-0001",
    "MCC control panel",
    "RFQ-431",
    "2026-08-10",
    "2026-08-20",
    "HIGH",
    "ME-001",
    "1875000",
    "INR",
    "Existing spreadsheet",
    "Design and manufacture as per customer RFQ.",
  ],
};

function money(amount: string | null, currency: string) {
  if (!amount) return "—";
  return `${currency || "₹"} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(amount))}`;
}

export default function EnquiriesPage() {
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [due, setDue] = useState("");
  const [showForm, setShowForm] = useState(false);
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    if (priority) next.set("priority", priority);
    if (due) next.set("due", due);
    return next;
  }, [page, search, status, priority, due]);
  const query = useQuery({
    queryKey: ["enquiries", params.toString()],
    queryFn: () => apiGet<Paginated<Enquiry>>(`/enquiries/?${params}`),
  });
  const canCreate = hasPermission(user, "enquiry.enquiry.create");
  const openForm = () => setShowForm(true);
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM"
        title="Enquiries & RFQs"
        description="Qualify customer requirements, control response dates, and send complete scopes to Workshop Review."
        actions={
          canCreate ? (
            <>
              <SpreadsheetImport
                endpoint="/enquiries/import-history/"
                label="enquiries"
                templateName="enquiries"
                headers={enquiryImport.headers}
                required={enquiryImport.required}
                example={enquiryImport.example}
                queryKey={["enquiries"]}
                note="Customers and employees must already exist. Use YYYY-MM-DD for dates."
              />
              <Button onClick={openForm}>
                <Plus data-icon="inline-start" />
                New enquiry
              </Button>
            </>
          ) : undefined
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              All in view
            </p>
            <p className="mt-2 text-2xl font-semibold">
              {query.data?.pagination.count ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Workflow focus
            </p>
            <p className="mt-2 text-lg font-semibold">
              Commercial → Workshop
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Estimation
            </p>
            <p className="mt-2 text-lg font-semibold text-muted-foreground">
              Gated until feasible
            </p>
          </CardContent>
        </Card>
        <Card className="border-primary/25">
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Milestone boundary
            </p>
            <p className="mt-2 text-lg font-semibold text-primary">
              Ready for Estimation
            </p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <CardTitle>Enquiry register</CardTitle>
            <CardDescription>
              Dense operational view of open and closed customer requests.
            </CardDescription>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-[minmax(220px,1fr)_180px_140px_150px] xl:max-w-4xl">
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(searchInput);
                setPage(1);
              }}
            >
              <Field>
                <FieldLabel htmlFor="enquiry-search" className="sr-only">
                  Search enquiries
                </FieldLabel>
                <Input
                  id="enquiry-search"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Number, customer, RFQ…"
                />
              </Field>
              <Button type="submit" variant="outline">
                <Search data-icon="inline-start" />
                Search
              </Button>
            </form>
            <Field>
              <FieldLabel htmlFor="enquiry-status-filter" className="sr-only">
                Stage
              </FieldLabel>
              <NativeSelect
                id="enquiry-status-filter"
                className="w-full"
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All stages</NativeSelectOption>
                <NativeSelectOption value="DRAFT">Draft</NativeSelectOption>
                <NativeSelectOption value="RECEIVED">
                  Received
                </NativeSelectOption>
                <NativeSelectOption value="UNDER_REVIEW">
                  Under review
                </NativeSelectOption>
              <NativeSelectOption value="ENGINEERING_REVIEW">
                  Workshop Review
                </NativeSelectOption>
                <NativeSelectOption value="WON">Won</NativeSelectOption>
                <NativeSelectOption value="LOST">Lost</NativeSelectOption>
                <NativeSelectOption value="CANCELLED">
                  Cancelled
                </NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="enquiry-priority-filter" className="sr-only">
                Priority
              </FieldLabel>
              <NativeSelect
                id="enquiry-priority-filter"
                className="w-full"
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
            <Field>
              <FieldLabel htmlFor="enquiry-due-filter" className="sr-only">
                Due
              </FieldLabel>
              <NativeSelect
                id="enquiry-due-filter"
                className="w-full"
                value={due}
                onChange={(event) => {
                  setDue(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">Any due date</NativeSelectOption>
                <NativeSelectOption value="overdue">Overdue</NativeSelectOption>
                <NativeSelectOption value="today">Due today</NativeSelectOption>
              </NativeSelect>
            </Field>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <ERPLoadingState rows={8} />
          ) : query.isError ? (
            <ERPErrorState message={query.error.message} />
          ) : !query.data.results.length ? (
            <ERPEmptyState
              title="No enquiries found"
              description="Adjust the filters or create the first customer enquiry."
              action={
                canCreate ? (
                  <Button onClick={openForm}>New enquiry</Button>
                ) : undefined
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Enquiry</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Response due</TableHead>
                    <TableHead>Indicative value</TableHead>
                    <TableHead>Sales owner</TableHead>
                    <TableHead>
                      <span className="sr-only">Open</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {query.data.results.map((enquiry) => (
                    <TableRow
                      key={enquiry.id}
                      className="cursor-pointer"
                      onClick={() =>
                        navigate(`/app/crm/enquiries/${enquiry.id}`)
                      }
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <span className="grid size-9 place-items-center rounded-md border bg-muted text-primary">
                            <ClipboardList />
                          </span>
                          <div>
                            <p className="font-medium">{enquiry.subject}</p>
                            <p className="text-xs text-muted-foreground">
                              {enquiry.enquiry_number}
                              {enquiry.customer_reference
                                ? ` · ${enquiry.customer_reference}`
                                : ""}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{enquiry.customer_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {enquiry.customer_code}
                        </p>
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={enquiry.status} />
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={enquiry.priority} />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {enquiry.is_overdue ? (
                            <AlertTriangle className="text-destructive" />
                          ) : (
                            <CalendarDays className="text-muted-foreground" />
                          )}
                          <span
                            className={
                              enquiry.is_overdue
                                ? "font-medium text-destructive"
                                : ""
                            }
                          >
                            {enquiry.due_date || "Not set"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {money(enquiry.estimated_value, enquiry.currency_code)}
                      </TableCell>
                      <TableCell>
                        {enquiry.responsible_salesperson_name}
                      </TableCell>
                      <TableCell>
                        <Button
                          aria-label={`Open ${enquiry.enquiry_number}`}
                          variant="ghost"
                          size="icon"
                        >
                          <ChevronRight />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {query.data && query.data.pagination.pages > 1 ? (
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                disabled={!query.data.pagination.previous}
                onClick={() => setPage((value) => value - 1)}
              >
                Previous
              </Button>
              <span className="self-center text-sm text-muted-foreground">
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
      <Sheet open={showForm} onOpenChange={setShowForm}>
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>New enquiry / RFQ</SheetTitle>
            <SheetDescription>
              Create a draft with a clear customer scope. Requirements and items
              can be completed in the workspace.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <EnquiryForm
              initialCustomerId={searchParams.get("customer") ?? ""}
              onSaved={(saved) => navigate(`/app/crm/enquiries/${saved.id}`)}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
