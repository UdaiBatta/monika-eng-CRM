# UX workflow consistency audit

Date: 2026-08-19  
Branch: `ux-workflow-consolidation`  
Scope: implemented employee and Owner surfaces before Phase 4 Detailed Engineering  
Product rule: **Simple for staff. Structured underneath.**

## Audit method and boundary

This audit was made from the real routes, navigation, shared components, page source, permissions, API-backed actions, tests, and current baseline. It is intentionally a presentation and workflow audit: internal model names, API paths, permission codes, migrations, and historical audit data may retain `engineering` identifiers where renaming would add compatibility risk.

Not in this milestone: Drawings, BOM, purchasing, inventory transactions, GRN, production, quality, dispatch, service, AMC, live WhatsApp/TradeIndia integrations, malware scanning, or deployment. References to Detailed Engineering are future-domain context only.

## Current navigation catalogue

| Section | Current item | Permission gate | Finding |
| --- | --- | --- | --- |
| Daily work | Home | authenticated | Mixes work counters, phase readiness, access explanations, system health, and future Engineering vision. It does not lead with actual tasks. |
| Daily work | New enquiries | `crm.external_enquiry.view` | Useful queue, but separated from active enquiries by an internal record boundary. |
| Daily work | Active enquiries | `enquiry.enquiry.view` | Useful register; name exposes lifecycle partition rather than the employee responsibility. |
| Daily work | Customers | `crm.customer.view` | Appropriate for Sales. |
| Daily work | Quotations | `crm.quotation.view` | Customer POs and Sales Orders compete beside it although they are one commercial journey. |
| Daily work | Customer POs | `sales.customer_po.view` | Should be secondary navigation inside Quotations & Orders. |
| Daily work | Sales orders | `sales.sales_order.view` | Should be secondary navigation inside Quotations & Orders. |
| Daily work | Projects | `projects.project.view` | Appropriate for Workshop/Owner; contextual links should make it unnecessary during ordinary Sales progression. |
| Daily work | Engineering work | `projects.handoff.take_ownership` | Wrong staff terminology; route currently aliases the general Projects register instead of a clear Workshop responsibility view. |
| Daily work | Follow-ups | `crm.activity.view` | Appropriate for Sales. |
| Daily work | Inventory & workshop | `organization.warehouse.view` | Links to the warehouse master register; the label promises daily inventory/workshop operations that are not implemented. |
| Shared | Documents | `documents.document.view` | Appropriate shared workspace. |
| Shared | Approvals | `approvals.request.view` | Appropriate shared/Owner responsibility. |
| Shared | Employees | `organization.employee.view` | Administration mixed into ordinary employee navigation. |
| More | Tools & settings | any broad tool permission | Contains both administration and operational Engineering checks/Cost estimates. Operational work must be removed. |
| Header | Owner control | `system.owner_control.view` | Correctly permission-gated and separated; retain. |

Desired standard: build a small, permission-derived responsibility navigation. Sales gets My Work, Enquiries, Customers, Quotations & Orders, Follow-ups, and Documents. Workshop gets My Workshop Work, Projects, Clarifications where supported, and Documents. Owner gets the Owner Centre entry plus appropriate shared responsibilities. Do not check role names; derive entries from effective permissions.

## Surface and interaction catalogue

`Shared` below means the page already uses at least one of `ERPPageHeader`, `ERPStatusBadge`, `ERPLoadingState`, `ERPErrorState`, or `ERPEmptyState`. `Local` means the page still invents a similar presentation locally.

