export type SalesOrder = {
  id: string
  date: string
  customer: string
  customerPo: string
  project: string
  amount: string
  deliveryDate: string
  salesperson: string
  status: string
  progress: number
  stage: string
}

export const salesOrders: SalesOrder[] = [
  { id: "SO-260184", date: "24 Jul 2026", customer: "Apex Process Systems", customerPo: "APS/PO/4817", project: "Solvent Recovery Skid", amount: "₹48,75,000", deliveryDate: "28 Aug 2026", salesperson: "Neha Shah", status: "In Production", progress: 68, stage: "Production" },
  { id: "SO-260176", date: "19 Jul 2026", customer: "Bharat Heavy Electricals", customerPo: "BHEL/PS/7782", project: "Boiler Feed Pump Package", amount: "₹1,24,50,000", deliveryDate: "15 Sep 2026", salesperson: "Arjun Mehta", status: "Engineering", progress: 34, stage: "Engineering" },
  { id: "SO-260165", date: "14 Jul 2026", customer: "Thermax Limited", customerPo: "THERMAX/PO/618", project: "Heat Exchanger System", amount: "₹67,80,000", deliveryDate: "05 Sep 2026", salesperson: "Neha Shah", status: "Awaiting PO", progress: 12, stage: "Enquiry" },
  { id: "SO-260152", date: "08 Jul 2026", customer: "Reliance Industries", customerPo: "RIL/MEP/3090", project: "Ammonia Storage Tank", amount: "₹2,18,40,000", deliveryDate: "20 Aug 2026", salesperson: "Vikram Iyer", status: "Ready to Dispatch", progress: 94, stage: "Dispatch" },
  { id: "SO-260141", date: "02 Jul 2026", customer: "Larsen & Toubro", customerPo: "L&T/PO/9845", project: "Cooling Tower Package", amount: "₹93,25,000", deliveryDate: "25 Sep 2026", salesperson: "Arjun Mehta", status: "Quality Hold", progress: 82, stage: "Quality" },
  { id: "SO-260130", date: "27 Jun 2026", customer: "GAIL (India) Limited", customerPo: "GAIL/PO/2211", project: "Gas Filtration Skid", amount: "₹56,10,000", deliveryDate: "10 Oct 2026", salesperson: "Neha Shah", status: "Engineering", progress: 26, stage: "Engineering" },
  { id: "SO-260121", date: "21 Jun 2026", customer: "ONGC Limited", customerPo: "ONGC/PO/5566", project: "Instrument Air Dryer", amount: "₹31,45,000", deliveryDate: "18 Sep 2026", salesperson: "Vikram Iyer", status: "Procurement", progress: 51, stage: "Procurement" },
  { id: "SO-260110", date: "15 Jun 2026", customer: "Adani Power", customerPo: "APL/PO/7789", project: "Coal Handling System", amount: "₹1,75,60,000", deliveryDate: "12 Nov 2026", salesperson: "Arjun Mehta", status: "In Production", progress: 63, stage: "Production" },
]

export const workItems = [
  { id: "WK-1082", task: "Approve revised GA drawing", context: "PRJ-2026-0148 · Engineering", due: "Today, 11:30 AM", priority: "High", status: "Approval pending" },
  { id: "WK-1087", task: "Release purchase indent for SS plate", context: "PRJ-2026-0148 · Materials", due: "Today, 1:00 PM", priority: "Critical", status: "Material shortage" },
  { id: "WK-1091", task: "Review hydro test results", context: "PRJ-2026-0129 · Quality", due: "Today, 3:00 PM", priority: "Medium", status: "Review due" },
  { id: "WK-1094", task: "Confirm dispatch vehicle", context: "PRJ-2026-0112 · Dispatch", due: "Today, 4:30 PM", priority: "High", status: "Not confirmed" },
  { id: "WK-1098", task: "Submit customer visit report", context: "SR-260481 · Service", due: "Today, 5:30 PM", priority: "Medium", status: "Report pending" },
]

export const projectShortages = [
  { item: "P-1023", description: "SS 316L Plate 10 mm", required: "12 Nos", available: "0", requiredDate: "12 Aug 2026", impact: "Critical" },
  { item: "P-1087", description: "CS Shell Plate 25 mm", required: "6 Nos", available: "2 Nos", requiredDate: "14 Aug 2026", impact: "High" },
  { item: "P-2045", description: "DWG Butterfly Valve 6 in", required: "4 Nos", available: "1 No", requiredDate: "18 Aug 2026", impact: "High" },
  { item: "P-3012", description: "Instrumentation Cable", required: "250 m", available: "80 m", requiredDate: "20 Aug 2026", impact: "Medium" },
]

export const projectJobs = [
  { job: "JOB-26-071", description: "Skid Base Frame", workCenter: "FAB-01", due: "16 Aug", status: "In Progress" },
  { job: "JOB-26-072", description: "Vessel V-101", workCenter: "FAB-02", due: "19 Aug", status: "In Progress" },
  { job: "JOB-26-073", description: "Piping Spool Set-01", workCenter: "PIPE-01", due: "21 Aug", status: "Not Started" },
  { job: "JOB-26-074", description: "Electrical Panel", workCenter: "ELEC-01", due: "24 Aug", status: "Blocked" },
]

