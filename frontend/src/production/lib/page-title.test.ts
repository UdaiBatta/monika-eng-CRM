import { describe, expect, it } from "vitest";

import { getPageTitle } from "./page-title";

describe("getPageTitle", () => {
  it.each([
    ["/app/crm/customers/9d632db7-62b7-4a58-a644-27f4e4395692", "Customer 360"],
    ["/app/crm/enquiries/4b793ff5-8d1a-470c-8f5b-823ac91320b8", "Enquiry 360"],
    ["/app/crm/engineering/9b87c68f-1a6e-49c7-92a1-99f4a5d14790", "Workshop Review"],
    ["/app/workshop/reviews/9b87c68f-1a6e-49c7-92a1-99f4a5d14790", "Workshop Review"],
    ["/app/documents/a88292da-33e4-43dd-b8e7-68c163953f79", "Document details"],
    ["/app", "My Work"],
    ["/app/settings", "Tools & settings"],
  ])("uses a business title for %s", (path, expected) => {
    expect(getPageTitle(path)).toBe(expected);
  });
});
