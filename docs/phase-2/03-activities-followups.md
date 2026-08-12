# CRM Activities and Follow-ups

The Phase 2 UI reuses `CrmActivity`; no second task or activity system was created.

## Supported work

Employees with permission can record calls, emails, meetings, visits, notes, and follow-ups. A follow-up has an owner, due time, priority, and controlled lifecycle. The work area supports operational queues such as due, upcoming, overdue, and completed.

Customer 360 and Enquiry 360 include the same records in context. The customer timeline also combines relevant immutable business events so employees can understand what happened without reading audit JSON.

## Commands

- create an activity or follow-up;
- complete an open follow-up;
- cancel or reschedule only where the existing backend permits it.

Direct arbitrary status editing is not used.

## Shared-service behavior

- permission and company scope are enforced in Django;
- completion is transaction safe and audited;
- assigned employees receive existing notification events where configured;
- timestamps are stored timezone-aware and displayed in Asia/Kolkata;
- history is preserved when a customer or employee becomes inactive.
