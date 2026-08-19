# Multi-user Working Guide

## The simple rule

Use the ERP record as the source of truth. Do not rely on a verbal “I am handling it” as the only coordination mechanism.

## Assigned To

**Assigned To** or **Responsible** identifies the person currently expected to move the work forward. Team queues show shared work; My Work filters to your responsibility; Unassigned means somebody still needs to take it.

## Take This

Where a queue provides **Take This**, the database decides the winner. If two employees click together, one assignment succeeds and the other receives a readable conflict. Do not create a second record to work around that message—open the record that was just assigned.

## Presence

“Rahul is viewing/editing this record” is advisory awareness. It helps avoid duplicated effort but does not lock the record and does not monitor keystrokes, screenshots, mouse movement or productivity.

## If somebody saves while you are editing

Important versioned forms reject an old save instead of overwriting the newer record. Load the latest version and review your values before saving again. The database never silently chooses the older edit.

## Live, reconnecting and offline

- **Live** means committed changes can reach the screen immediately.
- **Reconnecting** means live delivery is recovering.
- **Offline / updates delayed** means refresh if a decision depends on current ownership.

HTTP saves remain authoritative even when live delivery is unavailable. After reconnect, the application refetches current server state.

## Completed and released work

Status and related-record links show when a business action already happened. Do not repeat a send, release, conversion, Sales Order creation or Project creation because somebody else completed it. Released and historical revisions are read-only; use the domain's revision, amendment, cancel or supersede action when available.

## If work moved or was completed by somebody else

Open the current record, read the latest status/responsible employee/history, and continue only if the next action belongs to you. If your screen reports a conflict, never create a duplicate as a shortcut. Ask a manager or Owner to reassign work when responsibility is wrong.