| Surface | Header / status | Primary and secondary actions | Forms, overlays, tables, states, workflow/tabs | Main inconsistency and desired standard |
| --- | --- | --- | --- | --- |
| Login | Local | Sign in | Form, inline alert, loading button | Keep focused; use the same field/error language as production forms. |
| Home | Local Card header / mixed Badges | Many equal `Open register` links | Metric cards, journey cards, access matrix, health/readiness blocks, skeletons | Replace with real My Work and Needs Attention from permitted records. One task row = context + reason + one next action. Owner health belongs in Owner Centre. |
| Incoming enquiries register | Shared | Register/import/review actions | Search, queue/status filters, table/cards, import dialog, loading/error/empty | Preserve My/Team/Unassigned/Needs Attention queues; use Enquiries as the staff mental model and make Review the row action. |
| Incoming enquiry detail | Shared | Convert/decision actions | Tabs: Review, CRM conversion, Source & security; customer/contact forms; ownership; decision dialog; toasts | Tabs are information views, but conversion is both a tab and workflow action. Surface one Next Action and keep provenance secondary. |
| Enquiries register | Shared | New/import/open/claim | Queue filters, table, import, dialogs, loading/error/empty | Good register foundation; rename Workshop states, standardize queue tabs, friendly claim-race copy. |
| Enquiry create | Shared | Create enquiry | Long form, validation, submit/cancel | Known customer/contact context should prefill; advanced details should be disclosed only when needed. |
| Enquiry detail | Shared / several local workflow badges | Status-dependent action collection | Large form, multiple dialogs, tabs, workflow/progress cards, activity/documents, toasts | Duplicates state through header, status, controlled-flow panels, tabs and buttons. Use one restrained journey plus reusable Next Action. Rename operational Engineering labels to Workshop. |
| Customers register | Shared | New/import/open | Search/filter, table, import, dialog, states, toasts | Retain; align primary action placement and import copy. |
| Customer detail | Shared | Edit/add contact/activity | Forms, dialogs, tabs/sections, toasts, empty/loading/error | Customer is context; related records should offer direct continuation without exposing module plumbing. |
| Activities & follow-ups | Shared | Record activity | Filters, table, dialog/form, states, toast | Good responsibility view. Copy should consistently say next action/follow-up and link back to customer/enquiry. |
| Workshop review register (`engineering-page`) | Shared / old Engineering labels | Take/open/assign | Queue filters, table, assignment form, states | Correct operational location but wrong terminology. Make it My Workshop Work with My/Team/Unassigned/Needs Attention and domain actions. |
| Workshop review detail (`engineering-review-page`) | Shared / old Engineering labels | Assign, request clarification, save assessment, complete/not feasible | Large assessment form, dialogs, tabs, clarification thread, documents, activity, toasts | Multiple actions compete; form is more technical than many jobs require. Use one Next Action, Workshop wording, and progressive disclosure for optional programming/preliminary details. No arbitrary status dropdown. |
| Estimates register | Shared | Create/open | Filters, table, dialog/form, states | Operational work incorrectly discoverable under Tools. Keep accessible contextually from an approved enquiry and optionally through Quotations & Orders. |
| Estimate detail | Shared | Edit/submit/approve/create quotation | Tabs, cost tables, approval actions, states | Several equal actions; sensitive margin information needs permission enforcement and one status-derived Next Action. |
| Quotations register | Shared | Create/open/import where supported | Queue/filter table, dialog, states | Place inside Quotations & Orders secondary navigation and retain direct register route. |
| Quotation detail | Shared | Finalize/share/negotiate/confirm/revise | Progress/action card, tabs, item tables, dialogs, states | Workflow steps and tabs partially duplicate negotiation/confirmation. Tabs should be Quotation, Documents, Activity, Revisions; events/actions belong in Next Action. |
| Customer PO register | Shared | Record/link/revise/accept differences | Table, filters, dialogs, upload, states | Treat as Customer Confirmations/POs within Quotations & Orders; contextual creation should inherit customer and accepted quotation. |
| Sales Orders register | Shared | New/open | Queue/filter table, dialogs, states | Keep as secondary commercial register; common journey should reach it contextually. |
| Sales Order detail | Shared | Submit/release/create project/link PO/amend/hold/resume/cancel | One local “What happens next?” card with many buttons, tabs, line table, dialogs | Too many equally prominent actions. Reuse Next Action; secondary and destructive actions go under restrained alternatives. Released revision immutability remains authoritative. |
| Projects register | Shared | Open/take work | Queue table, states | Becomes Workshop-facing Projects; route alias must not be labelled Engineering work. |
| Project 360 detail | Shared | Prepare/send/take/accept handoff; clarify | Local action card, tabs, dialogs, revision/history tables | Rename practical handoff to Workshop. Keep Detailed Engineering as a future boundary, not a current action. Reuse Next Action and journey language. |
| Documents register/detail | Shared | Upload/new revision/submit/approve/download | Tables, forms, dialogs, workflow/history, states, toasts | Mostly consistent. Critical actions need one primary; private download authorization remains a production-security concern. |
| Approvals register/detail | Shared | Review/approve/reject/reassign | Queue tabs, dialogs, timeline, states, toasts | Appropriate shared responsibility. Standardize confirmation and success copy; retain immutable decision history. |
| Employees list/detail/form | Mixed Shared/Local | Add/edit/lifecycle actions | Resource table, forms, dialogs, loading/errors | Administrative, not normal staff navigation. Retain final-Owner and reassignment safeguards. |
| Activity history | Shared | Inspect | Table/list, detail Sheet, filters, states | Appropriate read-only administration surface; drawer use is consistent for inspection. |
| Tools & settings landing | Local header | Many link-buttons | Grouped cards; local empty state | Remove Workshop Review and Cost Estimates. Use shared page header/empty state; configuration only. |
| Company/branch/department/designation/warehouse resources | Generic ResourcePage | Create/edit/import/export | Shared generic table, form dialog/page, import dialog, states, toasts | Efficient reuse but labels/help vary by configuration. Keep administrative and consistently import-capable. Do not present warehouse master data as live inventory transactions. |
| Users/roles/permissions/assignments/overrides resources | Generic ResourcePage | Create/edit/assign/import where allowed | Tables/forms/dialogs/states | Permission editor patterns must remain uniform. Owner-only mutations require backend enforcement, not just hidden controls. |
| Company settings/features/numbering/masters/categories/notifications | Mixed generic/specialized | Save/enable/disable/create | Forms, dialogs, tabs, states, toasts | Use domain-specific verbs and shared header/form/error patterns. Feature control must also be enforced at API level. |
| Approval workflow setup | Shared | New/version/activate/add step/condition | Many dialogs/forms/cards, toasts | Correctly administrative but dense. Keep out of daily navigation and align confirmations/errors. Old “Engineering manager” placeholder should use Workshop where operational. |
| Owner overview | Owner layout + mixed cards | Inspect/open areas | Metric/action cards, states | Safety boundary is correct. Align headers/status/buttons with shared components; avoid duplicating system health. |
| Owner work | Owner layout + shared states | Reassign/open | Work table, filters, reassign dialog, toasts | Good coordination view; use Workshop labels and same queue/status conventions as employee work. |
| Owner access | Owner layout | Inspect people/access | Tables/cards, loading/error | Keep focused on effective access; use the same empty/status patterns. |
| Owner feature controls | Owner layout | Enable/disable with reason | Dialogs/forms, status badges, toasts | Preserve reason, stale edit, audit, and domain-specific verbs. Match shared confirmation language. |
| Owner data quality | Owner layout | Inspect/import routes | Cards/tables, states | Do not imply deduplication/archive automation exists. Link only to implemented imports and reports. |
| Owner system health | Owner layout | Refresh/inspect | Health cards, states | Correct home for system readiness; remove duplicate health from employee Home. |
| Notification centre | Local Sheet | Open/mark read | Sheet, list, badges, loading/empty/error | Suitable drawer; make user-facing Workshop notification wording consistent. |

