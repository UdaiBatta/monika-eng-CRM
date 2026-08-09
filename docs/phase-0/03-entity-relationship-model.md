# Entity Relationship Model

Status: conceptual Phase 0 model. Physical field definitions and migrations are produced at each implementation phase.

## 1. Shared conventions

Important entities use UUID primary keys, separate official document numbers, audit timestamps/actors and controlled status fields. Controlled documents use a stable root record plus immutable revision records.

## 2. Identity, organization and control

```mermaid
erDiagram
    USER ||--o| EMPLOYEE : "may represent"
    EMPLOYEE }o--|| DEPARTMENT : belongs_to
    EMPLOYEE }o--|| DESIGNATION : has
    EMPLOYEE }o--o| EMPLOYEE : reports_to
    EMPLOYEE }o--|| BRANCH : assigned_to
    BRANCH ||--o{ WAREHOUSE : owns
    WAREHOUSE ||--o{ ZONE : contains
    ZONE ||--o{ RACK : contains
    RACK ||--o{ BIN : contains
    USER ||--o{ USER_ROLE : has
    ROLE ||--o{ USER_ROLE : assigned
    ROLE ||--o{ ROLE_PERMISSION : grants
    PERMISSION ||--o{ ROLE_PERMISSION : included
    USER ||--o{ ACCESS_EXCEPTION : receives
    APPROVAL_RULE ||--o{ APPROVAL_RULE_STEP : defines
    APPROVAL_REQUEST ||--o{ APPROVAL_STEP : contains
    EMPLOYEE ||--o{ APPROVAL_STEP : decides
    USER ||--o{ AUDIT_EVENT : performs
```

Scope grants/exceptions can reference department, branch, warehouse, ownership rules and field policies. Exact role assignments remain configurable.

## 3. Customer-to-project lifecycle

```mermaid
erDiagram
    CUSTOMER ||--o{ CUSTOMER_CONTACT : has
    CUSTOMER ||--o{ CUSTOMER_ADDRESS : has
    CUSTOMER ||--o{ CRM_ACTIVITY : has
    CUSTOMER ||--o{ ENQUIRY : raises
    ENQUIRY ||--o{ ENGINEERING_REVIEW : reviewed_by
    ENQUIRY ||--o{ ESTIMATE : estimated_as
    ESTIMATE ||--o{ ESTIMATE_REVISION : versioned_as
    ENQUIRY ||--o{ QUOTATION : quoted_as
    QUOTATION ||--o{ QUOTATION_REVISION : versioned_as
    QUOTATION_REVISION ||--o{ QUOTATION_LINE : contains
    QUOTATION ||--o{ NEGOTIATION_EVENT : discussed_in
    QUOTATION_REVISION ||--o| SALES_ORDER : accepted_as
    SALES_ORDER ||--o{ SALES_ORDER_LINE : contains
    SALES_ORDER ||--o{ DELIVERY_SCHEDULE : schedules
    SALES_ORDER ||--o{ PROJECT : creates
    CUSTOMER ||--o{ PROJECT : owns
    PROJECT ||--o{ PROJECT_MILESTONE : tracks
    PROJECT ||--o{ TASK : has
    PROJECT ||--o{ COMMENT : has
```

Conversion services copy approved source data once and retain references; users do not manually re-enter accepted quotation data.

## 4. Engineering and planning

```mermaid
erDiagram
    PROJECT ||--o{ DRAWING : has
    DRAWING ||--o{ DRAWING_REVISION : versioned_as
    DRAWING_REVISION ||--o{ DRAWING_BOM_LINK : references
    BOM_REVISION ||--o{ DRAWING_BOM_LINK : references
    PROJECT ||--o{ ENGINEERING_CHANGE : controls
    ENGINEERING_CHANGE }o--o{ DRAWING_REVISION : affects
    ENGINEERING_CHANGE }o--o{ BOM_REVISION : affects
    PRODUCT ||--o{ BOM : standard_bom
    PROJECT ||--o{ BOM : project_bom
    BOM ||--o{ BOM_REVISION : versioned_as
    BOM_REVISION ||--o{ BOM_ITEM : contains
    BOM_ITEM }o--|| MATERIAL : requires
    BOM_ITEM }o--o| BOM_REVISION : child_assembly
    PRODUCT ||--o{ ROUTING : has
    PROJECT ||--o{ ROUTING : may_override
    ROUTING ||--o{ ROUTING_REVISION : versioned_as
    ROUTING_REVISION ||--o{ ROUTING_OPERATION : orders
    ROUTING_OPERATION }o--|| WORK_CENTRE : runs_at
    ROUTING_OPERATION }o--o| MACHINE : may_use
    BOM_REVISION ||--o{ MRP_RUN : plans
    MRP_RUN ||--o{ MRP_REQUIREMENT : calculates
```

Only one released/current revision is allowed per drawing/BOM/routing root, enforced by service logic and database constraints.

## 5. Procurement, receipt and inventory

