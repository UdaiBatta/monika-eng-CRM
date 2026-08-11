# Incoming Enquiries and Quotations: Staff Guide

This guide describes the local Phase 2 CRM workflow in plain language. What you can see or change depends on your permissions.

## Record an incoming enquiry

Open **CRM -> Incoming enquiries** and select **Record incoming enquiry**.

- For a phone call, choose **Phone** and write the customer's original request as clearly as possible.
- For WhatsApp, choose **WhatsApp** and copy the relevant customer wording. Attach the RFQ when available.
- For email or an in-person discussion, choose the matching source.
- For TradeIndia, choose **TradeIndia**. This records where the lead came from; the CRM is not claiming a live TradeIndia connection.

Add the person's name, company, phone/email, subject, original message, and received time. Save the entry, review the possible duplicates, then either take ownership or assign it through the normal review flow.

## Review website and TradeIndia enquiries

Website enquiries appear in the same **Incoming enquiries** list with a Website source label. Open the record to inspect the submitted details, source/security history, attachments, and duplicate suggestions. Do not convert a suspicious or incomplete request until it has been reviewed.

TradeIndia records use the same review process. Confirm the source, inspect suggested customers, and convert or link the record. The source stays visible after conversion.

## See who is handling an enquiry

The list and detail page show the current owner. **Shared queue** means nobody has taken responsibility yet. Use **Take ownership** when you will handle it. The page may also show active viewers; this is awareness only and does not lock the record.

## Prepare a standard quotation

Use the standard path for normal engineered jobs:

1. Complete the enquiry and engineering review.
2. Obtain an approved current commercial estimate.
3. Open **CRM -> Quotations** and select **Start quotation**.
4. Choose **Approved estimate**, then the eligible enquiry/estimate.
5. Review the customer-facing items, validity, tax, payment, delivery, warranty, and other terms.
6. Save the draft and finalize it. If an approval workflow is configured, complete that approval before sending.

Only selling information is copied to the quotation. Internal cost and margin details are not customer-facing.

## Prepare a quick quotation

Use the quick path only when the controlled standard path is not appropriate, such as a repeat job or known replacement item.

1. Open **CRM -> Quotations -> Start quotation**.
2. Choose **Quick quotation**.
3. Select an active customer or prospect.
4. Give a clear reason for using the quick path.
5. Enter the first customer-facing item, quantity, unit, rate, and tax.
6. Save and continue through the normal finalize, send, negotiate, and confirmation controls.

If the option is missing, your role does not have quick-quotation permission.

## Generate Word and PDF

Open the quotation's **Documents** tab. Choose the active approved quotation template and select **Generate**. The system stores the Word file in shared Documents and tries to create a PDF when the server has LibreOffice configured.

If PDF conversion is unavailable, the Word file remains valid and visible. Ask the system administrator to configure the approved template or PDF converter; do not recreate the quotation just because PDF conversion failed.

## Record that a quotation was sent

Open **Communication**, select how it was shared (Phone, WhatsApp, Email, Print, or In person), add the date/reference/notes, and save. This records what actually happened; it does not send a WhatsApp message or email for you.

Once communication is recorded, that revision is frozen. Customer-visible changes must be made in a new revision.

## Record a phone discussion or negotiation

Open **Negotiation**, record the customer's request and your notes, mark whether it is a material commercial change, and set a follow-up when needed. A material change should lead to a new quotation revision.

## Revise a quotation

Open **Revisions** and select **Create new revision**. The previous shared revision remains unchanged. Edit the new draft, save, and compare it with the earlier revision before finalizing and sharing it.

## Record customer confirmation and PO status

After the quotation has been shared, open **Confirmation**.

1. Choose Phone/Verbal, WhatsApp, Email, or Purchase Order.
2. Record the date, reference, and clear notes.
3. If the customer has agreed but the PO will arrive later, select **PO pending**.
4. Attach the PO later when it is received.
5. When the commercial handoff is complete, select **Mark Ready for Sales Order**.

The system never forces a PO, customer portal, or PDF for a genuine verbal confirmation. It also does not create a Sales Order at this stage.

## Understand collaboration messages

- **Live** means updates from colleagues can reach the screen automatically.
- **Reconnecting** means the CRM is restoring the live connection. Normal saved work still uses the server safely.
- **Offline** means live notifications are unavailable. Refresh before making a critical decision.
- **Someone is here/editing** means another permitted employee has the same record open. Coordinate before changing commercial terms.
- **A newer version exists** means somebody saved after you opened the draft. Your unsaved text is preserved on screen, but it cannot overwrite the newer work. Copy anything you need, select **Load latest**, and apply the change again.
- **Ready for Sales Order** means the customer-facing commercial work is accepted and ready for the future order process. No Sales Order has been created.
