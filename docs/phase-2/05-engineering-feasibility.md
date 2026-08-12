# Engineering Feasibility Review

## User routes

- \`/app/crm/engineering\`
- \`/app/crm/engineering/:reviewId\`

The engineering queue supports unassigned, mine, in-review, clarification, and completed work. The review workspace keeps the commercial scope, technical assessment, clarifications, shared documents, approvals, history, and revisions together.

## Controlled lifecycle

\`PENDING -> IN_REVIEW -> CLARIFICATION_REQUIRED -> FEASIBLE | NOT_FEASIBLE\`

\`CANCELLED\` and \`SUPERSEDED\` remain controlled terminal states. Results are \`FEASIBLE\`, \`FEASIBLE_WITH_CONDITIONS\`, or \`NOT_FEASIBLE\`. Clarifications move through \`OPEN\`, \`RESPONDED\`, \`CLOSED\`, or \`CANCELLED\`.

The supported commands are assign, start, update assessment, request clarification, respond, close, complete, mark not feasible, and reassess. Completed reviews cannot be edited. Reassessment preserves the completed revision and creates a new current revision.

## Ready for Estimation gate

The workspace reports READY FOR ESTIMATION only when:

- the current review has a feasible result;
- every clarification is closed;
- all mandatory assessment fields are complete; and
- the configured approval, when required, is approved.

This is a computed milestone. Phase 2 does not create an Estimate, Quotation, Project, Drawing, or BOM.

## Main APIs

- \`GET /api/v1/engineering-reviews/?queue=...\`
- \`GET /api/v1/engineering-reviews/{id}/workspace/\`
- \`GET /api/v1/engineering-reviews/{id}/revisions/\`
- command actions \`assign\`, \`start\`, \`assessment\`, \`request-clarification\`, \`complete\`, \`mark-not-feasible\`, and \`reassess\`
- clarification actions \`respond\` and \`close\`

## Controls

The module uses company-scoped querysets, permission codes for view/assign/start/edit/clarify/complete/reassess/sensitive access, PostgreSQL row locks, a unique current-revision constraint, immutable completed decisions, database indexes, shared audit history, private documents, notifications, and the existing approval engine.
