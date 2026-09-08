export type Equipment = {
  id: string;
  company: string;
  customer: string;
  customer_name: string;
  site: string | null;
  site_label?: string;
  product: string | null;
  product_code?: string;
  equipment_name: string;
  make_model: string;
  serial_number: string;
  installation_date: string | null;
  warranty_expiry: string | null;
  under_warranty: boolean;
  notes: string;
  is_active: boolean;
};

export type ServiceJobLine = {
  id: string;
  line_number: number;
  line_type: "PART" | "LABOUR";
  line_type_label: string;
  product: string | null;
  product_code?: string;
  description: string;
  quantity: string;
  unit_price: string;
  total_amount: string;
  consumed_quantity: string;
};

export type ServiceTicketStageEvent = {
  id: string;
  from_status: string;
  from_status_label: string;
  to_status: string;
  to_status_label: string;
  notes: string;
  actor_name: string;
  occurred_at: string;
};

export type ServiceTicket = {
  id: string;
  company: string;
  ticket_number: string;
  customer: string;
  customer_name: string;
  contact: string | null;
  contact_name?: string;
  equipment: string | null;
  equipment_name?: string;
  source: string;
  source_label: string;
  complaint: string;
  priority: string;
  priority_label: string;
  status: string;
  status_label: string;
  technician: string | null;
  technician_name?: string;
  scheduled_visit_at: string | null;
  diagnosis: string;
  quotation: string | null;
  quotation_number?: string;
  repair_notes: string;
  warranty_claim: boolean;
  dispatched_at: string | null;
  dispatch_reference: string;
  closed_at: string | null;
  job_lines: ServiceJobLine[];
  stage_events: ServiceTicketStageEvent[];
  created_at: string;
  updated_at: string;
};
