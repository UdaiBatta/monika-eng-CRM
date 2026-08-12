import type {
  AuditEvent,
  ERPDocument,
  Identifier,
} from "@/production/lib/types";

export type CustomerContact = {
  id: Identifier;
  customer: Identifier;
  display_name: string;
  first_name: string;
  last_name: string;
  title: string;
  department: string;
  email: string;
  phone: string;
  alternate_phone: string;
  is_primary: boolean;
  preferred_contact_method: string;
  notes: string;
  is_active: boolean;
};

export type CustomerSite = {
  id: Identifier;
  customer: Identifier;
  address_type: string;
  label: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  district: string;
  state: string;
  country: string;
  postal_code: string;
  gstin: string;
  contact: Identifier | null;
  phone: string;
  is_default: boolean;
  is_active: boolean;
};

export type Customer = {
  id: Identifier;
  company: Identifier;
  company_name: string;
  customer_code: string;
  legal_name: string;
  trade_name: string;
  customer_type: string;
  gstin?: string;
  pan?: string;
  cin?: string;
  industry: string;
  website: string;
  primary_email: string;
  primary_phone: string;
  account_manager: Identifier | null;
  account_manager_name: string;
  credit_limit?: string | null;
  payment_term?: Identifier | null;
  default_currency: Identifier;
  default_tax?: Identifier | null;
  status: string;
  source: string;
  notes: string;
  primary_contact?: CustomerContact | null;
  contacts?: CustomerContact[];
  sites?: CustomerSite[];
  created_at: string;
  updated_at: string;
  last_activity_at?: string | null;
};

export type CrmActivity = {
  id: Identifier;
  company: Identifier;
  customer: Identifier;
  customer_code: string;
  customer_name: string;
  enquiry: Identifier | null;
  contact: Identifier | null;
  contact_name: string;
  activity_type: string;
  subject: string;
  description: string;
  activity_date: string;
  next_follow_up_at: string | null;
  follow_up_owner: Identifier | null;
  follow_up_owner_name: string;
  priority: string;
  status: string;
  is_overdue: boolean;
  created_by_name: string;
};

export type EnquirySummary = {
  id: Identifier;
  enquiry_number: string;
  subject: string;
  status: string;
  customer_reference: string;
  due_date: string | null;
  responsible_salesperson_name: string;
  customer: Identifier;
  customer_code: string;
  customer_name: string;
  priority: string;
  estimated_value: string | null;
  currency_code: string;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
};

export type EnquiryRequirement = {
  id: Identifier;
  enquiry: Identifier;
  requirement_type: string;
  title: string;
  description: string;
  is_mandatory: boolean;
  customer_specification_reference: string;
  notes: string;
};

export type EnquiryItem = {
  id: Identifier;
  enquiry: Identifier;
  line_number: number;
  description: string;
  customer_reference: string;
  quantity: string;
  uom: Identifier;
  uom_code: string;
  technical_specification: string;
  requested_delivery: string | null;
  notes: string;
};

export type Enquiry = EnquirySummary & {
  company: Identifier;
  company_name: string;
  customer_contact: Identifier | null;
  customer_contact_name: string;
  customer_site: Identifier | null;
  customer_site_name: string;
  source: string;
  received_date: string;
  description: string;
  responsible_salesperson: Identifier;
  currency: Identifier | null;
  lost_reason: string;
  cancellation_reason: string;
  competitor: string;
  customer_feedback: string;
  closed_at: string | null;
  requirements: EnquiryRequirement[];
  items: EnquiryItem[];
};

export type EnquiryWorkspace = {
  enquiry: Enquiry;
  next_follow_up: CrmActivity | null;
  activities: CrmActivity[];
  documents: ERPDocument[];
  timeline: CustomerTimelineItem[];
  engineering_review?: {
    id: Identifier;
    revision_number: number;
    status: string;
    result: string;
    assigned_engineer_name: string;
    open_clarifications: number;
    ready_for_estimation: boolean;
  } | null;
};

export type EngineeringClarification = {
  id: Identifier;
  company: Identifier;
  review: Identifier;
  subject: string;
  question: string;
  context: string;
  status: string;
  assigned_to: Identifier;
  assigned_to_name: string;
  due_at: string | null;
  requested_by_name: string;
  requested_at: string;
  response: string;
  responded_by_name: string;
  responded_at: string | null;
  closed_by_name: string;
  closed_at: string | null;
  closure_comment: string;
  is_overdue: boolean;
};

