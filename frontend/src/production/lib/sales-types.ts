export type SalesOrderLine = {
  id: string;
  line_number: number;
  product: string | null;
  product_code?: string;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_price: string;
  discount_percent: string;
  tax_percent: string;
  line_subtotal: string;
  discount_amount: string;
  taxable_amount: string;
  tax_amount: string;
  total_amount: string;
  delivery_text: string;
  customer_visible_note: string;
};

export type SalesOrderRevision = {
  id: string;
  revision_number: number;
  record_version: number;
  status: string;
  status_label: string;
  currency_code: string;
  order_date: string;
  requested_delivery: string | null;
  promised_delivery: string | null;
  payment_terms: string;
  delivery_terms: string;
  warranty_terms: string;
  freight_terms: string;
  installation_terms: string;
  scope: string;
  exclusions: string;
  customer_notes: string;
  internal_notes?: string;
  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  grand_total: string;
  approval_request: string | null;
  revision_reason: string;
  released_at: string | null;
  created_at: string;
  updated_at: string;
  lines: SalesOrderLine[];
};

export type CustomerPORevision = {
  id: string;
  revision_number: number;
  customer_revision_reference: string;
  po_date: string;
  received_date: string;
  currency_code: string;
  stated_total: string | null;
  delivery_information: string;
  payment_terms: string;
  warranty_terms: string;
  notes: string;
  match_status: string;
  match_status_label: string;
  variance_snapshot: Array<{
    field: string;
    label: string;
    quotation: unknown;
    customer_po: unknown;
  }>;
  document_title: string;
  supporting_document: string | null;
  created_at: string;
};

export type CustomerPO = {
  id: string;
  company: string;
  customer: string;
  customer_name: string;
  po_number: string;
  quotation: string | null;
  quotation_number: string;
  responsible_name: string;
  status: string;
  status_label: string;
  current_revision: CustomerPORevision;
  revisions: CustomerPORevision[];
  created_at: string;
  updated_at: string;
};

export type SalesOrder = {
  id: string;
  company: string;
  financial_year: string;
  sales_order_number: string;
  customer: string;
  customer_name: string;
  contact_name: string;
  site_name: string;
  accepted_quotation: string | null;
  quotation_number: string;
  customer_purchase_order: string | null;
  customer_po_number: string;
  order_mode: "QUOTATION_BASED" | "DIRECT";
  order_mode_label: string;
  responsible_name: string;
  project_required: boolean;
  po_pending: boolean;
  direct_reason: string;
  status: string;
  status_label: string;
  project_id: string | null;
  project_number: string;
  current_revision: SalesOrderRevision;
  revisions: SalesOrderRevision[];
  created_at: string;
  updated_at: string;
};

export type ProjectClarification = {
  id: string;
  question: string;
  response: string;
  status: string;
  status_label: string;
  respond_to_name: string;
  requested_by_name: string;
  responded_by_name: string;
  response_document: string | null;
  response_document_title: string;
  due_date: string | null;
  created_at: string;
  responded_at: string | null;
};

export type ProjectHandoff = {
  id: string;
  record_version: number;
  project_scope_summary: string;
  technical_requirement_summary: string;
  customer_specifications: string;
  special_commercial_commitments: string;
  technical_assumptions: string;
  open_questions: string;
  sales_notes: string;
  assigned_engineer: string | null;
  assigned_engineer_name: string;
  status: string;
  status_label: string;
  submitted_at: string | null;
  accepted_at: string | null;
  clarifications: ProjectClarification[];
};

export type ProjectActivity = {
  id: string;
  action: string;
  summary: string;
  actor: string;
  occurred_at: string;
};

export type ProjectDocument = {
  id: string;
  title: string;
  category: string;
  relationship: string;
  filename: string;
  updated_at: string;
};

export type Project = {
  id: string;
  company: string;
  project_number: string;
  project_name: string;
  customer_name: string;
  contact_name: string;
  site_name: string;
  customer_project_reference: string;
  customer_po_reference: string;
  sales_owner_name: string;
  project_owner_name: string;
  engineering_owner_name: string;
  status: string;
  status_label: string;
  priority: string;
  priority_label: string;
  target_completion: string | null;
  customer_delivery_commitment: string;
  commercial_change_pending: boolean;
  current_commercial_baseline: string;
  previous_commercial_baseline: string;
  next_action: string;
  open_clarification_count: number;
  record_version: number;
  sales_order_detail: SalesOrder;
  customer_po_detail: CustomerPO | null;
  engineering_handoff: ProjectHandoff;
  documents: ProjectDocument[];
  activity: ProjectActivity[];
  created_at: string;
  updated_at: string;
};
