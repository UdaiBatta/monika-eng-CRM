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
