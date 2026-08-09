# Workflow and State Diagrams

Status: Phase 0 baseline. Final transition permissions and approval limits require business confirmation.

## 1. End-to-end operational lifecycle

```mermaid
flowchart LR
    Customer --> Enquiry --> Review["Requirement and engineering review"] --> Estimate --> Approval1["Internal approval"] --> Quotation --> Negotiation --> CPO["Customer PO"] --> SO["Sales order"] --> Project
    Project --> Drawing --> BOM --> MRP --> PR["Purchase requisition"] --> VRFQ["Vendor RFQ"] --> Compare["Vendor comparison"] --> PO["Purchase order"] --> GRN
    GRN --> IQC["Incoming QC"] --> Inventory --> Reservation --> Issue["Material issue"] --> Production --> JobCards["Job cards"] --> IPQC["In-process QC"] --> FQC["Final QC"]
    FQC --> Packing --> Dispatch --> Delivery --> Installation --> Acceptance --> Asset --> Warranty --> Service --> AMC --> Renewal --> Closure["Project closure"]
```

Each arrow represents a validated domain command and auditable handoff, not a free-form status change.

## 2. Enquiry and quotation

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Received: receive
    Received --> UnderReview: start_review
    UnderReview --> EngineeringReview: request_engineering_review
    EngineeringReview --> UnderReview: request_clarification
    EngineeringReview --> Estimation: confirm_feasible
    Estimation --> QuotationPreparation: complete_estimate
    QuotationPreparation --> QuotationSubmitted: submit_quotation
    QuotationSubmitted --> Negotiation: record_customer_response
    Negotiation --> QuotationPreparation: create_revision
    Negotiation --> Won: accept_customer_po
    Negotiation --> Lost: record_loss_reason
    Draft --> Cancelled: cancel
    Received --> Cancelled: cancel
    UnderReview --> Cancelled: cancel
    Won --> [*]
    Lost --> [*]
    Cancelled --> [*]
```

Quotation revisions are immutable. A revision follows Draft → Submitted for Approval → Approved → Sent to Customer. Rejection returns work to a new editable revision; it never mutates an approved revision.

## 3. Drawing, BOM and engineering change

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> InCheck: submit_for_check
    InCheck --> Draft: reject_check
    InCheck --> AwaitingApproval: pass_check
    AwaitingApproval --> Draft: reject_approval
    AwaitingApproval --> Released: approve_and_release
    Released --> Superseded: release_new_revision
    Superseded --> [*]
```

Creating a revision clones the last allowed baseline into a new Draft. Release performs one transaction that validates approvals, marks the prior released revision Superseded, marks the new revision Released, records audit evidence and notifies affected teams. Released content cannot be edited.

```mermaid
flowchart LR
    ECR["Engineering change request"] --> Impact["Impact analysis: cost, stock, purchase, production, customer"] --> ECNApproval["ECN approval"] --> NewDrawing["New drawing revision"] --> NewBOM["New BOM revision if affected"] --> Effective["Controlled effective date"] --> Notify["Notify affected teams"]
```

## 4. Purchase requisition and purchase order

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted: submit
    Submitted --> Approved: approve
    Submitted --> Rejected: reject
    Rejected --> Draft: revise
    Approved --> PartiallyConverted: convert_lines
    Approved --> Converted: convert_all
    PartiallyConverted --> Converted: convert_remaining
    Draft --> Cancelled: cancel
    Submitted --> Cancelled: withdraw_and_cancel
    Approved --> Cancelled: cancel_unconverted_balance
    Converted --> [*]
    Cancelled --> [*]
```

One PR may feed several POs and one PO may consolidate lines from several approved PRs. Conversion quantities are ledgered so remaining quantities are derived, not manually edited.

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingApproval: submit
    PendingApproval --> Draft: reject
    PendingApproval --> Approved: approve
    Approved --> Sent: send_to_vendor
    Sent --> PartiallyReceived: receive_partial
    PartiallyReceived --> Received: receive_balance
    Sent --> Received: receive_all
    Received --> Closed: close
    Draft --> Cancelled: cancel
    Approved --> Cancelled: cancel_before_send
    Sent --> Cancelled: controlled_cancel_open_balance
    Closed --> [*]
    Cancelled --> [*]
```

## 5. Receipt, incoming quality and stock