## Status and terminology catalogue

The shared status component currently maps common states consistently by semantic colour, but it renders internal identifiers by replacing underscores. This leaks internal language and creates several incorrect staff labels.

| Internal/current employee text | Required employee presentation | Notes |
| --- | --- | --- |
| Engineering checks / Engineering Review | Workshop Review | Operational pre-quotation review only. |
| Engineering work | Workshop Work | Practical project responsibility only. |
| Send to Engineering / Ready for Engineering | Send to Workshop / Ready for Workshop | Action language, not generic status selection. |
| Engineering Reviewing | Workshop Reviewing | Preserve internal enum if compatibility requires it. |
| Engineering Accepted | Workshop Accepted | Practical handoff accepted. |
| Engineering clarification | Workshop clarification | Clarification thread remains linked to Sales. |
| Feasible / Engineering Approved | Workshop Approved | Explain in plain language: build/program as currently specified. |
| Not feasible | Workshop cannot approve | Avoid implying a final commercial decision. |
| Ready for Detailed Engineering | Ready for Detailed Engineering | Legitimate future-domain terminology; not a functional Phase 4 action yet. |
| Engineering hours | Workshop/technical hours | Use only where the estimate genuinely requires the field. |

Required implementation pattern: a presentation-only label map used by status badges, navigation, page titles, toasts, and operational copy. Internal types, endpoints such as `/engineering-reviews/`, permissions such as `engineering.feasibility.*`, and migration history remain unchanged unless a separate compatibility-safe backend change is justified.

