const detailTitles: Array<[RegExp, string]> = [
  [/^\/app\/employees\/[^/]+\/edit$/, "Edit employee"],
  [/^\/app\/employees\/[^/]+$/, "Employee profile"],
  [/^\/app\/documents\/[^/]+$/, "Document details"],
  [/^\/app\/approvals\/[^/]+$/, "Approval details"],
  [/^\/app\/crm\/customers\/[^/]+$/, "Customer 360"],
  [/^\/app\/crm\/enquiries\/[^/]+$/, "Enquiry 360"],
  [/^\/app\/crm\/website-enquiries\/[^/]+$/, "Website enquiry review"],
  [/^\/app\/crm\/incoming-enquiries\/[^/]+$/, "Incoming enquiry review"],
  [/^\/app\/(?:crm\/engineering|workshop\/reviews)\/[^/]+$/, "Workshop Review"],
  [/^\/app\/crm\/estimates\/[^/]+$/, "Commercial estimate"],
  [/^\/app\/crm\/quotations\/[^/]+$/, "Quotation workspace"],
  [/^\/app\/sales\/orders\/[^/]+$/, "Sales Order 360"],
  [/^\/app\/projects\/[^/]+$/, "Project 360"],
  [/^\/app\/workshop\/panel-jobs\/[^/]+$/, "Panel Job"],
  [/^\/app\/owner\/work$/, "Owner Control · Work assignment"],
  [/^\/app\/owner\/people$/, "Owner Control · User accounts"],
  [/^\/app\/owner\/access$/, "Owner Control · Access check"],
  [/^\/app\/owner\/features$/, "Owner Control · Features"],
  [/^\/app\/owner\/data-quality$/, "Owner Control · Data quality"],
  [/^\/app\/owner\/system-health$/, "Owner Control · System health"],
];

const listTitles: Record<string, string> = {
  app: "My Work",
  activities: "Follow-ups",
  engineering: "Workshop Review",
  workshop: "My Workshop Work",
  sales: "Quotations & Orders",
  enquiries: "Enquiries",
  "website-enquiries": "Website enquiry inbox",
  "incoming-enquiries": "New enquiries",
  estimates: "Cost estimates",
  quotations: "Quotations",
  "customer-pos": "Customer purchase orders",
  orders: "Sales orders",
  projects: "Projects",
  work: "Workshop Work",
  settings: "Tools & settings",
  warehouses: "Warehouses",
  owner: "Owner Control Centre",
};

export function getPageTitle(pathname: string) {
  const detailTitle = detailTitles.find(([pattern]) => pattern.test(pathname))?.[1];
  if (detailTitle) return detailTitle;
  const segment = pathname.split("/").filter(Boolean).at(-1) ?? "app";
  return listTitles[segment] ?? segment.replaceAll("-", " ");
}
