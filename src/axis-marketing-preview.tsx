import Companies from "@/components/companies"
import Feature from "@/components/feature"
import Footer from "@/components/footer"
import Hero from "@/components/hero"
import Navbar from "@/components/navbar"
import Pricing from "@/components/pricing"
import Stats from "@/components/stats"
import Testimonials from "@/components/testimonials"
import { ThemeProvider } from "@/components/theme-provider"
import ToolFeature from "@/components/tools"

export default function AxisMarketingPreview() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <div className="min-h-svh bg-background text-foreground">
        <Navbar />
        <main className="mx-auto flex max-w-7xl flex-col gap-24 px-4 pb-24 pt-32">
          <Hero />
          <Companies />
          <Feature />
          <Stats />
          <Pricing />
          <Testimonials />
          <ToolFeature />
        </main>
        <footer className="border-t border-border px-4 py-16"><Footer /></footer>
      </div>
    </ThemeProvider>
  )
}
