import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Building2, CalendarDays, Mail, Pencil, Phone, UserRound } from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { apiGet } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { FoundationRecord } from "@/production/lib/types"

function Detail({ label, value }: { label: string; value: unknown }) {
  return <div><p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value ? String(value).replaceAll("_", " ") : "—"}</p></div>
}

export default function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const { data: user } = useCurrentUser()
  const query = useQuery({ queryKey: ["employee", employeeId], queryFn: () => apiGet<FoundationRecord>(`/employees/${employeeId}/`) })
  if (query.isPending) return <Skeleton className="mx-auto h-[520px] max-w-5xl" />
  if (query.isError) return <Alert variant="destructive"><AlertTitle>Employee unavailable</AlertTitle><AlertDescription>{query.error.message}</AlertDescription></Alert>
  const employee = query.data
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" render={<Link to="/app/employees" />} nativeButton={false}><ArrowLeft data-icon="inline-start" />Employee register</Button>
        {hasPermission(user, "organization.employee.manage") ? <Button render={<Link to={`/app/employees/${employee.id}/edit`} />} nativeButton={false}><Pencil data-icon="inline-start" />Edit employee</Button> : null}
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
    </div>
  )
}