export type EngineeringReview = {
  id: Identifier;
  company: Identifier;
  enquiry: Identifier;
  enquiry_number: string;
  enquiry_subject: string;
  customer_id: Identifier;
  customer_code: string;
  customer_name: string;
  due_date: string | null;
  priority: string;
  sales_owner_name: string;
  revision_number: number;
  is_current: boolean;
  status: string;
  assigned_engineer: Identifier | null;
  assigned_engineer_name: string;
  started_at: string | null;
  started_by_name: string;
  completed_at: string | null;
  completed_by_name: string;
  result: string;
  technical_summary: string;
  feasibility_notes: string;
  assumptions: string;
  exclusions: string;
  constraints: string;
  risks: string;
  special_materials: string;
  outsourced_processes: string;
  tooling_requirements: string;
  testing_requirements: string;
  customer_clarification_summary: string;
  preliminary_drawing_notes: string;
  preliminary_bom_notes: string;
  preliminary_routing_notes: string;
  engineering_hours: string | null;
  manufacturing_hours: string | null;
  lead_time_days: number | null;
  completion_comment: string;
  supersedes: Identifier | null;
  open_clarifications: number;
  ready_for_estimation: boolean;
  approval: {
    required: boolean;
    status: string;
    request_id: Identifier | null;
    workflow_name: string;
  };
  clarifications: EngineeringClarification[];
  created_at: string;
  updated_at: string;
};

export type EngineeringWorkspace = {
  review: EngineeringReview;
  enquiry: Enquiry;
  documents: ERPDocument[];
  approvals: Array<{
    id: Identifier;
    workflow_name: string;
    status: string;
    status_label: string;
    current_step_name: string | null;
    requested_at: string;
  }>;
  timeline: AuditEvent[];
};

export type CustomerTimelineItem = {
  kind: string;
  occurred_at: string;
  summary: string;
  actor_name?: string;
  activity_type?: string;
  action?: string;
};

export type Customer360 = {
  customer: Customer;
  overview: {
    open_follow_ups: number;
    open_enquiries: number;
    won_enquiries: number;
    lost_enquiries: number;
    last_contact: CrmActivity | null;
    next_follow_up: CrmActivity | null;
  };
  recent_activities: CrmActivity[];
  open_follow_ups: CrmActivity[];
  recent_enquiries: EnquirySummary[];
  recent_documents: ERPDocument[];
  timeline: CustomerTimelineItem[];
};

export type RelationOption = {
  id: Identifier;
  name?: string;
  code?: string;
  display_name?: string;
  employee_code?: string;
  title?: string;
  rate_name?: string;
};

export type CustomerFormValues = {
  legal_name: string;
  trade_name: string;
  customer_type: string;
  gstin: string;
  pan: string;
  cin: string;
  industry: string;
  website: string;
  primary_email: string;
  primary_phone: string;
  account_manager: string;
  credit_limit: string;
  payment_term: string;
  default_currency: string;
  default_tax: string;
  source: string;
  notes: string;
  duplicate_override_reason: string;
};

export type EntityHistory = AuditEvent[];

export type ExternalEnquiryAttachment = {
  id: Identifier;
  safe_display_filename: string;
  original_filename: string;
  mime_type: string;
  extension: string;
  size_bytes: number;
  checksum_sha256: string;
  validation_status: string;
  scan_status: string;
  promoted_document: Identifier | null;
  uploaded_at: string;
};

