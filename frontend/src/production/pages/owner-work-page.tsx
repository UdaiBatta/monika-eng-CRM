import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowUpRight, ListChecks, UserRoundCog } from "lucide-react"
import { Link, useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { ERPErrorState, ERPLoadingState, formatDateTime } from "@/production/components/shared"
import { apiGet, apiPost } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { OwnerEmployee, OwnerWorkItem, OwnerWorkResponse } from "@/production/lib/owner-types"

const workTypes = [
  ["", "All work"],
  ["incoming_enquiry", "Incoming enquiries"],
  ["enquiry", "Enquiries"],
  ["engineering_review", "Workshop Reviews"],
  ["quotation", "Quotations"],
  ["customer_po", "Customer POs"],
  ["sales_order", "Sales orders"],
  ["project_engineering", "Project Workshop work"],
]

const workKey = (item: OwnerWorkItem) => `${item.work_type}:${item.id}`

export default function OwnerWorkPage() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const queue = searchParams.get("queue") ?? ""
  const workType = searchParams.get("work_type") ?? ""
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [dialogItems, setDialogItems] = useState<OwnerWorkItem[]>([])
  const [employeeId, setEmployeeId] = useState("")
  const [reason, setReason] = useState("")
  const canReassign = hasPermission(user, "system.work.reassign")
  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), page_size: "25" })
    if (queue) next.set("queue", queue)
    if (workType) next.set("work_type", workType)
    return next
  }, [page, queue, workType])
  const work = useQuery({
    queryKey: ["owner-work", params.toString()],
    queryFn: () => apiGet<OwnerWorkResponse>(`/owner/work-items/?${params}`),
  })
  const employees = useQuery({
    queryKey: ["owner-employees"],
    queryFn: () => apiGet<OwnerEmployee[]>("/owner/employees/"),
    enabled: canReassign,
  })
  const records = work.data?.results ?? []
  const selectedRecords = records.filter((item) => selected.has(workKey(item)))
  const reassign = useMutation({
    mutationFn: () => apiPost<{ reassigned: number }>("/owner/reassign-work/", {
      items: dialogItems.map((item) => ({ work_type: item.work_type, id: item.id })),
      employee_id: employeeId,
      reason,
    }),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["owner-work"] }),
        queryClient.invalidateQueries({ queryKey: ["owner"] }),
        queryClient.invalidateQueries({ queryKey: ["owner-data-quality"] }),
      ])
      toast.success(
        result.reassigned
          ? `${result.reassigned} work item${result.reassigned === 1 ? "" : "s"} reassigned.`
          : "That work was already assigned to this employee.",
      )
      setSelected(new Set())
      closeDialog()
    },
  })

  function setFilter(name: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next, { replace: true })
    setPage(1)
    setSelected(new Set())
  }

  function openDialog(items: OwnerWorkItem[]) {
    setDialogItems(items)
    setEmployeeId("")
    setReason("")
  }

  function closeDialog() {
    setDialogItems([])
    setEmployeeId("")
    setReason("")
    reassign.reset()
  }

  function toggle(item: OwnerWorkItem, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current)
      if (checked) next.add(workKey(item))
      else next.delete(workKey(item))
      return next
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <Card size="sm">
        <CardHeader><CardTitle>Work assignment</CardTitle><CardDescription>See who is responsible and safely move open work when somebody is unavailable. Completed history is never reassigned.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field><FieldLabel htmlFor="owner-work-type">Work type</FieldLabel><NativeSelect id="owner-work-type" value={workType} onChange={(event) => setFilter("work_type", event.target.value)}>{workTypes.map(([value, label]) => <NativeSelectOption key={value || "all"} value={value}>{label}</NativeSelectOption>)}</NativeSelect></Field>
            <Field><FieldLabel htmlFor="owner-work-queue">Responsibility</FieldLabel><NativeSelect id="owner-work-queue" value={queue} onChange={(event) => setFilter("queue", event.target.value)}><NativeSelectOption value="">All open work</NativeSelectOption><NativeSelectOption value="unassigned">Unassigned</NativeSelectOption><NativeSelectOption value="inactive">Assigned to inactive employee</NativeSelectOption></NativeSelect></Field>
          </div>
          {canReassign ? <Button disabled={!selectedRecords.length} onClick={() => openDialog(selectedRecords)}><UserRoundCog data-icon="inline-start" />Reassign selected ({selectedRecords.length})</Button> : null}
        </CardContent>
      </Card>

      {!canReassign ? <Alert><ListChecks /><AlertTitle>View only</AlertTitle><AlertDescription>Your role can review responsibility but cannot move work.</AlertDescription></Alert> : null}
      {work.isPending ? <ERPLoadingState rows={8} /> : work.isError ? <ERPErrorState title="Work assignments could not load" message={work.error.message} /> : !records.length ? (
        <Card size="sm"><CardHeader><CardTitle>No matching open work</CardTitle><CardDescription>There is nothing to reassign for these filters.</CardDescription></CardHeader></Card>
      ) : (
        <Card>
          <CardContent className="px-0">
            <div className="hidden overflow-x-auto md:block">
              <Table>
                <TableHeader><TableRow>{canReassign ? <TableHead className="w-12"><span className="sr-only">Select</span></TableHead> : null}<TableHead>Work</TableHead><TableHead>Status</TableHead><TableHead>Responsible</TableHead><TableHead>Last updated</TableHead><TableHead><span className="sr-only">Actions</span></TableHead></TableRow></TableHeader>
                <TableBody>{records.map((item) => <TableRow key={workKey(item)}>{canReassign ? <TableCell><Checkbox aria-label={`Select ${item.reference}`} checked={selected.has(workKey(item))} onCheckedChange={(checked) => toggle(item, checked === true)} /></TableCell> : null}<TableCell><p className="font-medium">{item.reference}</p><p className="text-xs text-muted-foreground">{item.work_type_label} · {item.title}</p></TableCell><TableCell><Badge variant="outline">{item.status}</Badge></TableCell><TableCell>{item.assigned_to_name}</TableCell><TableCell>{formatDateTime(item.updated_at)}</TableCell><TableCell><div className="flex justify-end gap-2">{canReassign ? <Button variant="outline" size="sm" onClick={() => openDialog([item])}>Reassign</Button> : null}<Button variant="ghost" size="icon" aria-label={`Open ${item.reference}`} nativeButton={false} render={<Link to={item.action_url} />}><ArrowUpRight /></Button></div></TableCell></TableRow>)}</TableBody>
              </Table>
            </div>
            <div className="grid gap-3 p-4 md:hidden">{records.map((item) => <div key={workKey(item)} className="rounded-lg border p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{item.reference}</p><p className="text-xs text-muted-foreground">{item.work_type_label}</p></div><Badge variant="outline">{item.status}</Badge></div><p className="mt-3 text-sm">{item.title}</p><p className="mt-1 text-xs text-muted-foreground">Responsible: {item.assigned_to_name}</p><div className="mt-4 flex gap-2">{canReassign ? <Button variant="outline" size="sm" onClick={() => openDialog([item])}>Reassign</Button> : null}<Button variant="ghost" size="sm" nativeButton={false} render={<Link to={item.action_url} />}>Open<ArrowUpRight data-icon="inline-end" /></Button></div></div>)}</div>
          </CardContent>
        </Card>
      )}

      {work.data && work.data.pagination.pages > 1 ? <div className="flex justify-end gap-3"><Button variant="outline" disabled={!work.data.pagination.previous} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="self-center text-sm text-muted-foreground">Page {page} of {work.data.pagination.pages}</span><Button variant="outline" disabled={!work.data.pagination.next} onClick={() => setPage((value) => value + 1)}>Next</Button></div> : null}

      <Dialog open={dialogItems.length > 0} onOpenChange={(open) => { if (!open) closeDialog() }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Reassign {dialogItems.length} open work item{dialogItems.length === 1 ? "" : "s"}</DialogTitle><DialogDescription>The selected records will move together. Completed records and historical activity are not changed.</DialogDescription></DialogHeader>
          <FieldGroup>
            <Field><FieldLabel htmlFor="replacement-employee">New responsible employee</FieldLabel><NativeSelect id="replacement-employee" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}><NativeSelectOption value="">Choose an active employee</NativeSelectOption>{employees.data?.map((employee) => <NativeSelectOption key={employee.id} value={employee.id}>{employee.employee_code} · {employee.display_name}</NativeSelectOption>)}</NativeSelect></Field>
            <Field><FieldLabel htmlFor="reassignment-reason">Why is this work moving?</FieldLabel><Textarea id="reassignment-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="For example: covering planned leave until 26 August" /><FieldDescription>This reason appears in Activity history.</FieldDescription></Field>
            {reassign.isError ? <Alert variant="destructive"><AlertTitle>Work could not be reassigned</AlertTitle><AlertDescription>{reassign.error.message}</AlertDescription></Alert> : null}
          </FieldGroup>
          <DialogFooter><Button variant="outline" onClick={closeDialog}>Cancel</Button><Button disabled={!employeeId || reason.trim().length < 3 || reassign.isPending} onClick={() => reassign.mutate()}>{reassign.isPending ? <Spinner data-icon="inline-start" /> : <UserRoundCog data-icon="inline-start" />}{reassign.isPending ? "Reassigning…" : "Confirm reassignment"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
