export type ProductCategory = {
  id: string;
  company: string;
  code: string;
  name: string;
  is_active: boolean;
};

export type Supplier = {
  id: string;
  company: string;
  code: string;
  name: string;
  gstin: string;
  contact_name: string;
  phone: string;
  email: string;
  address: string;
  payment_term: string | null;
  payment_term_name?: string;
  is_active: boolean;
};

export type Product = {
  id: string;
  company: string;
  category: string | null;
  category_name?: string;
  default_supplier: string | null;
  default_supplier_name?: string;
  unit_of_measure: string;
  unit_of_measure_code: string;
  alternates: string[];
  internal_code: string;
  brand: string;
  part_number: string;
  description: string;
  specification: string;
  warranty_months: number;
  reorder_level: string;
  reorder_quantity: string;
  available_quantity: string;
  is_active: boolean;
  record_version: number;
  created_at: string;
  updated_at: string;
};

export type StockCondition =
  | "AVAILABLE"
  | "RESERVED"
  | "DAMAGED"
  | "REPAIR_HELD"
  | "DEMO"
  | "IN_TRANSIT";

export type StockLocation = {
  id: string;
  warehouse: string;
  warehouse_name: string;
  bin_code: string;
};

export type StockItem = {
  id: string;
  product: string;
  product_code: string;
  product_description: string;
  location: string;
  location_label: string;
  condition: StockCondition;
  condition_label: string;
  quantity: string;
};

export type MovementType =
  | "INWARD"
  | "OUTWARD"
  | "RESERVE"
  | "RELEASE_RESERVE"
  | "RETURN"
  | "TRANSFER"
  | "ADJUSTMENT"
  | "PANEL_CONSUMPTION"
  | "SERVICE_CONSUMPTION";

export type StockMovement = {
  id: string;
  company: string;
  movement_number: string;
  movement_type: MovementType;
  movement_type_label: string;
  product: string;
  product_code: string;
  product_description: string;
  quantity: string;
  from_location: string | null;
  from_location_label?: string;
  from_condition: string;
  to_location: string | null;
  to_location_label?: string;
  to_condition: string;
  reference_type: string;
  reference_id: string | null;
  reason: string;
  created_by: string | null;
  created_by_name?: string;
  created_at: string;
};

export type LowStockRow = {
  product_id: string;
  internal_code: string;
  description: string;
  available_quantity: string;
  reorder_level: string;
  reorder_quantity: string;
};
