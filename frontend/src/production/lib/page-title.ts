const detailTitles: Array<[RegExp, string]> = [
  [/^\/app\/employees\/[^/]+\/edit$/, "Edit employee"],
  [/^\/app\/employees\/[^/]+$/, "Employee profile"],
  [/^\/app\/documents\/[^/]+$/, "Document details"],
  [/^\/app\/approvals\/[^/]+$/, "Approval details"],
  [/^\/app\/crm\/customers\/[^/]+$/, "Customer 360"],
  [/^\/app\/crm\/enquiries\/[^/]+$/, "Enquiry 360"],
  [/^\/app\/crm\/website-enquiries\/[^/]+$/, "Website enquiry review"],
  [/^\/app\/crm\/engineering\/[^/]+$/, "Engineering review"],
];

const listTitles: Record<string, string> = {
  app: "Workspace overview",
  activities: "Activities & follow-ups",
  engineering: "Engineering reviews",
  enquiries: "Enquiries & RFQs",
  "website-enquiries": "Website enquiry inbox",
};

export function getPageTitle(pathname: string) {
  const detailTitle = detailTitles.find(([pattern]) => pattern.test(pathname))?.[1];
  if (detailTitle) return detailTitle;
  const segment = pathname.split("/").filter(Boolean).at(-1) ?? "app";
  return listTitles[segment] ?? segment.replaceAll("-", " ");
}
