import { lazy, Suspense } from "react"

const AxisERPMockup = lazy(() => import("@/mockups/axis/axis-erp-mockup"))
const AxisMarketingPreview = lazy(() => import("@/axis-marketing-preview"))

export default function App() {
  const isERPMockup = window.location.pathname.startsWith("/mockups/axis")

  return (
    <Suspense fallback={<div className="flex min-h-svh items-center justify-center bg-background text-sm text-muted-foreground">Loading UI preview…</div>}>
      {isERPMockup ? <AxisERPMockup /> : <AxisMarketingPreview />}
    </Suspense>
  )
}
