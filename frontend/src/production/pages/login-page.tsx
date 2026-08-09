import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowRight, CheckCircle2, Factory, LockKeyhole, ShieldCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { Navigate, useLocation, useNavigate } from "react-router-dom"
import { z } from "zod"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { ApiError, apiGet, apiPost } from "@/production/lib/api"
import { currentUserQueryKey, useCurrentUser } from "@/production/lib/auth"
import type { CurrentUser } from "@/production/lib/types"

const loginSchema = z.object({
  identifier: z.string().trim().min(1, "Enter your email or username."),
  password: z.string().min(1, "Enter your password."),
})

type LoginValues = z.infer<typeof loginSchema>

const foundationPoints = [
  "Same-origin sessions with CSRF protection",
  "Company, branch, department and warehouse scopes",
  "Explicit deny takes precedence across access rules",
]

export default function LoginPage() {
  const currentUser = useCurrentUser()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: "", password: "" },
  })
  const mutation = useMutation({
    mutationFn: (values: LoginValues) => apiPost<CurrentUser>("/auth/login/", values),
    onSuccess: async () => {
      const user = await apiGet<CurrentUser>("/auth/me/")
      queryClient.setQueryData(currentUserQueryKey, user)
      const destination = (location.state as { from?: string } | null)?.from ?? "/app"
      navigate(destination, { replace: true })
    },
  })

  if (currentUser.data) return <Navigate to="/app" replace />

  return (
    <main className="axis-erp grid min-h-svh bg-background lg:grid-cols-[minmax(0,1.08fr)_minmax(440px,0.92fr)]">
      <section className="relative hidden overflow-hidden bg-erp-sidebar p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-6 border border-white/10" aria-hidden="true" />
        <div className="relative flex items-center gap-3">
          <div className="flex size-11 items-center justify-center border border-white/30 bg-white/5 text-xl font-black">M</div>
          <div>
            <p className="text-lg font-bold tracking-tight">MONIKA ENGINEERS</p>
            <p className="text-xs tracking-[0.22em] text-white/60">INTEGRATED ERP</p>
          </div>
        </div>

        <div className="relative max-w-2xl">
          <Badge variant="secondary" className="mb-6">Production foundation · Phase 1</Badge>
          <h1 className="max-w-xl text-5xl font-semibold leading-[1.04] tracking-[-0.04em]">
            One controlled workspace for engineering operations.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-white/65">
            The Axis project-first experience, now connected to a secure Django foundation built for Monika Engineers.
          </p>
          <div className="mt-9 grid gap-3">
            {foundationPoints.map((point) => (
              <div key={point} className="flex items-center gap-3 border-t border-white/10 pt-3 text-sm text-white/80">
                <CheckCircle2 aria-hidden="true" />
                <span>{point}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative grid grid-cols-3 gap-3">
          {[
            [Factory, "Industrial", "Project-first"],
            [ShieldCheck, "Controlled", "Role-based"],
            [LockKeyhole, "Protected", "Session-secure"],
          ].map(([Icon, title, label]) => {
            const FeatureIcon = Icon as typeof Factory
            return (
              <div key={String(title)} className="border border-white/10 bg-white/5 p-4">
                <FeatureIcon aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold">{String(title)}</p>
                <p className="text-xs text-white/50">{String(label)}</p>
              </div>
            )
          })}
        </div>
      </section>

      <section className="flex items-center justify-center p-5 sm:p-10">
        <Card className="w-full max-w-md shadow-none">
          <CardHeader className="gap-2">
            <div className="mb-4 flex size-10 items-center justify-center bg-erp-sidebar font-black text-white lg:hidden">M</div>
            <CardTitle className="text-3xl tracking-tight">Welcome back</CardTitle>
            <CardDescription>Sign in to the Monika Engineers production foundation.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
              <FieldGroup>
                {mutation.error ? (
                  <Alert variant="destructive">
                    <AlertTitle>Sign-in failed</AlertTitle>
                    <AlertDescription>
                      {mutation.error instanceof ApiError ? mutation.error.message : "Please try again."}
                    </AlertDescription>
                  </Alert>
                ) : null}
                <Field data-invalid={Boolean(form.formState.errors.identifier)}>
                  <FieldLabel htmlFor="identifier">Email or username</FieldLabel>
                  <Input
                    id="identifier"
                    autoComplete="username"
                    autoFocus
                    aria-invalid={Boolean(form.formState.errors.identifier)}
                    {...form.register("identifier")}
                  />
                  <FieldError errors={[form.formState.errors.identifier]} />
                </Field>
                <Field data-invalid={Boolean(form.formState.errors.password)}>
                  <FieldLabel htmlFor="password">Password</FieldLabel>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    aria-invalid={Boolean(form.formState.errors.password)}
                    {...form.register("password")}
                  />
                  <FieldError errors={[form.formState.errors.password]} />
                </Field>
                <Field>
                  <Button type="submit" size="lg" disabled={mutation.isPending} className="w-full">
                    {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
                    {mutation.isPending ? "Signing in…" : "Enter workspace"}
                    {!mutation.isPending ? <ArrowRight data-icon="inline-end" /> : null}
                  </Button>
                  <FieldDescription className="text-center">
                    Access is granted by your organization administrator.
                  </FieldDescription>
                </Field>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
