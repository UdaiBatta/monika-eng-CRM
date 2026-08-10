# Configurable Approval Engine

Status: Phase 1G complete and locally verified on 2026-08-10.

## Configuration and history

`ApprovalWorkflow` owns a company-scoped record-type definition. Immutable activated `ApprovalWorkflowVersion` records contain ordered `ApprovalStepDefinition` and safe `ApprovalCondition` rows. Conditions use an allowlisted field/operator evaluator; executable expressions are never accepted. Phase 1 supports specific-user and permission-based company resolvers without inventing Monika Engineers' real hierarchy.

Runtime history is stored in `ApprovalRequest`, `ApprovalStepInstance`, `ApprovalAssignment` and `ApprovalDecision`. Names, workflow version and record reference are snapshotted so completed history survives workflow replacement, role change and employee deactivation.

## Commands and safety

Submission, approve, reject, return for changes, cancel and administrative reassignment are explicit POST commands. Decisions lock the request, current step and assignment in PostgreSQL, enforce the state machine, verify current assignment and permission, block duplicate/racing decisions and block self-approval by default. Rejection and return require a comment. Draft versions expose an explicit self-approval policy switch.

An administrator with `approvals.workflow.manage` can reassign a pending item from an inactive/unavailable employee to another active, company-authorized approver. The former assignment remains in permanent history, the reassignment is audited, and the replacement notification is scheduled after commit.

## Integration and UI

Document submission may include `supporting_document_ids`; links are created in the same transaction and retain independent document-view/download authorization. Audit is synchronous for each material transition. Approval notifications are post-commit and deduplicated.

The Axis routes `/app/approvals`, `/app/approvals/:id` and `/app/settings/approval-workflows` provide task queues, complete decision context/history, deliberate confirmation, supporting files, submission, reassignment and versioned workflow administration.

Relevant permissions include workflow view/manage and request view/submit/approve/reject/return/cancel. Permission and assignment are both required; neither alone grants a decision.

## Business decisions still required

Real approval workflows, approver hierarchy, amount thresholds, SLAs/escalations and module-specific conditions must be agreed with Monika Engineers before CRM or operational rollout. No production approval matrix is seeded automatically.
