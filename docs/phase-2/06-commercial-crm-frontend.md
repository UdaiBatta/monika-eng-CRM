# Commercial CRM Frontend

## Axis design contract

The production CRM keeps the accepted Axis industrial language: near-black/navy surfaces, a compact left navigation rail, orange active states and actions, dense information cards, restrained borders, concise tables, and green success gates. The UI is operational and data-backed; it does not copy the reference's fake Project, Drawing, BOM, production, or costing data.

Desktop uses a persistent navigation rail. Mobile uses a drawer, stacked cards, and horizontally scrollable tab rows without page-level overflow. Permissions hide unavailable navigation and the API independently rejects unauthorized access.

## Operator guide

1. Create a customer from Customers, then add the working contact and site in Customer 360.
2. Create the RFQ from Enquiries and record its customer reference, commercial dates, requirements, and Decimal-quantity items.
3. Upload the RFQ in Documents and link it to the enquiry.
4. Record calls, emails, meetings, notes, or follow-ups in context.
5. Receive the enquiry, start commercial review, and send it to engineering.
6. In Engineering reviews, assign and start the review, save the assessment, and raise structured clarifications when needed.
7. Respond to and close each clarification. Complete the review only when the technical decision is justified.
8. Treat READY FOR ESTIMATION as the end of this release. It is not an estimate or quotation.

Marking a review not feasible records a controlled technical outcome. Reassess creates a new revision; it does not rewrite the old decision.

## Production routes

- \`/app/crm/customers\` and Customer 360
- \`/app/crm/enquiries\`, enquiry creation, and Enquiry 360
- \`/app/crm/engineering\` and Engineering Review
- \`/app/crm/activities\`

Loading, empty, validation, error, and access-restricted states are present. The accepted Axis mockup routes remain available as visual reference material.