```mermaid
flowchart LR
    PO["Approved PO"] --> GRN["Record GRN in receiving location"] --> RequiresQC{"Incoming QC required?"}
    RequiresQC -->|"No"| Accept["Post accepted receipt ledger"]
    RequiresQC -->|"Yes"| Inspect["Inspect"]
    Inspect -->|"Accepted"| Accept
    Inspect -->|"Accepted with deviation"| Deviation["Authorized deviation"] --> Accept
    Inspect -->|"Hold"| Hold["Blocked receiving stock"]
    Inspect -->|"Rejected"| Reject["Rejected stock / vendor return"]
    Accept --> Available["Usable inventory"]
```

Goods receipt, PO received quantities, inspection disposition, stock ledger entries and audit events are transactionally consistent. Rejected or held material is never available for issue.

## 6. Inventory reservation and issue

```mermaid
flowchart LR
    Demand["Project / production / service demand"] --> Check["Calculate physical, reserved and available-to-promise"] --> Enough{"Enough stock?"}
    Enough -->|"Yes"| Reserve["Create reservation"] --> Request["Request issue"] --> Lock["Lock relevant stock rows"] --> Validate["Revalidate availability and serial/batch"] --> Issue["Post issue ledger entries"]
    Enough -->|"No"| Shortage["Shortage / MRP suggestion"]
    Validate -->|"Failed"| Message["Human-readable available quantity error"]
```

## 7. Production, quality and dispatch

```mermaid
stateDiagram-v2
    [*] --> Planned
    Planned --> Ready: release_material_and_route
    Ready --> InProgress: start
    InProgress --> Paused: pause
    Paused --> InProgress: resume
    InProgress --> Blocked: quality_or_material_block
    Blocked --> InProgress: clear_block
    InProgress --> Completed: complete_operation
    Planned --> Cancelled: cancel
    Ready --> Cancelled: controlled_cancel
    Completed --> [*]
    Cancelled --> [*]
```

```mermaid
flowchart LR
    Job["Job-card operation"] --> Inspection{"Inspection configured?"}
    Inspection -->|"No"| Next["Next operation"]
    Inspection -->|"Yes"| Result{"Pass?"}
    Result -->|"Yes"| Next
    Result -->|"No"| NCR --> Disposition{"Disposition"}
    Disposition --> Rework --> Job
    Disposition --> Reject
    Disposition --> Authorized["Authorized use-as-is"] --> Next
    Final["Final QC"] --> Approved{"Approved or authorized deviation?"}
    Approved -->|"Yes"| Dispatch
    Approved -->|"No"| BlockDispatch["Dispatch blocked"]
```

## 8. Service request and field execution

```mermaid
stateDiagram-v2
    [*] --> New
    New --> Assigned: assign_engineer
    Assigned --> Scheduled: schedule
    Scheduled --> Travelling: check_in_travel
    Travelling --> InProgress: start_work
    InProgress --> WaitingParts: wait_for_parts
    WaitingParts --> InProgress: resume_with_parts
    InProgress --> WaitingCustomer: request_customer_action
    WaitingCustomer --> InProgress: customer_ready
    InProgress --> Resolved: complete_work
    Resolved --> ConfirmationPending: request_signoff
    ConfirmationPending --> Closed: confirm_and_close
    New --> Cancelled: cancel
    Assigned --> Cancelled: cancel
    Scheduled --> Cancelled: cancel
    Closed --> [*]
    Cancelled --> [*]
```

Closure validates configured requirements: service report, parts, expenses and customer acknowledgement. GPS remains feature-flagged.

## 9. AMC lifecycle

```mermaid
flowchart LR
    Opportunity --> Proposal --> Quotation --> Acceptance --> Contract --> Schedule["PM schedule generation"] --> Visits["Service visits"] --> Billing --> Reminder["90/60/30-day renewal reminders"] --> Renewal
    Renewal -->|"Accepted"| NewTerm["New contract term"]
    Renewal -->|"Not renewed"| Expired
```

## 10. Generic approval state

```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> InProgress: begin_steps
    InProgress --> Approved: all_required_steps_approved
    InProgress --> Rejected: any_required_step_rejected
    Pending --> Withdrawn: withdraw
    Rejected --> Pending: resubmit_new_request
    Approved --> [*]
    Withdrawn --> [*]
```

The approval engine records decisions; the owning domain service performs the resulting domain transition after revalidating current state and dependencies.

## 11. Universal transition checks

Every important command answers:

- Is the current state eligible?
- Does the user have action permission and the correct record/branch/warehouse scope?
- Are mandatory fields, documents and dependencies complete?
- Has another user changed the record since it was loaded?
- What happens to partial quantities and open balances?
- What audit event and notification are required?
- Is the operation atomic, and which rows require locks?
