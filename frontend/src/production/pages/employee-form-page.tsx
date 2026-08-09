import { useQuery } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { apiGet } from "@/production/lib/api"
import { resourceConfigs } from "@/production/lib/resource-config"
import type { FoundationRecord } from "@/production/lib/types"

import { ResourceRecordForm } from "./resource-page"

export default function EmployeeFormPage() {
  const { employeeId } = useParams()
  const navigate = useNavigate()
  const query = useQuery({
    queryKey: ["employee", employeeId],
    queryFn: () => apiGet<FoundationRecord>(`/employees/${employeeId}/`),
    enabled: Boolean(employeeId),
  })
  if (employeeId && query.isPending) return <Skeleton className="mx-auto h-[720px] max-w-3xl" />
  if (query.isError) return <Alert variant="destructive"><AlertTitle>Employee unavailable</AlertTitle><AlertDescription>{query.error.message}</AlertDescription></Alert>
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <Button variant="ghost" render={<Link to={employeeId ? `/app/employees/${employeeId}` : "/app/employees"} />} nativeButton={false} className="self-start"><ArrowLeft data-icon="inline-start" />Back</Button>
      <Card>
        <CardHeader><CardTitle>{employeeId ? "Edit employee" : "Create employee"}</CardTitle><CardDescription>Employee identity, organization placement, reporting line, and optional sign-in account.</CardDescription></CardHeader>
        <CardContent>
          <ResourceRecordForm
            key={employeeId ?? "new"}
            config={resourceConfigs.employees}
            record={query.data}
            onSuccess={(saved) => navigate(`/app/employees/${saved.id}`, { replace: true })}
          />
        </CardContent>
      </Card>
    </div>
  )
}
