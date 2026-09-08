import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { ERPEmptyState, ERPErrorState, ERPStatusBadge } from "@/production/components/shared";
import { apiGet, apiPost, ApiError } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import type { PanelJob } from "@/production/lib/workshop-types";
import type { Paginated } from "@/production/lib/types";

const blankForm = { panel_name: "", panel_reference: "", warehouse_id: "" };

export function PanelJobsCard({ projectId, projectStatus }: { projectId: string; projectStatus: string }) {
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blankForm);

  const jobsQuery = useQuery({
    queryKey: ["panel-jobs", projectId],
    queryFn: () => apiGet<Paginated<PanelJob>>(`/workshop/panel-jobs/?project=${projectId}&ordering=-updated_at`),
  });
  const warehouses = useQuery({
    queryKey: ["panel-job-warehouses"],
    queryFn: () => apiGet<Paginated<{ id: string; name: string }>>("/warehouses/?page_size=100"),
    enabled: open,
  });

  const create = useMutation({
    mutationFn: () =>
      apiPost<PanelJob>(`/projects/${projectId}/create-panel-job/`, {
        panel_name: form.panel_name,
        panel_reference: form.panel_reference,
        warehouse: form.warehouse_id,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["panel-jobs", projectId] });
      setForm(blankForm);
      setOpen(false);
    },
  });

  const canCreate = projectStatus === "ENGINEERING_ACCEPTED" && hasPermission(user, "workshop.panel_job.create");
  const jobs = jobsQuery.data?.results ?? [];

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Boxes className="text-primary" />
            Panel Jobs
          </CardTitle>
          <CardDescription>Workshop execution from requirement review through handover.</CardDescription>
        </div>
        {canCreate ? (
          <Button onClick={() => setOpen(true)}>
            <Plus data-icon="inline-start" />
            Create Panel Job
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {jobsQuery.isError ? (
          <ERPErrorState message={jobsQuery.error.message} />
        ) : !jobs.length ? (
          <ERPEmptyState
            title="No Panel Jobs yet"
            description={
              canCreate
                ? "Create a Panel Job to start Workshop Review and material planning."
                : "A Panel Job can be created once this Project's Workshop handoff is accepted."
            }
          />
        ) : (
          <div className="grid gap-2">
            {jobs.map((job) => (
              <Link
                key={job.id}
                to={`/app/workshop/panel-jobs/${job.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 hover:border-primary/50"
              >
                <div>
                  <p className="font-medium">{job.panel_job_number} · {job.panel_name}</p>
                  <p className="text-xs text-muted-foreground">{job.warehouse_name}</p>
                </div>
                <ERPStatusBadge value={job.status} label={job.status_label} />
              </Link>
            ))}
          </div>
        )}
      </CardContent>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Panel Job</DialogTitle>
            <DialogDescription>Starts Workshop Review for one panel under this Project.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <Field>
              <FieldLabel htmlFor="panel-job-name">Panel name</FieldLabel>
              <Input id="panel-job-name" value={form.panel_name} onChange={(event) => setForm((c) => ({ ...c, panel_name: event.target.value }))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="panel-job-reference">Drawing / reference (optional)</FieldLabel>
              <Input id="panel-job-reference" value={form.panel_reference} onChange={(event) => setForm((c) => ({ ...c, panel_reference: event.target.value }))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="panel-job-warehouse">Workshop warehouse</FieldLabel>
              <NativeSelect id="panel-job-warehouse" value={form.warehouse_id} onChange={(event) => setForm((c) => ({ ...c, warehouse_id: event.target.value }))}>
                <NativeSelectOption value="">Choose warehouse</NativeSelectOption>
                {warehouses.data?.results.map((item) => (
                  <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>
                ))}
              </NativeSelect>
            </Field>
          </div>
          {create.isError ? (
            <ERPErrorState title="Panel Job could not be created" message={create.error instanceof ApiError ? create.error.message : "The request could not be completed."} />
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button disabled={!form.panel_name.trim() || !form.warehouse_id || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? "Creating…" : "Create Panel Job"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
