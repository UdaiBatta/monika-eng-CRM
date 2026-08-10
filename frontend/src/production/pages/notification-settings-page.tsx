import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell, Mail, MessageCircle, Smartphone } from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { apiGet, apiPatch } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import { ERPErrorState, ERPLoadingState, ERPPageHeader, ERPPermissionState } from "@/production/components/shared"

type Preference = {
  id: string
  in_app_enabled: boolean
  email_enabled: boolean
  sms_enabled: boolean
  whatsapp_enabled: boolean
  push_enabled: boolean
}

export default function NotificationSettingsPage() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const canManage = hasPermission(user, "notifications.notification.manage_preferences")
  const query = useQuery({ queryKey: ["notification-preferences"], queryFn: () => apiGet<Preference>("/notification-preferences/me/"), enabled: canManage })
  const mutation = useMutation({
    mutationFn: (enabled: boolean) => apiPatch<Preference>("/notification-preferences/me/", { in_app_enabled: enabled }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["notification-preferences"] }); toast.success("Notification preference saved.") },
  })
  if (!canManage) return <ERPPermissionState />
  if (query.isPending) return <ERPLoadingState rows={5} />
  if (query.isError) return <ERPErrorState message={query.error.message} />
  const channels = [
    { key: "in_app_enabled", label: "In-app notifications", description: "Approval assignments and important ERP outcomes inside this workspace.", icon: Bell, enabled: query.data.in_app_enabled, available: true },
    { key: "email_enabled", label: "Email", description: "Prepared for a future approved email delivery policy.", icon: Mail, enabled: false, available: false },
    { key: "sms_enabled", label: "SMS", description: "Not connected in this phase.", icon: Smartphone, enabled: false, available: false },
    { key: "whatsapp_enabled", label: "WhatsApp", description: "Not connected in this phase.", icon: MessageCircle, enabled: false, available: false },
  ]
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <ERPPageHeader eyebrow="Personal settings" title="Notification preferences" description="Choose how this ERP should alert you. In-app delivery is available now; paid external channels remain intentionally disabled." />
      <Alert><Bell /><AlertTitle>Business-critical policy is not invented here</AlertTitle><AlertDescription>Mandatory notification rules and external delivery channels require a future Monika Engineers policy decision.</AlertDescription></Alert>
      <Card><CardHeader><CardTitle>Delivery channels</CardTitle><CardDescription>Channels are introduced only when they are operational and approved.</CardDescription></CardHeader><CardContent className="divide-y">{channels.map((channel) => { const Icon = channel.icon; return <div key={channel.key} className="flex items-center gap-4 py-4 first:pt-0 last:pb-0"><span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary"><Icon /></span><div className="min-w-0 flex-1"><p className="font-semibold">{channel.label}</p><p className="text-sm text-muted-foreground">{channel.description}</p></div><div className="flex items-center gap-3"><span className="hidden text-xs text-muted-foreground sm:inline">{channel.available ? channel.enabled ? "Enabled" : "Disabled" : "Coming later"}</span><Switch aria-label={`Enable ${channel.label}`} checked={channel.enabled} disabled={!channel.available || mutation.isPending} onCheckedChange={(enabled) => mutation.mutate(enabled)} /></div></div> })}</CardContent></Card>
    </div>
  )
}
