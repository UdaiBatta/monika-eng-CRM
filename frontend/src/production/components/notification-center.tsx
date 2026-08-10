import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Bell, CheckCheck, CircleCheck, Info, TriangleAlert } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { apiGet, apiPost } from "@/production/lib/api"
import { hasPermission, useCurrentUser } from "@/production/lib/auth"
import type { ERPNotification, Paginated } from "@/production/lib/types"
import { ERPEmptyState, ERPErrorState, ERPLoadingState, ERPStatusBadge, formatDateTime } from "@/production/components/shared"
import { cn } from "@/lib/utils"

function relativeTime(value: string) {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000)
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" })
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second")
  const minutes = Math.round(seconds / 60)
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute")
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour")
  return formatDateTime(value)
}

const icons = {
  INFO: Info,
  SUCCESS: CircleCheck,
  WARNING: TriangleAlert,
  ACTION_REQUIRED: AlertTriangle,
  CRITICAL: AlertTriangle,
}

export function ERPNotificationItem({ notification, onOpen }: { notification: ERPNotification; onOpen: () => void }) {
  const Icon = icons[notification.severity as keyof typeof icons] ?? Info
  return (
    <button type="button" onClick={onOpen} className={cn("flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", !notification.read_at && "border-primary/30 bg-primary/5")}>
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md bg-muted text-primary"><Icon /></span>
      <span className="min-w-0 flex-1"><span className="flex items-start justify-between gap-2"><span className="font-semibold">{notification.title}</span>{!notification.read_at ? <span className="mt-1 size-2 shrink-0 rounded-full bg-primary"><span className="sr-only">Unread</span></span> : null}</span><span className="mt-1 block text-sm leading-5 text-muted-foreground">{notification.message}</span><span className="mt-2 flex items-center justify-between gap-2"><span className="text-xs text-muted-foreground">{relativeTime(notification.created_at)}</span><ERPStatusBadge value={notification.severity} label={notification.severity_label} /></span></span>
    </button>
  )
}

export default function ERPNotificationBell() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const canView = hasPermission(user, "notifications.notification.view")
  const count = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => apiGet<{ count: number }>("/notifications/unread-count/"),
    enabled: canView,
    refetchInterval: 30_000,
  })
  const notifications = useQuery({
    queryKey: ["notifications", "inbox"],
    queryFn: () => apiGet<Paginated<ERPNotification>>("/notifications/?page_size=50"),
    enabled: canView,
  })
  const read = useMutation({
    mutationFn: (notification: ERPNotification) => notification.read_at ? Promise.resolve(notification) : apiPost<ERPNotification>(`/notifications/${notification.id}/read/`),
    onSuccess: (_, notification) => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] })
      if (notification.action_url) navigate(notification.action_url)
    },
  })
  const readAll = useMutation({
    mutationFn: () => apiPost<{ updated: number }>("/notifications/read-all/"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  })
  if (!canView) return null
  const items = notifications.data?.results ?? []
  const attention = items.filter((item) => !item.read_at && ["ACTION_REQUIRED", "CRITICAL", "WARNING"].includes(item.severity))
  const recent = items.filter((item) => !attention.includes(item)).slice(0, 12)
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button aria-label={`Notifications${count.data?.count ? `, ${count.data.count} unread` : ""}`} variant="outline" size="icon" className="relative">
          <Bell />
          {count.data?.count ? <Badge className="absolute -right-2 -top-2 min-w-5 justify-center px-1 text-[10px]">{count.data.count > 99 ? "99+" : count.data.count}</Badge> : null}
        </Button>
      </SheetTrigger>
      <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-md">
        <SheetHeader><div className="flex items-start justify-between gap-3 pr-8"><div><SheetTitle>Notifications</SheetTitle><SheetDescription>Work that needs attention and recent ERP updates.</SheetDescription></div>{count.data?.count ? <Button variant="ghost" size="sm" onClick={() => readAll.mutate()}><CheckCheck data-icon="inline-start" />Read all</Button> : null}</div></SheetHeader>
        <div className="mt-5 space-y-5">
          {notifications.isPending ? <ERPLoadingState rows={5} /> : notifications.isError ? <ERPErrorState message={notifications.error.message} /> : !items.length ? <ERPEmptyState title="No notifications" description="New approval work and important updates will appear here." /> : <>{attention.length ? <section><div className="mb-2 flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Needs attention</h3><Badge variant="secondary">{attention.length}</Badge></div><div className="space-y-2">{attention.map((item) => <ERPNotificationItem key={item.id} notification={item} onOpen={() => read.mutate(item)} />)}</div></section> : null}{attention.length && recent.length ? <Separator /> : null}{recent.length ? <section><h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent</h3><div className="space-y-2">{recent.map((item) => <ERPNotificationItem key={item.id} notification={item} onOpen={() => read.mutate(item)} />)}</div></section> : null}</>}
        </div>
      </SheetContent>
    </Sheet>
  )
}
