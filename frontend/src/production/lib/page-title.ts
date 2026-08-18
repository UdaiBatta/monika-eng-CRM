const detailTitles: Array<[RegExp, string]> = [
  [/^\/app\/employees\/[^/]+\/edit$/, "Edit employee"],
  [/^\/app\/employees\/[^/]+$/, "Employee profile"],
  [/^\/app\/documents\/[^/]+$/, "Document details"],
  [/^\/app\/approvals\/[^/]+$/, "Approval details"],
  [/^\/app\/crm\/customers\/[^/]+$/, "Customer 360"],
  [/^\/app\/crm\/enquiries\/[^/]+$/, "Enquiry 360"],
  [/^\/app\/crm\/website-enquiries\/[^/]+$/, "Website enquiry review"],
  [/^\/app\/crm\/incoming-enquiries\/[^/]+$/, "Incoming enquiry review"],
  [/^\/app\/crm\/engineering\/[^/]+$/, "Engineering review"],
  [/^\/app\/crm\/estimates\/[^/]+$/, "Commercial estimate"],
  [/^\/app\/crm\/quotations\/[^/]+$/, "Quotation workspace"],
  [/^\/app\/sales\/orders\/[^/]+$/, "Sales Order 360"],
  [/^\/app\/projects\/[^/]+$/, "Project 360"],
];

const listTitles: Record<string, string> = {
  app: "Home",
  activities: "Follow-ups",
  engineering: "Engineering checks",
  enquiries: "Active enquiries",
  "website-enquiries": "Website enquiry inbox",
  "incoming-enquiries": "New enquiries",
  estimates: "Cost estimates",
  quotations: "Quotations",
  "customer-pos": "Customer purchase orders",
  orders: "Sales orders",
  projects: "Projects",
  work: "Engineering work",
  settings: "Tools & settings",
  warehouses: "Inventory & workshop",
};

export function getPageTitle(pathname: string) {
  const detailTitle = detailTitles.find(([pattern]) => pattern.test(pathname))?.[1];
  if (detailTitle) return detailTitle;
  const segment = pathname.split("/").filter(Boolean).at(-1) ?? "app";
  return listTitles[segment] ?? segment.replaceAll("-", " ");
}
