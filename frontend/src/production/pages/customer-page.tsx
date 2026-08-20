import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  CalendarClock,
  FileText,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  UserRound,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPost } from "@/production/lib/api";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";
import { employeeLabel } from "@/production/lib/terminology";
import {
  ActivityForm,
  ContactForm,
  SiteForm,
} from "@/production/components/crm-forms";
import {
  ERPEmptyState,
  ERPErrorState,
  ERPLoadingState,
  ERPPageHeader,
  ERPStatusBadge,
  formatBytes,
  formatDateTime,
} from "@/production/components/shared";
import type {
  Customer,
  Customer360,
  CustomerContact,
  CustomerSite,
  Quotation,
} from "@/production/lib/crm-types";
import type { Paginated } from "@/production/lib/types";
import type { Project, SalesOrder } from "@/production/lib/sales-types";
import { CustomerForm } from "@/production/pages/customers-page";

type Panel =
  | { kind: "customer" }
  | { kind: "contact"; record?: CustomerContact }
  | { kind: "site"; record?: CustomerSite }
  | { kind: "activity" }
  | null;

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <Card className="border-primary/15">
      <CardContent className="p-4">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </p>
        <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
        {detail ? (
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {detail}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CustomerSummary({ customer }: { customer: Customer }) {
  const location =
    customer.sites?.find((site) => site.is_default) ?? customer.sites?.[0];
  return (
    <Card>
      <CardContent className="grid gap-5 p-5 md:grid-cols-[minmax(240px,1.2fr)_repeat(3,minmax(130px,1fr))]">
        <div className="flex gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 text-primary">
            <Building2 />
          </span>
          <div>
            <p className="font-semibold">{customer.legal_name}</p>
            <p className="text-sm text-muted-foreground">
              {customer.customer_code} ·{" "}
              {customer.customer_type.replaceAll("_", " ")}
            </p>
            {customer.trade_name ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Trading as {customer.trade_name}
              </p>
            ) : null}
          </div>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Primary contact</p>
          <p className="mt-1 font-medium">
            {customer.primary_contact?.display_name || "Not assigned"}
          </p>
          <p className="text-xs text-muted-foreground">
            {customer.primary_contact?.phone ||
              customer.primary_phone ||
              customer.primary_email ||
              "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Primary location</p>
          <p className="mt-1 font-medium">{location?.label || "Not added"}</p>
          <p className="text-xs text-muted-foreground">
            {location ? `${location.city}, ${location.state}` : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Account manager</p>
          <p className="mt-1 font-medium">
            {customer.account_manager_name || "Unassigned"}
          </p>
          <p className="text-xs text-muted-foreground">
            Updated {formatDateTime(customer.updated_at)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function CustomerPage() {
  const { customerId = "" } = useParams();
  const { data: user } = useCurrentUser();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [panel, setPanel] = useState<Panel>(null);
  const [statusAction, setStatusAction] = useState<
    "activate" | "deactivate" | "block" | null
  >(null);
  const [statusReason, setStatusReason] = useState("");
  const query = useQuery({
    queryKey: ["customer-360", customerId],
    queryFn: () => apiGet<Customer360>(`/customers/${customerId}/360/`),
  });
  const quotations = useQuery({
    queryKey: ["customer-quotations", customerId],
    queryFn: () => apiGet<Paginated<Quotation>>(`/quotations/?customer=${customerId}&page_size=100`),
    enabled: Boolean(customerId) && hasPermission(user, "crm.quotation.view"),
  });
  const salesOrders = useQuery({
    queryKey: ["customer-sales-orders", customerId],
    queryFn: () => apiGet<Paginated<SalesOrder>>(`/sales/orders/?customer=${customerId}&page_size=100&ordering=-updated_at`),
    enabled: Boolean(customerId) && hasPermission(user, "sales.sales_order.view"),
  });
  const projects = useQuery({
    queryKey: ["customer-projects", customerId],
    queryFn: () => apiGet<Paginated<Project>>(`/projects/?customer=${customerId}&page_size=100&ordering=-updated_at`),
    enabled: Boolean(customerId) && hasPermission(user, "projects.project.view"),
  });
  const statusMutation = useMutation({
    mutationFn: () =>
      apiPost<Customer>(`/customers/${customerId}/${statusAction}/`, {
        reason: statusReason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-360", customerId] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      toast.success("Customer status updated.");
      setStatusAction(null);
      setStatusReason("");
    },
  });
  if (query.isPending) return <ERPLoadingState rows={9} />;
  if (query.isError)
    return (
      <ERPErrorState
        title="Customer could not be opened"
        message={query.error.message}
      />
    );
  const data = query.data;
  const customer = data.customer;
  const canEdit = hasPermission(user, "crm.customer.edit");
  const canAddContact = hasPermission(user, "crm.contact.create");
  const canAddActivity = hasPermission(user, "crm.activity.create");
  const canCreateEnquiry = hasPermission(user, "enquiry.enquiry.create");

  const panelTitle =
    panel?.kind === "customer"
      ? `Edit ${customer.legal_name}`
      : panel?.kind === "contact"
        ? panel.record
          ? "Edit contact"
          : "New contact"
        : panel?.kind === "site"
          ? panel.record
            ? "Edit site"
            : "New site"
          : "Record activity";
  const closePanel = () => setPanel(null);
  return (
    <div className="mx-auto flex max-w-[1580px] flex-col gap-5">
      <ERPPageHeader
        eyebrow="Customer 360"
        title={customer.legal_name}
        description={`${customer.customer_code} · One commercial record across the full customer relationship.`}
        actions={
          <>
            <ERPStatusBadge value={customer.status} />
            {canAddActivity ? (
              <Button
                variant="outline"
                onClick={() => setPanel({ kind: "activity" })}
              >
                <Activity data-icon="inline-start" />
                Log activity
              </Button>
            ) : null}
            {canCreateEnquiry ? (
              <Button
                onClick={() =>
                  navigate(`/app/crm/enquiries/new?customer=${customer.id}`)
                }
              >
                <Plus data-icon="inline-start" />
                New enquiry
              </Button>
            ) : null}
          </>
        }
      />
      <CustomerSummary customer={customer} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Open enquiries"
          value={data.overview.open_enquiries}
          detail={`${data.overview.won_enquiries} won · ${data.overview.lost_enquiries} lost`}
        />
        <Metric
          label="Open follow-ups"
          value={data.overview.open_follow_ups}
          detail={
            data.overview.next_follow_up
              ? formatDateTime(data.overview.next_follow_up.next_follow_up_at)
              : "Nothing scheduled"
          }
        />
        <Metric
          label="Last contact"
          value={
            data.overview.last_contact
              ? formatDateTime(data.overview.last_contact.activity_date)
              : "—"
          }
          detail={data.overview.last_contact?.subject ?? "No activity recorded"}
        />
        <Metric
          label="Customer since"
          value={formatDateTime(customer.created_at)}
          detail={
            customer.source
              ? `Source: ${customer.source}`
              : "Direct relationship"
          }
        />
      </div>

      <Tabs defaultValue="overview">
        <div className="overflow-x-auto pb-1">
          <TabsList className="h-auto min-w-max justify-start">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="contacts">
              Contacts{" "}
              <Badge variant="outline">{customer.contacts?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="sites">
              Sites{" "}
              <Badge variant="outline">{customer.sites?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="enquiries">
              Enquiries{" "}
              <Badge variant="outline">{data.recent_enquiries.length}</Badge>
            </TabsTrigger>
            {hasPermission(user, "crm.quotation.view") ? <TabsTrigger value="quotations">Quotations <Badge variant="outline">{quotations.data?.pagination.count ?? 0}</Badge></TabsTrigger> : null}
            {hasPermission(user, "sales.sales_order.view") ? <TabsTrigger value="sales-orders">Sales orders <Badge variant="outline">{salesOrders.data?.pagination.count ?? 0}</Badge></TabsTrigger> : null}
            {hasPermission(user, "projects.project.view") ? <TabsTrigger value="projects">Projects <Badge variant="outline">{projects.data?.pagination.count ?? 0}</Badge></TabsTrigger> : null}
            <TabsTrigger value="activities">Activities</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-[1.05fr_.95fr]">
            <Card>
              <CardHeader className="flex-row items-start justify-between">
                <div>
                  <CardTitle>Account profile</CardTitle>
                  <CardDescription>
                    Business identity and commercial defaults.
                  </CardDescription>
                </div>
                {canEdit ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPanel({ kind: "customer" })}
                  >
                    <Pencil data-icon="inline-start" />
                    Edit
                  </Button>
                ) : null}
              </CardHeader>
              <CardContent className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">
                    Legal / trade name
                  </p>
                  <p>
                    {customer.legal_name}
                    {customer.trade_name ? ` / ${customer.trade_name}` : ""}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Industry</p>
                  <p>{customer.industry || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">GSTIN / PAN</p>
                  <p>
                    {customer.gstin || "—"}
                    {customer.pan ? ` / ${customer.pan}` : ""}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Source</p>
                  <p>{customer.source || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Email</p>
                  <p>{customer.primary_email || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Phone</p>
                  <p>{customer.primary_phone || "—"}</p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-xs text-muted-foreground">
                    Internal notes
                  </p>
                  <p className="whitespace-pre-wrap">
                    {customer.notes || "No notes added."}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Next actions</CardTitle>
                <CardDescription>
                  Work requiring commercial attention.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.open_follow_ups.length ? (
                  <div className="flex flex-col divide-y">
                    {data.open_follow_ups.slice(0, 6).map((activity) => (
                      <div
                        key={activity.id}
                        className="flex items-start gap-3 py-3 first:pt-0"
                      >
                        <CalendarClock
                          className={
                            activity.is_overdue
                              ? "text-destructive"
                              : "text-primary"
                          }
                        />
                        <div className="min-w-0 flex-1">
                          <p className="font-medium">{activity.subject}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatDateTime(activity.next_follow_up_at)} ·{" "}
                            {activity.follow_up_owner_name || "Unassigned"}
                          </p>
                        </div>
                        <ERPStatusBadge
                          value={
                            activity.is_overdue ? "CRITICAL" : activity.priority
                          }
                          label={
                            activity.is_overdue
                              ? "Overdue"
                              : activity.priority.toLowerCase()
                          }
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <ERPEmptyState
                    title="No open follow-ups"
                    description="This account has no pending follow-up actions."
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="contacts" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Contacts</CardTitle>
                <CardDescription>
                  Buying, engineering, finance, and site stakeholders.
                </CardDescription>
              </div>
              {canAddContact ? (
                <Button size="sm" onClick={() => setPanel({ kind: "contact" })}>
                  <Plus data-icon="inline-start" />
                  Add contact
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {customer.contacts?.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {customer.contacts.map((contact) => (
                    <div
                      key={contact.id}
                      className="rounded-lg border bg-muted/20 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex gap-3">
                          <span className="grid size-9 place-items-center rounded-md border bg-background text-primary">
                            <UserRound />
                          </span>
                          <div>
                            <p className="font-medium">
                              {contact.display_name}{" "}
                              {contact.is_primary ? (
                                <Badge className="ml-1">Primary</Badge>
                              ) : null}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {[contact.title, contact.department]
                                .filter(Boolean)
                                .join(" · ") || "Contact"}
                            </p>
                          </div>
                        </div>
                        {canAddContact ? (
                          <Button
                            aria-label={`Edit ${contact.display_name}`}
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setPanel({ kind: "contact", record: contact })
                            }
                          >
                            <Pencil />
                          </Button>
                        ) : null}
                      </div>
                      <div className="mt-4 grid gap-2 text-sm">
                        <span className="flex items-center gap-2">
                          <Mail className="text-muted-foreground" />
                          {contact.email || "—"}
                        </span>
                        <span className="flex items-center gap-2">
                          <Phone className="text-muted-foreground" />
                          {contact.phone || "—"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No contacts yet"
                  description="Add the first stakeholder for this customer."
                  action={
                    canAddContact ? (
                      <Button onClick={() => setPanel({ kind: "contact" })}>
                        Add contact
                      </Button>
                    ) : undefined
                  }
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="sites" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Sites and addresses</CardTitle>
                <CardDescription>
                  Registered, billing, dispatch, and project locations.
                </CardDescription>
              </div>
              {canEdit ? (
                <Button size="sm" onClick={() => setPanel({ kind: "site" })}>
                  <Plus data-icon="inline-start" />
                  Add site
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {customer.sites?.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {customer.sites.map((site) => (
                    <div
                      key={site.id}
                      className="rounded-lg border bg-muted/20 p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex gap-3">
                          <MapPin className="text-primary" />
                          <div>
                            <p className="font-medium">
                              {site.label}{" "}
                              {site.is_default ? (
                                <Badge className="ml-1">Default</Badge>
                              ) : null}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {site.address_type.toLowerCase()}
                            </p>
                          </div>
                        </div>
                        {canEdit ? (
                          <Button
                            aria-label={`Edit ${site.label}`}
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setPanel({ kind: "site", record: site })
                            }
                          >
                            <Pencil />
                          </Button>
                        ) : null}
                      </div>
                      <p className="mt-3 text-sm leading-6 text-muted-foreground">
                        {site.address_line_1}
                        {site.address_line_2 ? `, ${site.address_line_2}` : ""}
                        <br />
                        {site.city}, {site.state} {site.postal_code}
                        <br />
                        {site.country}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No sites yet"
                  description="Add a registered, billing, dispatch, or project address."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="enquiries" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Enquiries and RFQs</CardTitle>
                <CardDescription>
                  Commercial opportunities raised for this account.
                </CardDescription>
              </div>
              {canCreateEnquiry ? (
                <Button
                  size="sm"
                  onClick={() =>
                    navigate(`/app/crm/enquiries/new?customer=${customer.id}`)
                  }
                >
                  <Plus data-icon="inline-start" />
                  New enquiry
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {data.recent_enquiries.length ? (
                <div className="divide-y">
                  {data.recent_enquiries.map((enquiry) => (
                    <Link
                      key={enquiry.id}
                      to={`/app/crm/enquiries/${enquiry.id}`}
                      className="flex items-center gap-3 py-3 first:pt-0 hover:text-primary"
                    >
                      <FileText />
                      <div className="min-w-0 flex-1">
                        <p className="font-medium">{enquiry.subject}</p>
                        <p className="text-xs text-muted-foreground">
                          {enquiry.enquiry_number} · Due{" "}
                          {enquiry.due_date || "not set"}
                        </p>
                      </div>
                      <ERPStatusBadge value={enquiry.status} />
                    </Link>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No enquiries yet"
                  description="Create the first enquiry when an RFQ or requirement is received."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        {hasPermission(user, "crm.quotation.view") ? <TabsContent value="quotations" className="mt-4"><Card><CardHeader className="flex-row items-start justify-between"><div><CardTitle>Customer quotations</CardTitle><CardDescription>Current commercial offers and their latest customer-facing value.</CardDescription></div><Link to="/app/crm/quotations"><Button size="sm" variant="outline">Open register</Button></Link></CardHeader><CardContent>{quotations.isPending ? <ERPLoadingState rows={4} /> : !quotations.data?.results.length ? <ERPEmptyState title="No quotations yet" description="Approved estimates and permitted quick offers will appear here." /> : <div className="divide-y">{quotations.data.results.map((quotation) => <Link key={quotation.id} to={`/app/crm/quotations/${quotation.id}`} className="flex items-center gap-3 py-3 first:pt-0 hover:text-primary"><FileText /><div className="min-w-0 flex-1"><p className="font-medium">{quotation.quotation_number}</p><p className="text-xs text-muted-foreground">Rev {quotation.current_revision.revision_number} · {quotation.current_revision.currency_code} {Number(quotation.current_revision.grand_total).toLocaleString("en-IN")}</p></div><ERPStatusBadge value={quotation.status} /></Link>)}</div>}</CardContent></Card></TabsContent> : null}
        {hasPermission(user, "sales.sales_order.view") ? <TabsContent value="sales-orders" className="mt-4"><Card><CardHeader className="flex-row items-start justify-between"><div><CardTitle>Customer sales orders</CardTitle><CardDescription>Confirmed commercial orders, PO state, and the released execution baseline.</CardDescription></div><Link to="/app/sales/orders"><Button size="sm" variant="outline">Open register</Button></Link></CardHeader><CardContent>{salesOrders.isPending ? <ERPLoadingState rows={4} /> : !salesOrders.data?.results.length ? <ERPEmptyState title="No Sales Orders yet" description="A ready quotation or permitted direct order will appear here." /> : <div className="divide-y">{salesOrders.data.results.map((order) => <Link key={order.id} to={`/app/sales/orders/${order.id}`} className="flex items-center gap-3 py-3 first:pt-0 hover:text-primary"><FileText /><div className="min-w-0 flex-1"><p className="font-medium">{order.sales_order_number}</p><p className="text-xs text-muted-foreground">{order.current_revision.currency_code} {Number(order.current_revision.grand_total).toLocaleString("en-IN")} · {order.po_pending ? "PO pending" : order.customer_po_number || "No PO linked"}</p></div><ERPStatusBadge value={order.status} /></Link>)}</div>}</CardContent></Card></TabsContent> : null}
        {hasPermission(user, "projects.project.view") ? <TabsContent value="projects" className="mt-4"><Card><CardHeader className="flex-row items-start justify-between"><div><CardTitle>Customer projects</CardTitle><CardDescription>Released orders that require an operational Project and Workshop handoff.</CardDescription></div><Link to="/app/projects"><Button size="sm" variant="outline">Open register</Button></Link></CardHeader><CardContent>{projects.isPending ? <ERPLoadingState rows={4} /> : !projects.data?.results.length ? <ERPEmptyState title="No Projects yet" description="Project work appears after a project-required Sales Order is released." /> : <div className="divide-y">{projects.data.results.map((project) => <Link key={project.id} to={`/app/projects/${project.id}`} className="flex items-center gap-3 py-3 first:pt-0 hover:text-primary"><Building2 /><div className="min-w-0 flex-1"><p className="font-medium">{project.project_number} · {project.project_name}</p><p className="text-xs text-muted-foreground">Workshop: {project.engineering_owner_name || "Unassigned"} · {employeeLabel(project.next_action)}</p></div><ERPStatusBadge value={project.status} /></Link>)}</div>}</CardContent></Card></TabsContent> : null}
        <TabsContent value="activities" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Activities and follow-ups</CardTitle>
                <CardDescription>
                  Calls, meetings, visits, notes, and scheduled next actions.
                </CardDescription>
              </div>
              {canAddActivity ? (
                <Button
                  size="sm"
                  onClick={() => setPanel({ kind: "activity" })}
                >
                  <Plus data-icon="inline-start" />
                  Record activity
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {data.recent_activities.length ? (
                <div className="divide-y">
                  {data.recent_activities.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex items-start gap-3 py-3 first:pt-0"
                    >
                      <span className="grid size-8 place-items-center rounded-full border bg-muted">
                        <Activity />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium">{activity.subject}</p>
                        <p className="text-xs text-muted-foreground">
                          {activity.activity_type.replaceAll("_", " ")} ·{" "}
                          {formatDateTime(activity.activity_date)} ·{" "}
                          {activity.created_by_name}
                        </p>
                        {activity.description ? (
                          <p className="mt-1 text-sm text-muted-foreground">
                            {activity.description}
                          </p>
                        ) : null}
                      </div>
                      <ERPStatusBadge value={activity.status} />
                    </div>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No activity yet"
                  description="Record the first call, meeting, visit, or commercial note."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Linked documents</CardTitle>
              <CardDescription>
                Files linked to this customer or its enquiries through the
                shared document service.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.recent_documents.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {data.recent_documents.map((document) => (
                    <Link
                      key={document.id}
                      to={`/app/documents/${document.id}`}
                      className="flex items-center gap-3 rounded-lg border p-4 hover:border-primary/50"
                    >
                      <FileText className="text-primary" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{document.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {document.document_number} · Version{" "}
                          {document.current_version?.version_number ?? "—"} ·{" "}
                          {formatBytes(document.current_version?.size_bytes)}
                        </p>
                      </div>
                      <ERPStatusBadge value={document.status} />
                    </Link>
                  ))}
                </div>
              ) : (
                <ERPEmptyState
                  title="No linked documents"
                  description="Documents linked through the shared document service will appear here."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Relationship history</CardTitle>
              <CardDescription>
                An audit-backed timeline of commercial activity and business
                changes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.timeline.length ? (
                <ol className="relative ml-3 border-l">
                  {data.timeline.map((item, index) => (
                    <li
                      key={`${item.occurred_at}-${index}`}
                      className="ml-6 pb-6 last:pb-0"
                    >
                      <span className="absolute -left-2 mt-1.5 size-3 rounded-full border-2 border-background bg-primary" />
                      <p className="font-medium">{item.summary}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(item.occurred_at)}
                        {item.actor_name ? ` · ${item.actor_name}` : ""}
                      </p>
                    </li>
                  ))}
                </ol>
              ) : (
                <ERPEmptyState
                  title="No history yet"
                  description="Audited changes and commercial activity will appear here."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Sheet
        open={Boolean(panel)}
        onOpenChange={(open) => {
          if (!open) closePanel();
        }}
      >
        <SheetContent className="axis-erp w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>{panelTitle}</SheetTitle>
            <SheetDescription>
              Changes are validated, permission checked, and recorded in the
              shared audit history.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {panel?.kind === "customer" ? (
              <CustomerForm customer={customer} onSaved={closePanel} />
            ) : panel?.kind === "contact" ? (
              <ContactForm
                customerId={customer.id}
                contact={panel.record}
                onSaved={closePanel}
              />
            ) : panel?.kind === "site" ? (
              <SiteForm
                customerId={customer.id}
                contacts={customer.contacts ?? []}
                site={panel.record}
                onSaved={closePanel}
              />
            ) : panel?.kind === "activity" ? (
              <ActivityForm customer={customer} onSaved={closePanel} />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
      <Dialog
        open={Boolean(statusAction)}
        onOpenChange={(open) => {
          if (!open) setStatusAction(null);
        }}
      >
        <DialogContent className="axis-erp">
          <DialogHeader>
            <DialogTitle>
              {statusAction === "block"
                ? "Block this customer?"
                : statusAction === "deactivate"
                  ? "Deactivate this customer?"
                  : "Activate this customer?"}
            </DialogTitle>
            <DialogDescription>
              This is a deliberate business status change and will be recorded
              in the audit trail.
            </DialogDescription>
          </DialogHeader>
          {statusMutation.error ? (
            <Alert variant="destructive">
              <AlertTitle>Status could not be changed</AlertTitle>
              <AlertDescription>
                {statusMutation.error.message}
              </AlertDescription>
            </Alert>
          ) : null}
          <Field>
            <FieldLabel htmlFor="status-reason">Reason</FieldLabel>
            <Textarea
              id="status-reason"
              value={statusReason}
              onChange={(event) => setStatusReason(event.target.value)}
            />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusAction(null)}>
              Cancel
            </Button>
            <Button
              variant={statusAction === "block" ? "destructive" : "default"}
              onClick={() => statusMutation.mutate()}
              disabled={statusMutation.isPending}
            >
              Confirm status change
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {canEdit ? (
        <Card>
          <CardHeader>
            <CardTitle>Account controls</CardTitle>
            <CardDescription>
              Use explicit lifecycle actions instead of editing status directly.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {customer.status !== "ACTIVE" ? (
              <Button
                variant="outline"
                onClick={() => setStatusAction("activate")}
              >
                Activate
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => setStatusAction("deactivate")}
              >
                Deactivate
              </Button>
            )}
            {customer.status !== "BLOCKED" ? (
              <Button
                variant="destructive"
                onClick={() => setStatusAction("block")}
              >
                Block account
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
