import { useMemo, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronRight,
  ClipboardCheck,
  Inbox,
  Search,
  UserCheck,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

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
} from "@/production/components/shared";
import { apiGet } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { EngineeringReview } from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";

const queues = [
  {
    key: "unassigned",
    label: "Unassigned",
    description: "Needs a Workshop owner",
    icon: Inbox,
  },
  {
    key: "mine",
    label: "My Work",
    description: "Assigned to me",
    icon: UserCheck,
  },
  {
    key: "in_review",
    label: "Team Work",
    description: "Workshop is reviewing",
    icon: ClipboardCheck,
  },
  {
    key: "clarification",
    label: "Needs Attention",
    description: "Waiting for answers",
    icon: AlertTriangle,
  },
  {
    key: "completed",
    label: "Completed",
    description: "Decision history",
    icon: ClipboardCheck,
  },
];

export default function EngineeringPage() {
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const [queue, setQueue] = useState("mine");
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const counts = useQueries({
    queries: queues.map((item) => ({
      queryKey: ["engineering-reviews", "count", item.key],
      queryFn: () =>
        apiGet<Paginated<EngineeringReview>>(
          `/engineering-reviews/?queue=${item.key}&page_size=1`,
        ),
      staleTime: 20_000,
    })),
  });
  const params = useMemo(() => {
    const next = new URLSearchParams({
      queue,
      page: String(page),
      page_size: "25",
    });
    if (search) next.set("search", search);
    return next;
  }, [queue, page, search]);
  const query = useQuery({
    queryKey: ["engineering-reviews", params.toString()],
    queryFn: () =>
      apiGet<Paginated<EngineeringReview>>(`/engineering-reviews/?${params}`),
  });
  if (!hasPermission(user, "engineering.feasibility.view"))
    return (
      <ERPEmptyState
        title="Access restricted"
        description="You do not have permission to view Workshop Reviews."
      />
    );
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Workshop · Daily work"
        title="My Workshop Work"
        description="Review practical requirements, resolve Sales questions, and confirm whether work can proceed."
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {queues.map((item, index) => {
          const Icon = item.icon;
          const active = queue === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => {
                setQueue(item.key);
                setPage(1);
              }}
              className={`rounded-lg border p-4 text-left transition-colors ${active ? "border-primary bg-primary/10" : "bg-card hover:border-primary/40"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <Icon
                  className={active ? "text-primary" : "text-muted-foreground"}
                />
                <span className="text-2xl font-semibold">
                  {counts[index].data?.pagination.count ?? "—"}
                </span>
              </div>
              <p className={`mt-4 font-medium ${active ? "text-primary" : ""}`}>
                {item.label}
              </p>
              <p className="text-xs text-muted-foreground">
                {item.description}
              </p>
            </button>
          );
        })}
      </div>
      <Card>
        <CardHeader className="gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle>
              {queues.find((item) => item.key === queue)?.label}
            </CardTitle>
            <CardDescription>
              {query.data?.pagination.count ?? 0} Workshop Reviews in this
              queue
            </CardDescription>
          </div>
          <form
            className="flex w-full max-w-md gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              setSearch(searchInput);
              setPage(1);
            }}
          >
            <Field>
              <FieldLabel htmlFor="engineering-search" className="sr-only">
                Search Workshop Reviews
              </FieldLabel>
              <Input
                id="engineering-search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Enquiry, customer, subject…"
              />
            </Field>
            <Button type="submit" variant="outline">
              <Search data-icon="inline-start" />
              Search
            </Button>
          </form>
        </CardHeader>
        <CardContent>
          {query.isPending ? (
            <ERPLoadingState rows={8} />
          ) : query.isError ? (
            <ERPErrorState message={query.error.message} />
          ) : !query.data.results.length ? (
            <ERPEmptyState
              title="This queue is clear"
              description="There are no Workshop Reviews matching this queue and search."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Enquiry / customer</TableHead>
                    <TableHead>Review</TableHead>
                    <TableHead>Workshop owner</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Response due</TableHead>
                    <TableHead>Clarifications</TableHead>
                    <TableHead>
                      <span className="sr-only">Open</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {query.data.results.map((review) => (
                    <TableRow
                      key={review.id}
                      className="cursor-pointer"
                      onClick={() =>
                        navigate(`/app/crm/engineering/${review.id}`)
                      }
                    >
                      <TableCell>
                        <p className="font-medium">{review.enquiry_subject}</p>
                        <p className="text-xs text-muted-foreground">
                          {review.enquiry_number} · {review.customer_name}
                        </p>
                      </TableCell>
                      <TableCell>
                        Rev {review.revision_number}
                        {review.is_current ? (
                          <span className="ml-1 text-xs text-primary">
                            Current
                          </span>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        {review.assigned_engineer_name || "Unassigned"}
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge
                          value={review.status}
                          label={review.result || undefined}
                        />
                      </TableCell>
                      <TableCell>
                        <ERPStatusBadge value={review.priority} />
                      </TableCell>
                      <TableCell
                        className={
                          review.due_date &&
                          new Date(review.due_date) < new Date()
                            ? "text-destructive"
                            : ""
                        }
                      >
                        {review.due_date || "Not set"}
                      </TableCell>
                      <TableCell>{review.open_clarifications}</TableCell>
                      <TableCell>
                        <Button
                          aria-label={`Open ${review.enquiry_number} review`}
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
    </div>
  );
}
