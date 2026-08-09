import { Navigate, Outlet, useLocation } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/production/lib/api"
import { useCurrentUser } from "@/production/lib/auth"

export default function AuthBoundary() {
  const location = useLocation()
  const currentUser = useCurrentUser()

  if (currentUser.isPending) {
    return (
      <div className="axis-erp flex min-h-svh items-center justify-center bg-background text-muted-foreground">
        <Spinner />
        <span className="ml-2 text-sm">Securing your workspace…</span>
      </div>
    )
  }

  if (currentUser.error instanceof ApiError && currentUser.error.status === 401) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (currentUser.isError) {
    return (
      <div className="axis-erp flex min-h-svh items-center justify-center bg-background p-6">
        <Alert variant="destructive" className="max-w-lg">
          <AlertTitle>Workspace unavailable</AlertTitle>
          <AlertDescription className="flex flex-col gap-3">
            <span>{currentUser.error.message}</span>
            <Button variant="outline" onClick={() => currentUser.refetch()}>Try again</Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return <Outlet />
}