## Shared UI standard to apply

### Record/page header

Use `ERPPageHeader` for all major pages. A detail page shows record identity and short context on the left, then status/owner and at most one primary action on the right. Registers show title, useful queue context, and one create/import action group.

### Next action

Add one small shared `NextActionPanel`. It shows current status, a plain-language explanation, next step, one dominant permitted action, and restrained secondary actions. It delegates all eligibility and mutation to existing domain rules; it is not a new workflow engine.

### Journey and tabs

- Journey/progress answers “Where am I?” and is read-only.
- Next Action answers “What should I do?”
- Tabs answer “Which information do I want to inspect?”

Do not use tabs named for actions or render multiple competing workflow diagrams.

### Forms

Use shared Field primitives, visible labels, required markers/help/error text, consistent submit/cancel placement, disabled/pending copy, and a “More details” disclosure for optional technical fields. Server validation remains visible near the form and focusable.

### Tables and queues

Keep the existing compact enterprise tables. Standard queue vocabulary is My Work, Team Work, Unassigned, and Needs Attention where the endpoint supports it. Rows show identity, customer/context, status text, owner, attention reason/due information, and one clear Open/Review action. `Take This` must retain transaction-safe claiming and translate conflicts into colleague-friendly copy.

### Dialogs, drawers, confirmation, and toasts

- Dialog: short create/action/confirmation requiring focus.
- Drawer/Sheet: inspect contextual information without leaving a register.
- Page: long forms or records that need a stable URL.
- Sensitive/destructive dialogs state impact and require the existing reason where applicable.
- Success toast: what happened + record identity; next route only when useful.
- Error toast/alert: plain-language cause + recovery. Never expose locking/serializer terminology.

### Empty/loading/error/access states

Use the shared components everywhere. Empty states say why the list is empty and offer one valid next action. Loading retains layout. Errors explain retry/recovery. Permission denial is explicit and does not masquerade as “not found” in the UI; backend object access remains authoritative.

### Visual and accessibility standard

Preserve Axis CRM: deep navy, teal, off-white, restrained amber, table-first density. Use semantic tokens, visible focus, labels, button text for critical actions, status text in addition to colour, keyboard-operable tabs/dialogs, and accessible validation. Avoid large KPI walls, tiny labels, decorative future-feature canvases, and equal emphasis on every control.

## Highest-priority implementation sequence

1. Add the presentation terminology map and targeted tests.
2. Replace the long module navigation with permission-derived responsibility groups; add Quotations & Orders secondary navigation and Workshop aliases while preserving old URLs.
3. Remove operational work from Tools & Settings.
4. Replace Home counters/readiness/future canvas with real My Work and Needs Attention records.
5. Add `NextActionPanel` and apply it to enquiry, Workshop review, estimate, quotation, Sales Order, and project handoff details.
6. Simplify enquiry/quotation progress vs tabs vs actions; preserve contextual references through downstream creation.
7. Align Owner labels/patterns without changing its safety architecture.
8. Run targeted authorization, isolation, workflow-bypass, immutable-release, CSRF, document, import/export, XSS-rendering, audit, concurrency, and regression tests.
9. Attempt real Sales, Workshop, and Owner browser UAT. Record anything not actually exercised as an open gate.

## Risks and production gates identified before changes

- UI terminology is spread across components, pages, tests, backend notification copy, seed data, and Owner work labels. A partial rename would be worse than leaving one coherent term.
- Existing generic status rendering exposes internal enum names; the presentation layer must not change stored values.
- Home currently queries counts, not actionable record summaries. Real task rows need existing queue APIs and must respect each endpoint's permissions/scopes.
- “Inventory & workshop” currently points to warehouse master data; inventory transactions do not exist and must not be implied.
- Manual multi-account UAT, presence/race testing, malware scanning, live integrations, and production deployment cannot be claimed from automated regression alone.
- Security conclusions must be stated per tested surface. “The app is secure” is not an acceptable completion statement.
