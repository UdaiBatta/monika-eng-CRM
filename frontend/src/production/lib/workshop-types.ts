export type PanelJobMaterialLine = {
  id: string;
  line_number: number;
  product: string;
  product_code: string;
  product_description: string;
  required_quantity: string;
  reserved_quantity: string;
  issued_quantity: string;
  consumed_quantity: string;
  returned_quantity: string;
  shortage_quantity: string;
  notes: string;
};

export type PanelJobStageEvent = {
  id: string;
  from_status: string;
  from_status_label: string;
  to_status: string;
  to_status_label: string;
  notes: string;
  actor_name: string;
  occurred_at: string;
};

export type PanelJob = {
  id: string;
  company: string;
  panel_job_number: string;
  project: string;
  project_number: string;
  panel_name: string;
  panel_reference: string;
  warehouse: string;
  warehouse_name: string;
  workshop_owner: string | null;
  workshop_owner_name?: string;
  status: string;
  status_label: string;
  requirement_notes: string;
  target_completion: string | null;
  quality_check_notes: string;
  quality_passed: boolean | null;
  handover_notes: string;
  handed_over_at: string | null;
  material_lines: PanelJobMaterialLine[];
  stage_events: PanelJobStageEvent[];
  created_at: string;
  updated_at: string;
};
