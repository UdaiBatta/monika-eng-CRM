export type PurchaseRequisitionLine = {
  id: string;
  line_number: number;
  product: string;
  product_code: string;
  product_description: string;
  quantity: string;
  notes: string;
};

export type PurchaseRequisition = {
  id: string;
  company: string;
  requisition_number: string;
  warehouse: string;
  warehouse_name: string;
  requested_by: string;
  requested_by_name: string;
  preferred_supplier: string | null;
  preferred_supplier_name?: string;
  justification: string;
  required_by_date: string | null;
  status: string;
  status_label: string;
  approval_request: string | null;
  approved_by: string | null;
  approved_at: string | null;
  lines: PurchaseRequisitionLine[];
  created_at: string;
  updated_at: string;
};

export type PurchaseOrderLine = {
  id: string;
  line_number: number;
  product: string;
  product_code: string;
  product_description: string;
  description: string;
  quantity: string;
  unit_price: string;
  tax_percent: string;
  line_subtotal: string;
  tax_amount: string;
  total_amount: string;
  received_quantity: string;
  pending_quantity: string;
};

export type PurchaseOrder = {
  id: string;
  company: string;
  po_number: string;
  supplier: string;
  supplier_name: string;
  warehouse: string;
  warehouse_name: string;
  requisition: string | null;
  requisition_number?: string;
  responsible_employee: string;
  responsible_name: string;
  currency: string;
  currency_code: string;
  order_date: string;
  expected_delivery_date: string | null;
  payment_terms: string;
  delivery_terms: string;
  notes: string;
  subtotal: string;
  tax_amount: string;
  grand_total: string;
  invoiced_amount: string;
  paid_amount: string;
  balance_due: string;
  payment_due_date: string | null;
  status: string;
  status_label: string;
  payment_status: string;
  payment_status_label: string;
  lines: PurchaseOrderLine[];
  created_at: string;
  updated_at: string;
};

export type GoodsReceiptLine = {
  id: string;
  order_line: string;
  order_line_number: number;
  product_code: string;
  quantity_received: string;
  condition: string;
};

export type GoodsReceipt = {
  id: string;
  company: string;
  grn_number: string;
  purchase_order: string;
  purchase_order_number: string;
  received_by: string;
  received_by_name: string;
  received_date: string;
  supplier_reference: string;
  notes: string;
  status: string;
  status_label: string;
  confirmed_by: string | null;
  confirmed_at: string | null;
  lines: GoodsReceiptLine[];
  created_at: string;
  updated_at: string;
};