export const pendingQc = [
  { id: "QC-26-198", item: "Vessel V-101 · RT Joint", type: "RT", raised: "07 Aug", priority: "High" },
  { id: "QC-26-199", item: "Piping Spool · Hydro Test", type: "HT", raised: "08 Aug", priority: "High" },
  { id: "QC-26-200", item: "Skid Base · Dimensional Check", type: "DC", raised: "08 Aug", priority: "Medium" },
]

export const documents = [
  { number: "PRJ-26-0148-DRG-0001", title: "GA Drawing · Solvent Recovery Skid", revision: "B", type: "Drawing", owner: "Neha Shah" },
  { number: "PRJ-26-0148-QP-0001", title: "Quality Plan", revision: "A", type: "Quality Plan", owner: "Vikram Patel" },
  { number: "PRJ-26-0148-ITP-0002", title: "Inspection Test Plan · Piping", revision: "A", type: "ITP", owner: "Suresh Joshi" },
]

export const recentActivity = [
  { time: "Today · 10:15 AM", title: "Production progress updated to 68%", meta: "Ramesh Kumar · JOB-26-071", tone: "info" },
  { time: "Today · 9:20 AM", title: "GRN-26-0554 received for PO-26-098", meta: "Stores · SS 316L Pipe", tone: "success" },
  { time: "Yesterday · 4:45 PM", title: "QC-26-198 raised for Vessel V-101", meta: "Quality · Radiography", tone: "warning" },
  { time: "Yesterday · 11:30 AM", title: "GA drawing revision B uploaded", meta: "Neha Shah · Engineering", tone: "info" },
]

export const purchaseRequisitions = [
  { id: "PR-260348", project: "PRJ-2026-0148", item: "SS 316L Plate 10 mm", qty: "12 Nos", required: "12 Aug", buyer: "Pooja Nair", status: "RFQ Pending" },
  { id: "PR-260344", project: "PRJ-2026-0148", item: "Butterfly Valve 6 in", qty: "4 Nos", required: "18 Aug", buyer: "Pooja Nair", status: "Quote Review" },
  { id: "PR-260339", project: "PRJ-2026-0137", item: "Siemens PLC S7-1200", qty: "2 Nos", required: "25 Aug", buyer: "Amit Desai", status: "Approved" },
  { id: "PR-260331", project: "PRJ-2026-0129", item: "CS Seamless Pipe 4 in", qty: "80 m", required: "20 Aug", buyer: "Pooja Nair", status: "PO Created" },
]

export const purchaseOrders = [
  { id: "PO-260198", vendor: "Jindal Stainless Ltd.", project: "PRJ-2026-0148", amount: "₹8,42,000", due: "13 Aug", status: "Overdue" },
  { id: "PO-260191", vendor: "Flowserve India", project: "PRJ-2026-0148", amount: "₹5,18,500", due: "18 Aug", status: "Acknowledged" },
  { id: "PO-260187", vendor: "Siemens Ltd.", project: "PRJ-2026-0137", amount: "₹3,76,000", due: "25 Aug", status: "In Transit" },
  { id: "PO-260179", vendor: "Ratnamani Metals", project: "PRJ-2026-0129", amount: "₹6,24,800", due: "20 Aug", status: "Part Received" },
]

export const inventoryStock = [
  { code: "RM-SS-PL-10", item: "SS 316L Plate 10 mm", location: "RM-YARD-A2", available: "0 Nos", reserved: "12 Nos", reorder: "8 Nos", status: "Critical" },
  { code: "VL-BFV-06", item: "Butterfly Valve 6 in", location: "ST-BIN-V14", available: "1 No", reserved: "4 Nos", reorder: "2 Nos", status: "Short" },
  { code: "CB-INST-2P", item: "Instrumentation Cable 2 Pair", location: "ST-CAB-C03", available: "80 m", reserved: "250 m", reorder: "150 m", status: "Short" },
  { code: "FG-MS-WN-150", item: "MS Flange WN 150# 6 in", location: "ST-FLG-B11", available: "24 Nos", reserved: "10 Nos", reorder: "12 Nos", status: "Healthy" },
]

export type ServiceRequest = {
  id: string
  customer: string
  asset: string
  site: string
  visit: string
  engineer: string
  priority: string
  status: string
}

export const serviceRequests: ServiceRequest[] = [
  { id: "SR-260487", customer: "Apex Process Systems", asset: "Solvent Recovery Skid · SRS-4418", site: "Apex Plant 1 · Pune", visit: "11 Aug 2026 · 10:30 AM", engineer: "Rohan Patil", priority: "High", status: "Visit Scheduled" },
  { id: "SR-260486", customer: "Bharat Chemicals", asset: "Distillation Column · DC-2201", site: "Dahej Site · Gujarat", visit: "09 Aug 2026 · 2:00 PM", engineer: "Kiran Jadhav", priority: "Medium", status: "On Site" },
  { id: "SR-260485", customer: "Sigma Pharma", asset: "Chiller Unit · CH-1180", site: "Hyderabad Unit", visit: "08 Aug 2026 · 11:00 AM", engineer: "Vikas More", priority: "High", status: "Report Pending" },
  { id: "SR-260484", customer: "Nova Petrochem", asset: "Boiler Package · BP-3320", site: "Panoli Plant · Gujarat", visit: "06 Aug 2026 · 9:30 AM", engineer: "Rohan Patil", priority: "Medium", status: "Closed" },
]
