# Owner Administration Guide

## Open Owner Control

Sign in with an account that has `Owner Control` access and choose **Owner control** in the application header. Ordinary employees do not see this entry. The home page groups occasional administration into People & access, Organization, Business rules, Operations, Data & governance, and System readiness.

## Create an employee and login

1. Open **Owner Control → Employees → New employee**.
2. Record the employee identity, company, branch, department, designation and reporting manager.
3. Create the separate login from **Owner Control → User accounts → New user account**. Enter a strong temporary password; passwords are hashed and never displayed again.
4. Edit the Employee and link the User account.
5. Open **Roles & permissions** and create or select the business role, then create a Role assignment for the user at the correct company/branch/department/warehouse/self scope.

Employee identity and login access are intentionally separate. An employee can exist without a login, and disabling a login never deletes employee history.

## Check somebody's access

Open **Access check**, choose a login account and a business action, then select **Explain access**. The result shows Allowed or Denied, the matching role/scope and any direct Allow/Deny exception. A direct Deny takes priority. This is a diagnostic tool, not impersonation.

## Change a role or permission

Open **Roles & permissions**. The role editor groups actions by business area, supports search, group selection and individual actions. Raw permission codes appear only as secondary reference. A manager cannot grant a permission they do not already hold; final Owner continuity is protected.

Use individual permission overrides only for genuine exceptions. Record a clear reason. Prefer fixing the role when the rule applies to the whole team.

## Reassign open work

Open **Work assignment**, filter by work type or responsibility, select one or more open records, and choose **Reassign selected**. Select an active employee and record the reason. The entire batch succeeds or fails together. Completed history is not changed.

If the selected employee already owns an item, that item is treated as already complete for the assignment command and no duplicate Audit entry is created.

## Disable an employee safely

Open the employee profile and choose **Deactivate employee**. The screen first counts open assigned work.

- **Reassign all open work now** transfers supported open work atomically to the chosen active employee.
- **Leave assigned temporarily** keeps current responsibility explicitly; the Data quality and Work assignment pages continue to flag the situation.
- **Cancel** makes no change.

A reason is mandatory. The linked login is disabled, history remains available, and the final Owner cannot be deactivated. Use **Reactivate employee** when employment resumes; enabling the linked login is a separate explicit choice.

To disable only a login, open **User accounts → Disable login**. The same open-work impact check is performed. Existing sessions stop authenticating on subsequent requests through Django's active-user authentication behavior.

## Enable or disable a feature

Open **Feature controls**. Only implemented capabilities have switches. Changing one opens a confirmation dialog and requires a reason. Existing records stay available. Unfinished modules display **Not available yet** and have no switch.

At present, Quick quotation and Website enquiries are controlled. The backend checks the feature even if an old browser temporarily displays a stale action.

## Numbering, approvals, masters and imports

- **Numbering** manages future sequence rules through the existing row-locked engine. Preview the next value; historical documents are not renumbered.
- **Approval rules** uses versioned workflow definitions. Existing requests retain their workflow-version context.
- **Common lists** manages current master data. Deactivate referenced values instead of deleting history.
- Supported registers expose **Import Excel / CSV**, a downloadable template and all-or-nothing validation. Imports currently support organization registers and the commercial registers already implemented.

## Audit, data quality and system readiness

- **Activity history** shows important business/admin events and actors. Owner actions are not hidden.
- **Data quality** lists deterministic issues and a review link. It never edits or merges records automatically.
- **System health** performs safe checks and uses Available, Unavailable, Configured, Unknown or Not configured. Unknown is honest; it is not a hidden success.
- Integration credentials and technical errors are never printed in full.

## Owner versus technical superuser

Business administration should use the Owner Control Centre and RBAC. Django superuser is a technical emergency capability and is not the recommended daily account. Production setup must assign a protected Business Owner role to real active employee accounts and keep a controlled recovery path.

MFA, session revocation administration, credential rotation, job retry controls and external backup/restore telemetry are production-readiness follow-ups; do not claim they are present on the current screen.
