import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { BadgeCheck, ShieldAlert, ShieldCheck } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Spinner } from "@/components/ui/spinner"
import { apiGet, apiPost } from "@/production/lib/api"
import type { AccessExplanation } from "@/production/lib/owner-types"
import type { FoundationRecord, Paginated } from "@/production/lib/types"

export default function OwnerAccessPage() {
  const [userId, setUserId] = useState("")
  const [permissionCode, setPermissionCode] = useState("")
  const users = useQuery({ queryKey: ["owner-access-users"], queryFn: () => apiGet<Paginated<FoundationRecord>>("/users/?page_size=100&ordering=email") })
  const permissions = useQuery({ queryKey: ["owner-access-permissions"], queryFn: () => apiGet<Paginated<FoundationRecord>>("/permissions/?is_active=true&page_size=100&ordering=code") })
  const explain = useMutation({
    mutationFn: () => apiPost<AccessExplanation>("/permissions/explain/", { user_id: userId, permission_code: permissionCode }),
  })

  return (
    <div className="flex flex-col gap-4">
      <Card size="sm">
        <CardHeader><CardTitle>Access check</CardTitle><CardDescription>Choose one login account and one action. The result explains the current effective access, including role scope and direct exceptions.</CardDescription></CardHeader>
        <CardContent>
          <FieldGroup>
            <div className="grid gap-4 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="access-user">Whose access?</FieldLabel>
                <NativeSelect id="access-user" value={userId} disabled={users.isPending || users.isError} onChange={(event) => { setUserId(event.target.value); explain.reset() }}>
                  <NativeSelectOption value="">Choose a login account</NativeSelectOption>
                  {users.data?.results.map((account) => <NativeSelectOption key={String(account.id)} value={String(account.id)}>{String(account.email)}{account.first_name ? ` · ${String(account.first_name)} ${String(account.last_name ?? "")}` : ""}</NativeSelectOption>)}
                </NativeSelect>
                <FieldDescription>Employee records without login accounts cannot sign in.</FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="access-action">Which action?</FieldLabel>
                <NativeSelect id="access-action" value={permissionCode} disabled={permissions.isPending || permissions.isError} onChange={(event) => { setPermissionCode(event.target.value); explain.reset() }}>
                  <NativeSelectOption value="">Choose an action</NativeSelectOption>
                  {permissions.data?.results.map((permission) => <NativeSelectOption key={String(permission.id)} value={String(permission.code)}>{String(permission.name)} · {String(permission.code)}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
            </div>
            {(users.isError || permissions.isError) ? <Alert variant="destructive"><AlertTitle>Options could not load</AlertTitle><AlertDescription>{users.error?.message ?? permissions.error?.message}</AlertDescription></Alert> : null}
            <Button className="self-start" disabled={!userId || !permissionCode || explain.isPending} onClick={() => explain.mutate()}>{explain.isPending ? <Spinner data-icon="inline-start" /> : <BadgeCheck data-icon="inline-start" />}Explain access</Button>
          </FieldGroup>
        </CardContent>
      </Card>

      {explain.isError ? <Alert variant="destructive"><ShieldAlert /><AlertTitle>Access could not be explained</AlertTitle><AlertDescription>{explain.error.message}</AlertDescription></Alert> : null}
      {explain.data ? (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">{explain.data.allowed ? <ShieldCheck /> : <ShieldAlert />}{explain.data.permission_name}</CardTitle>
            <CardDescription>{explain.data.reason}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Badge className="self-start" variant={explain.data.allowed ? "secondary" : "destructive"}>{explain.data.allowed ? "Allowed" : "Denied"}</Badge>
            {explain.data.roles.length ? <div><p className="text-sm font-medium">Matching roles</p><div className="mt-2 flex flex-wrap gap-2">{explain.data.roles.map((role, index) => <Badge key={`${role.name}-${index}`} variant="outline">{role.name} · {role.scope}</Badge>)}</div></div> : null}
            {explain.data.overrides.length ? <div><p className="text-sm font-medium">Direct exceptions</p><div className="mt-2 flex flex-col gap-2">{explain.data.overrides.map((override, index) => <div key={`${override.effect}-${index}`} className="rounded-lg border p-3 text-sm"><span className="font-medium">{override.effect} · {override.scope}</span><p className="mt-1 text-xs text-muted-foreground">{override.reason}</p></div>)}</div></div> : null}
            {!explain.data.roles.length && !explain.data.overrides.length ? <p className="text-sm text-muted-foreground">No matching role or direct exception was found for this company context.</p> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
