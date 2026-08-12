import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock3, Plus, Search, X } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

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
import { ActivityForm } from "@/production/components/crm-forms";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatDateTime,
} from "@/production/components/shared";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { CrmActivity } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

export default function ActivitiesPage() {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("OPEN");
  const [activityType, setActivityType] = useState("");
  const [mine, setMine] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25" });
    if (search) next.set("search", search);
    if (status) next.set("status", status);
    if (activityType) next.set("activity_type", activityType);
    if (mine) next.set("mine", "true");
    return next;
  }, [page, search, status, activityType, mine]);
  const query = useQuery({
    queryKey: ["crm-activities", params.toString()],
    queryFn: () => apiGet<Paginated<CrmActivity>>(`/crm-activities/?${params}`),
  });
  const command = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "complete" | "cancel";
    }) => apiPost(`/crm-activities/${id}/${action}/`, {}),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["crm-activities"] });
      toast.success(
        variables.action === "complete"
          ? "Follow-up completed."
          : "Follow-up cancelled.",
      );
    },
  });
  const canCreate = hasPermission(user, "crm.activity.create");
  const canComplete = hasPermission(user, "crm.activity.complete");
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Commercial CRM"
        title="Activities & follow-ups"
        description="A working queue for customer conversations, commitments, and due next actions."
        actions={
          canCreate ? (
            <Button onClick={() => setShowForm(true)}>
              <Plus data-icon="inline-start" />
              Record activity
            </Button>
          ) : undefined
        }
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Queue view
            </p>
            <p className="mt-2 text-xl font-semibold">
              {mine ? "My follow-ups" : "Team follow-ups"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Records in view
            </p>
            <p className="mt-2 text-xl font-semibold">
              {query.data?.pagination.count ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Local time
            </p>
            <p className="mt-2 text-xl font-semibold">Asia / Kolkata</p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader className="gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <CardTitle>Action queue</CardTitle>
            <CardDescription>
              Prioritize overdue and high-priority commitments first.
            </CardDescription>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-[minmax(220px,1fr)_160px_170px_auto] xl:max-w-4xl">
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(searchInput);
                setPage(1);
              }}
            >
              <Field>
                <FieldLabel htmlFor="activity-search" className="sr-only">
                  Search activities
                </FieldLabel>
                <Input
                  id="activity-search"
                  placeholder="Customer, subject, contact…"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                />
              </Field>
              <Button variant="outline" type="submit">
                <Search data-icon="inline-start" />
                Search
              </Button>
            </form>
            <Field>
              <FieldLabel htmlFor="activity-status" className="sr-only">
                Status
              </FieldLabel>
              <NativeSelect
                id="activity-status"
                className="w-full"
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">All statuses</NativeSelectOption>
                <NativeSelectOption value="OPEN">Open</NativeSelectOption>
                <NativeSelectOption value="COMPLETED">
                  Completed
                </NativeSelectOption>
                <NativeSelectOption value="CANCELLED">
                  Cancelled
                </NativeSelectOption>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="activity-kind" className="sr-only">
                Activity type
              </FieldLabel>
              <NativeSelect
                id="activity-kind"
                className="w-full"
                value={activityType}
                onChange={(event) => {
                  setActivityType(event.target.value);
                  setPage(1);
                }}
              >
                <NativeSelectOption value="">
                  All activity types
                </NativeSelectOption>
                <NativeSelectOption value="FOLLOW_UP">
                  Follow-ups
                </NativeSelectOption>
                <NativeSelectOption value="CALL">Calls</NativeSelectOption>
                <NativeSelectOption value="EMAIL">Emails</NativeSelectOption>
                <NativeSelectOption value="MEETING">
                  Meetings
                </NativeSelectOption>
                <NativeSelectOption value="SITE_VISIT">
                  Site visits
                </NativeSelectOption>
                <NativeSelectOption value="NOTE">Notes</NativeSelectOption>
              </NativeSelect>
            </Field>
            <Button
              variant={mine ? "secondary" : "outline"}
              onClick={() => {
                setMine((value) => !value);
                setPage(1);
              }}
            >
              Mine only
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <ERPLoadingState rows={8} />
          ) : query.isError ? (
            <ERPErrorState message={query.error.message} />
          ) : !query.data.results.length ? (
            <ERPEmptyState
              title="No activities found"
              description="Adjust the filters or record the next customer interaction."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Due / activity date</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {query.data.results.map((activity) => (
                    <TableRow
                      key={activity.id}
                      className={activity.is_overdue ? "bg-destructive/5" : ""}
                    >
                      <TableCell className="whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Clock3
                            className={
                              activity.is_overdue
                                ? "text-destructive"
                                : "text-muted-foreground"
                            }
                          />
                          <div>
                            <p
                              className={
                                activity.is_overdue
                                  ? "font-medium text-destructive"
                                  : ""
                              }
                            >
                              {formatDateTime(
                                activity.next_follow_up_at ??
                                  activity.activity_date,
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {activity.is_overdue
                                ? "Overdue"
                                : activity.activity_type.replaceAll("_", " ")}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link
                          className="font-medium hover:text-primary"
                          to={`/app/crm/customers/${activity.customer}`}
                        >
                          {activity.customer_name}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {activity.customer_code}
                        </p>
                      </TableCell>
                      <TableCell>
                        <p className="max-w-[360px] truncate font-medium">
                          {activity.subject}
                        </p>
                        <p className="max-w-[360px] truncate text-xs text-muted-foreground">
                          {activity.description}
                        </p>
                      </TableCell>
                      <TableCell>
                        {activity.follow_up_owner_name ||
                          activity.created_by_name}
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={activity.priority} />
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={activity.status} />
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          {activity.status === "OPEN" && canComplete ? (
                            <Button
                              aria-label={`Complete ${activity.subject}`}
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                command.mutate({
                                  id: activity.id,
                                  action: "complete",
                                })
                              }
                            >
                              <Check />
                            </Button>
                          ) : null}
                          {activity.status === "OPEN" &&
                          hasPermission(user, "crm.activity.edit") ? (
                            <Button
                              aria-label={`Cancel ${activity.subject}`}
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                command.mutate({
                                  id: activity.id,
                                  action: "cancel",
                                })
                              }
                            >
                              <X />
                            </Button>
                          ) : null}
                        </div>
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
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>Record customer activity</SheetTitle>
            <SheetDescription>
              Capture the interaction and schedule the next action when
              required.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <ActivityForm onSaved={() => setShowForm(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
