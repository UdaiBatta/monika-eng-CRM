# In-Application Notification Engine

Status: implementation and automated verification complete on 2026-08-10; final signed-in browser acceptance pending.

## Behavior

`Notification` is a recipient-isolated in-app inbox record with severity, message, controlled record link, read time, archive time and deduplication key. `NotificationPreference` stores user preference architecture without claiming email, SMS or WhatsApp delivery.

The notification service is subscribed to domain events after database commit. It handles new approval assignments, reassignment and final decisions. A transaction rollback creates no notification. A post-commit delivery error is logged and may be retried; it never rolls back a valid approval. Inactive accounts are not selected for new interactive notifications, while historical notifications remain preserved.

## API and UI

The recipient-scoped routes support paginated list, unread count, read, unread, read-all and archive actions plus preference retrieval/update. Users cannot choose or manipulate another recipient. `notifications.notification.view` and `.manage_preferences` control access.

The production shell contains an Axis notification bell and unread count. The notification sheet groups actionable items, opens validated internal application routes and supports read/read-all behavior. `/app/settings/notifications` explains and manages the currently supported in-app channel.

## Deferred channels

Email, SMS, WhatsApp, digest schedules, escalations and quiet hours are intentionally not delivered in Phase 1. They must reuse this preference/event/idempotency architecture rather than create separate business notification rules.
