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
  title: string;
  status: string;
  status_label?: string;
  customer_reference: string;
  due_date: string | null;
  responsible_salesperson_name: string;
  created_at: string;
  updated_at: string;
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
