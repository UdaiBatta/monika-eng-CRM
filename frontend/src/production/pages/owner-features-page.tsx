import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { LockKeyhole, Settings2 } from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { ERPErrorState, ERPLoadingState } from "@/production/components/shared"
import { apiGet, apiPost } from "@/production/lib/api"
import { currentUserQueryKey, hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { OwnerFeature } from "@/production/lib/owner-types"

type FeatureResponse = { features: OwnerFeature[] }

export default function OwnerFeaturesPage() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<OwnerFeature | null>(null)
  const [reason, setReason] = useState("")
  const canManage = hasPermission(user, "configuration.feature_flag.manage")
  const query = useQuery({ queryKey: ["owner-features"], queryFn: () => apiGet<FeatureResponse>("/owner/features/") })
  const change = useMutation({
    mutationFn: () => apiPost<FeatureResponse>("/owner/change-feature/", {
      key: selected?.key,
      is_enabled: !selected?.is_enabled,
      reason,
      record_version: selected?.record_version,
    }),
    onSuccess: async (data) => {
      queryClient.setQueryData(["owner-features"], data)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: currentUserQueryKey }),
        queryClient.invalidateQueries({ queryKey: ["owner"] }),
      ])
      toast.success(`${selected?.name} ${selected?.is_enabled ? "disabled" : "enabled"}.`)
      closeDialog()
    },
  })

  function closeDialog() {
    setSelected(null)
    setReason("")
    change.reset()
  }

  if (query.isPending) return <ERPLoadingState rows={8} />
  if (query.isError) return <ERPErrorState title="Feature controls could not load" message={query.error.message} />

  return (
    <div className="flex flex-col gap-4">
      <Alert>
        <LockKeyhole />
        <AlertTitle>Safe business controls</AlertTitle>
        <AlertDescription>Changes affect future actions only. Existing records stay available, and unfinished modules cannot be enabled.</AlertDescription>
      </Alert>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {query.data.features.map((feature) => (
          <Card key={feature.key} size="sm">
            <CardHeader>
              <CardTitle>{feature.name}</CardTitle>
              <CardDescription>{feature.description}</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-4">
              <Badge variant={feature.implemented ? feature.is_enabled ? "secondary" : "outline" : "outline"}>{feature.status}</Badge>
              {feature.implemented ? (
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{canManage ? "Change" : "View only"}</span>
                  <Switch
                    aria-label={`${feature.is_enabled ? "Disable" : "Enable"} ${feature.name}`}
                    checked={feature.is_enabled}
                    disabled={!canManage}
                    onCheckedChange={() => { setSelected(feature); setReason("") }}
                  />
                </div>
              ) : <span className="text-xs text-muted-foreground">Planned module</span>}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={selected !== null} onOpenChange={(open) => { if (!open) closeDialog() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selected?.is_enabled ? "Disable" : "Enable"} {selected?.name}</DialogTitle>
            <DialogDescription>This controlled change is recorded in Activity history. Existing records will not be deleted.</DialogDescription>
          </DialogHeader>
          <Field>
            <FieldLabel htmlFor="feature-change-reason">Why is this changing?</FieldLabel>
            <Textarea id="feature-change-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain the business reason…" />
            <FieldDescription>Required so another administrator can understand the decision later.</FieldDescription>
          </Field>
          {change.isError ? <Alert variant="destructive"><AlertTitle>Feature could not be changed</AlertTitle><AlertDescription>{change.error.message}</AlertDescription></Alert> : null}
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>Cancel</Button>
            <Button disabled={reason.trim().length < 3 || change.isPending} onClick={() => change.mutate()}>
              {change.isPending ? <Spinner data-icon="inline-start" /> : <Settings2 data-icon="inline-start" />}
              Confirm change
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
