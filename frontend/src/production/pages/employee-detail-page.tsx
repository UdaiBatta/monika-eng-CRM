import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Building2, CalendarDays, Mail, Pencil, Phone, UserCheck, UserRound, UserX } from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { apiGet, apiPost } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { OwnerEmployee, OwnerWorkItem } from "@/production/lib/owner-types"
import type { FoundationRecord } from "@/production/lib/types"

function Detail({ label, value }: { label: string; value: unknown }) {
  return <div><p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value ? String(value).replaceAll("_", " ") : "—"}</p></div>
}

export default function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const [action, setAction] = useState<"activate" | "deactivate" | null>(null)
  const [reason, setReason] = useState("")
  const [openWorkAction, setOpenWorkAction] = useState("")
  const [replacementEmployeeId, setReplacementEmployeeId] = useState("")
  const [enableLogin, setEnableLogin] = useState(false)
  const query = useQuery({ queryKey: ["employee", employeeId], queryFn: () => apiGet<FoundationRecord>(`/employees/${employeeId}/`) })
  const impact = useQuery({
    queryKey: ["employee-deactivation-impact", employeeId],
    queryFn: () => apiGet<{ open_work_count: number; work: OwnerWorkItem[] }>(`/employees/${employeeId}/deactivation-impact/`),
    enabled: action === "deactivate",
  })
  const replacements = useQuery({
    queryKey: ["owner-employees"],
    queryFn: () => apiGet<OwnerEmployee[]>("/owner/employees/"),
    enabled: action === "deactivate" && Boolean(impact.data?.open_work_count),
  })
  const lifecycle = useMutation({
    mutationFn: () => apiPost<FoundationRecord>(`/employees/${employeeId}/${action}/`, action === "activate" ? {
      reason,
      enable_login: enableLogin,
    } : {
      reason,
      ...(impact.data?.open_work_count ? { open_work_action: openWorkAction } : {}),
      ...(openWorkAction === "REASSIGN" ? { replacement_employee_id: replacementEmployeeId } : {}),
    }),
    onSuccess: async (saved) => {
      queryClient.setQueryData(["employee", employeeId], saved)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["resource", "employees"] }),
        queryClient.invalidateQueries({ queryKey: ["owner"] }),
        queryClient.invalidateQueries({ queryKey: ["owner-work"] }),
      ])
      closeAction()
    },
  })

  function closeAction() {
    setAction(null)
    setReason("")
    setOpenWorkAction("")
    setReplacementEmployeeId("")
    setEnableLogin(false)
    lifecycle.reset()
  }
  if (query.isPending) return <Skeleton className="mx-auto h-[520px] max-w-5xl" />
  if (query.isError) return <Alert variant="destructive"><AlertTitle>Employee unavailable</AlertTitle><AlertDescription>{query.error.message}</AlertDescription></Alert>
  const employee = query.data
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" render={<Link to="/app/employees" />} nativeButton={false}><ArrowLeft data-icon="inline-start" />Employee register</Button>
        {hasPermission(user, "organization.employee.manage") ? <div className="flex flex-wrap justify-end gap-2"><Button render={<Link to={`/app/employees/${employee.id}/edit`} />} nativeButton={false}><Pencil data-icon="inline-start" />Edit employee</Button>{employee.employment_status === "INACTIVE" ? <Button variant="outline" onClick={() => setAction("activate")}><UserCheck data-icon="inline-start" />Reactivate employee</Button> : <Button variant="destructive" onClick={() => setAction("deactivate")}><UserX data-icon="inline-start" />Deactivate employee</Button>}</div> : null}
      </div>
      <Card>
        <CardHeader className="bg-erp-sidebar text-white">
          <div className="flex items-start gap-4"><div className="flex size-14 items-center justify-center bg-white/10"><UserRound /></div><div><Badge variant="secondary">{String(employee.employment_status)}</Badge><CardTitle className="mt-3 text-2xl">{String(employee.display_name)}</CardTitle><CardDescription className="text-white/60">{String(employee.employee_code)}</CardDescription></div></div>
        </CardHeader>
        <CardContent className="grid gap-6 pt-6 sm:grid-cols-2 lg:grid-cols-3">
          <Detail label="Company" value={employee.company_name} /><Detail label="Branch" value={employee.branch_name} />
          <Detail label="Department" value={employee.department_name} /><Detail label="Designation" value={employee.designation_name} />
          <Detail label="Reporting manager" value={employee.reporting_manager_name} /><Detail label="Employment type" value={employee.employment_type} />
          <Detail label="Joining date" value={employee.joining_date} /><Detail label="Company email" value={employee.company_email} /><Detail label="Phone" value={employee.phone} />
        </CardContent>
      </Card>
      <div className="grid gap-4 sm:grid-cols-3">
        {[[Building2, "Organization linked"], [Mail, employee.company_email || "No company email"], [Phone, employee.phone || "No phone"]].map(([Icon, label]) => {
          const DetailIcon = Icon as typeof Building2
          return <Card key={String(label)}><CardContent className="flex items-center gap-3 pt-6"><DetailIcon className="text-primary" /><span className="text-sm">{String(label)}</span></CardContent></Card>
        })}
      </div>
      <Alert><CalendarDays /><AlertTitle>Employment record</AlertTitle><AlertDescription>User access and employee identity are deliberately maintained as separate records.</AlertDescription></Alert>

      <Dialog open={action !== null} onOpenChange={(open) => { if (!open) closeAction() }}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader><DialogTitle>{action === "activate" ? "Reactivate" : "Deactivate"} {String(employee.display_name)}?</DialogTitle><DialogDescription>{action === "activate" ? "This restores the employee to active employment. Login access stays separate unless explicitly enabled below." : "The employee and linked login will be disabled. Historical activity remains intact."}</DialogDescription></DialogHeader>
          {action === "deactivate" && impact.isPending ? <Skeleton className="h-28 w-full" /> : null}
          {action === "deactivate" && impact.isError ? <Alert variant="destructive"><AlertTitle>Impact could not be checked</AlertTitle><AlertDescription>{impact.error.message}</AlertDescription></Alert> : null}
          {action === "deactivate" && impact.data?.open_work_count ? <Alert><UserX /><AlertTitle>{impact.data.open_work_count} assigned open work item{impact.data.open_work_count === 1 ? "" : "s"}</AlertTitle><AlertDescription>{Array.from(new Set(impact.data.work.map((item) => item.work_type_label))).join(", ")}. Decide what should happen before continuing.</AlertDescription></Alert> : null}
          <FieldGroup>
            {action === "deactivate" && impact.data?.open_work_count ? <Field><FieldLabel htmlFor="employee-open-work-action">Open work</FieldLabel><NativeSelect id="employee-open-work-action" value={openWorkAction} onChange={(event) => { setOpenWorkAction(event.target.value); setReplacementEmployeeId("") }}><NativeSelectOption value="">Choose what should happen</NativeSelectOption><NativeSelectOption value="REASSIGN">Reassign all open work now</NativeSelectOption><NativeSelectOption value="LEAVE_TEMPORARILY">Leave assigned temporarily</NativeSelectOption></NativeSelect><FieldDescription>Completed work and assignment history are not changed.</FieldDescription></Field> : null}
            {action === "deactivate" && openWorkAction === "REASSIGN" ? <Field><FieldLabel htmlFor="employee-replacement">Reassign to</FieldLabel><NativeSelect id="employee-replacement" value={replacementEmployeeId} disabled={replacements.isPending || replacements.isError} onChange={(event) => setReplacementEmployeeId(event.target.value)}><NativeSelectOption value="">Choose an active employee</NativeSelectOption>{replacements.data?.filter((item) => item.id !== employee.id).map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.employee_code} · {item.display_name}</NativeSelectOption>)}</NativeSelect></Field> : null}
            {action === "activate" && employee.user ? <Field orientation="horizontal"><Checkbox id="enable-employee-login" checked={enableLogin} onCheckedChange={(checked) => setEnableLogin(checked === true)} /><FieldContent><FieldLabel htmlFor="enable-employee-login">Also enable the linked login</FieldLabel><FieldDescription>Only use this when the employee should sign in immediately.</FieldDescription></FieldContent></Field> : null}
            <Field><FieldLabel htmlFor="employee-lifecycle-reason">Why is this changing?</FieldLabel><Textarea id="employee-lifecycle-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Record the business reason…" /><FieldDescription>This reason is stored in Activity history.</FieldDescription></Field>
            {lifecycle.isError ? <Alert variant="destructive"><AlertTitle>Employee status could not be changed</AlertTitle><AlertDescription>{lifecycle.error.message}</AlertDescription></Alert> : null}
          </FieldGroup>
          <DialogFooter><Button variant="outline" onClick={closeAction}>Cancel</Button><Button variant={action === "deactivate" ? "destructive" : "default"} disabled={reason.trim().length < 3 || (action === "deactivate" && (impact.isPending || impact.isError || (Boolean(impact.data?.open_work_count) && !openWorkAction) || (openWorkAction === "REASSIGN" && !replacementEmployeeId))) || lifecycle.isPending} onClick={() => lifecycle.mutate()}>{lifecycle.isPending ? <Spinner data-icon="inline-start" /> : action === "activate" ? <UserCheck data-icon="inline-start" /> : <UserX data-icon="inline-start" />}{action === "activate" ? "Reactivate employee" : "Deactivate employee"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