```mermaid
erDiagram
    MRP_REQUIREMENT ||--o{ PURCHASE_REQUISITION_LINE : suggests
    PURCHASE_REQUISITION ||--o{ PURCHASE_REQUISITION_LINE : contains
    PURCHASE_REQUISITION_LINE }o--|| MATERIAL : requests
    PURCHASE_REQUISITION_LINE }o--o{ VENDOR_RFQ_LINE : sourced_as
    VENDOR_RFQ ||--o{ VENDOR_RFQ_VENDOR : invites
    VENDOR ||--o{ VENDOR_RFQ_VENDOR : receives
    VENDOR_RFQ_VENDOR ||--o{ VENDOR_QUOTE_LINE : responds_with
    VENDOR_COMPARISON ||--o{ VENDOR_COMPARISON_LINE : compares
    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_LINE : contains
    PURCHASE_ORDER_LINE }o--o{ PURCHASE_REQUISITION_LINE : fulfils
    PURCHASE_ORDER ||--o{ GOODS_RECEIPT : received_by
    GOODS_RECEIPT ||--o{ GOODS_RECEIPT_LINE : contains
    GOODS_RECEIPT_LINE ||--o{ INSPECTION : inspected_by
    INSPECTION ||--o{ INSPECTION_RESULT : records
    GOODS_RECEIPT_LINE ||--o{ STOCK_TRANSACTION : posts_after_acceptance
    MATERIAL ||--o{ STOCK_TRANSACTION : moves
    WAREHOUSE ||--o{ STOCK_TRANSACTION : locates
    BIN ||--o{ STOCK_TRANSACTION : locates
    MATERIAL ||--o{ STOCK_RESERVATION : reserves
    PROJECT ||--o{ STOCK_RESERVATION : owns
    STOCK_RESERVATION ||--o{ MATERIAL_ISSUE_LINE : consumed_by
```

Stock balance is derived from accepted ledger transactions. Reservations affect available-to-promise stock without changing physical stock.

## 6. Production, quality and dispatch

```mermaid
erDiagram
    PROJECT ||--o{ PRODUCTION_ORDER : has
    PRODUCTION_ORDER }o--|| BOM_REVISION : freezes
    PRODUCTION_ORDER }o--|| ROUTING_REVISION : freezes
    PRODUCTION_ORDER ||--o{ JOB_CARD : creates
    JOB_CARD }o--|| ROUTING_OPERATION : executes
    JOB_CARD ||--o{ PRODUCTION_ENTRY : records
    JOB_CARD ||--o{ MATERIAL_ISSUE_LINE : consumes
    JOB_CARD ||--o{ INSPECTION : requires
    INSPECTION ||--o{ NCR : may_raise
    NCR ||--o{ CAPA : may_require
    JOB_WORK_ORDER }o--|| JOB_CARD : outsources
    JOB_WORK_ORDER }o--|| VENDOR : assigned_to
    PRODUCTION_ORDER ||--o{ FINISHED_ITEM : produces
    FINISHED_ITEM ||--o{ PACKING_ITEM : packed_as
    PACKING_LIST ||--o{ PACKING_ITEM : contains
    PROJECT ||--o{ DISPATCH : ships
    DISPATCH ||--o{ DISPATCH_LINE : contains
    DISPATCH ||--o{ DELIVERY_CONFIRMATION : confirms
    DISPATCH ||--o{ INSTALLATION_JOB : triggers
```

Final-QC approval is a dispatch prerequisite unless an authorized, audited deviation exists.

## 7. Assets, service and AMC

```mermaid
erDiagram
    CUSTOMER ||--o{ CUSTOMER_ASSET : owns
    PROJECT ||--o{ CUSTOMER_ASSET : supplied
    CUSTOMER_ASSET ||--o{ WARRANTY_PERIOD : covered_by
    CUSTOMER_ASSET ||--o{ SERVICE_REQUEST : reported_for
    SERVICE_REQUEST ||--o{ SERVICE_JOB_CARD : creates
    EMPLOYEE ||--o{ SERVICE_ASSIGNMENT : receives
    SERVICE_JOB_CARD ||--o{ SERVICE_ASSIGNMENT : scheduled_as
    SERVICE_JOB_CARD ||--o{ SERVICE_VISIT : executed_as
    SERVICE_VISIT ||--o{ SERVICE_PART : uses
    SERVICE_VISIT ||--o{ SERVICE_PHOTO : documents
    SERVICE_VISIT ||--o| CUSTOMER_SIGNOFF : accepted_by
    SERVICE_VISIT ||--o{ SERVICE_EXPENSE : incurs
    CUSTOMER ||--o{ AMC_OPPORTUNITY : has
    AMC_OPPORTUNITY ||--o{ AMC_PROPOSAL : quoted_as
    AMC_PROPOSAL ||--o| AMC_CONTRACT : accepted_as
    AMC_CONTRACT }o--o{ CUSTOMER_ASSET : covers
    AMC_CONTRACT ||--o{ PM_SCHEDULE : plans
    PM_SCHEDULE ||--o{ SERVICE_JOB_CARD : generates
    AMC_CONTRACT ||--o{ AMC_BILLING_SCHEDULE : bills
    AMC_CONTRACT ||--o{ AMC_RENEWAL : renews
```

## 8. Documents, comments and events

```mermaid
erDiagram
    DOCUMENT ||--o{ DOCUMENT_VERSION : versioned_as
    DOCUMENT_VERSION }o--|| STORED_OBJECT : stored_as
    DOCUMENT ||--o{ DOCUMENT_LINK : linked_by
    AUDIT_EVENT }o--|| USER : actor
    NOTIFICATION }o--|| EMPLOYEE : recipient
    TASK }o--|| EMPLOYEE : assignee
```

`DOCUMENT_LINK`, audit subject references, comments and tasks use a controlled content-type/reference mechanism with service validation. They do not grant access by themselves.

## 9. Physical-model rules reserved for phase design

- Human-readable numbering and uniqueness scopes.
- Revision uniqueness and one-current constraints.
- Check constraints for non-negative quantities and valid date ranges.
- Deferred constraints for balanced accounting entries.
- Partial receipt, issue and dispatch quantities computed from immutable line movements.
- Serial/batch uniqueness and traceability rules activated by material flags.
- Retention policies for audit, finance, engineering and HR documents.