export type ExternalEnquirySubmission = {
  id: Identifier;
  company: Identifier;
  external_submission_id: string;
  channel: string;
  channel_label: string;
  source_type: string;
  received_at: string;
  submitted_at: string | null;
  person_name: string;
  company_name: string;
  email: string;
  phone: string;
  subject: string;
  message: string;
  product_reference: string;
  product_name: string;
  product_url: string;
  source_page_url: string;
  referrer_url?: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_term?: string;
  utm_content?: string;
  spam_status: string;
  spam_score: string | null;
  review_status: string;
  duplicate_status: string;
  matched_customer: Identifier | null;
  matched_customer_name: string;
  matched_contact: Identifier | null;
  matched_contact_name: string;
  converted_customer: Identifier | null;
  converted_customer_name: string;
  converted_contact: Identifier | null;
  converted_contact_name: string;
  converted_enquiry: Identifier | null;
  converted_enquiry_number: string;
  assigned_to: Identifier | null;
  assigned_to_name: string;
  priority: string;
  reviewed_at: string | null;
  converted_at: string | null;
  rejection_reason: string;
  attachments: ExternalEnquiryAttachment[];
  source_history: Array<{
    id: Identifier;
    channel: string;
    channel_label: string;
    source_reference: string;
    original_message: string;
    captured_by: Identifier | null;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
};

export type QuotationLine = {
  id: Identifier;
  line_number: number;
  item_code: string;
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
  is_optional: boolean;
  notes: string;
};

export type QuotationRevision = {
  id: Identifier;
  revision_number: number;
  record_version: number;
  status: string;
  currency: Identifier;
  currency_code: string;
  issue_date: string;
  valid_until: string | null;
  introduction: string;
  scope: string;
  inclusions: string;
  exclusions: string;
  assumptions: string;
  payment_terms: string;
  delivery_terms: string;
  warranty_terms: string;
  freight_terms: string;
  customer_notes: string;
  subtotal: string;
  discount_amount: string;
  taxable_amount: string;
  tax_amount: string;
  grand_total: string;
  frozen_at: string | null;
  frozen_reason: string;
  approval_request: Identifier | null;
  sent_at: string | null;
  lines: QuotationLine[];
  communications: Array<{
    id: Identifier;
    channel: string;
    channel_label: string;
    direction: string;
    occurred_at: string;
    summary: string;
    manual_reference: string;
  }>;
  negotiations: Array<{
    id: Identifier;
    channel: string;
    channel_label: string;
    occurred_at: string;
    summary: string;
    customer_request: string;
    our_response: string;
    commercial_impact: string;
    material_change: boolean;
    follow_up_at: string | null;
  }>;
  generated_documents: Array<{
    id: Identifier;
    status: string;
    docx_document: Identifier;
    docx_title: string;
    pdf_document: Identifier | null;
    pdf_title: string;
    pdf_error: string;
    created_at: string;
  }>;
};

export type Quotation = {
  id: Identifier;
  company: Identifier;
  quotation_number: string;
  customer: Identifier;
  customer_name: string;
  customer_code: string;
  customer_contact: Identifier | null;
  enquiry: Identifier | null;
  enquiry_number: string;
  estimate: Identifier | null;
  estimate_number: string;
  path: string;
  path_label: string;
  quick_reason: string;
  status: string;
  status_label: string;
  owner: Identifier;
  owner_name: string;
  current_revision: QuotationRevision;
  commercial_confirmation?: {
    id: Identifier;
    method: string;
    method_label: string;
    confirmed_at: string;
    confirmation_reference: string;
    notes: string;
    po_pending: boolean;
    po_number: string;
    po_date: string | null;
    po_document: Identifier | null;
    ready_for_sales_order_at: string | null;
  } | null;
  created_at: string;
  updated_at: string;
};

export type ExternalEnquiryCandidates = {
  customers: Array<{
    id: Identifier;
    customer_code: string;
    legal_name: string;
    status: string;
    reasons: string[];
  }>;
  contacts: Array<{
    id: Identifier;
    display_name: string;
    customer_id: Identifier;
    customer_code: string;
    customer_name: string;
    reasons: string[];
  }>;
};

export type EstimateCostLine = {
  id: Identifier;
  estimate: Identifier;
  line_number: number;
  category: string;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_cost: string;
  amount: string;
  source_reference: string;
  notes: string;
  is_optional: boolean;
};

export type CommercialEstimate = {
  id: Identifier;
  company: Identifier;
  enquiry: Identifier;
  enquiry_number: string;
  enquiry_subject: string;
  customer_id: Identifier;
  customer_code: string;
  customer_name: string;
  sales_owner_name: string;
  engineering_review: Identifier;
  engineering_review_revision: number;
  estimate_number: string;
  revision_number: number;
  is_current: boolean;
  status: string;
  currency: Identifier;
  currency_code: string;
  currency_symbol: string;
  pricing_method?: string;
  markup_percent?: string;
  target_margin_percent?: string;
  manual_selling_price?: string | null;
  total_cost?: string;
  proposed_selling_price?: string;
  gross_margin_amount?: string;
  gross_margin_percent?: string;
  category_totals?: Record<string, string>;
  assumptions: string;
  exclusions: string;
  commercial_notes: string;
  technical_reference_summary: string;
  prepared_by_name: string;
  submitted_at: string | null;
  submitted_by_name: string;
  approved_at: string | null;
  approved_by_name: string;
  approval_request: Identifier | null;
  approval_status: string;
  supersedes: Identifier | null;
  cost_lines?: EstimateCostLine[];
  created_at: string;
  updated_at: string;
};

export type EstimateWorkspace = {
  estimate: CommercialEstimate;
  enquiry: Enquiry;
  documents: ERPDocument[];
  approvals: Array<{
    id: Identifier;
    workflow_name: string;
    status: string;
    status_label: string;
    current_step_name: string | null;
    requested_at: string;
  }>;
  timeline: AuditEvent[];
};
