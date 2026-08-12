# Commercial Estimation

## Entry and exit gates

An Estimate can be created only from the current completed FEASIBLE Engineering review with no open clarifications. Creating the first revision moves the Enquiry to Estimation. Approving the current Estimate moves it to Estimation Complete and displays Ready for Quotation. No Quotation model, PDF, action, or route is included in this milestone.

Frontend routes:

- `/app/crm/estimates`
- `/app/crm/estimates/:estimateId`

Primary APIs:

- `/api/v1/commercial-estimates/`
- `/api/v1/commercial-estimates/:id/workspace/`
- `/api/v1/commercial-estimates/:id/submit/`
- `/api/v1/commercial-estimates/:id/revise/`
- `/api/v1/commercial-estimates/:id/revisions/`
- `/api/v1/estimate-cost-lines/`

## Data and calculations

`CommercialEstimate` is a numbered, company-scoped revision with a frozen Engineering reference, commercial basis, pricing method, totals, owner, approval link, and audit actors/timestamps. `EstimateCostLine` records category, description, Decimal quantity, unit, Decimal unit cost, calculated amount, source reference, notes, and optional/included treatment.

Supported categories are Material, Labour, Machine, Subcontract, Engineering, Overhead, Packing, Freight, Installation, Travel, Other, and Contingency. Optional lines remain visible but are excluded from the included total.

All calculations are server-authoritative and use `Decimal`:

- line amount = quantity × unit cost, rounded to currency precision;
- markup selling price = total cost × (1 + markup / 100);
- margin selling price = total cost / (1 - margin / 100);
- manual selling price = explicitly entered proposed price;
- gross margin amount = proposed selling price - total cost;
- gross margin percent = gross margin amount / proposed selling price × 100.

## Lifecycle, approval, and revisions

Editable revisions are Draft, In preparation, and Returned for changes. Submission recalculates totals, copies a commercial snapshot into the existing shared approval engine, and locks the revision. Approval, rejection, and return events synchronize the Estimate through the domain-event subscriber.

An approved revision cannot be edited. `New revision` supersedes the old immutable record, copies its cost lines and basis, reopens the Enquiry at Estimation, and creates a new editable revision. Approval of the new current revision restores the Estimation Complete / Ready for Quotation handoff.

## Confidentiality and concurrency

View, create, edit, submit, approve, revise, cost-view, and margin-view are separate permissions. The API removes cost lines/totals and margin/selling-price fields when the caller lacks the relevant confidential permission; hiding UI controls is not the security boundary.

Estimate creation, line mutation, submission, approval sync, numbering, and revision use transactions and row locks. A PostgreSQL concurrency test verifies that simultaneous creation produces one current revision.

