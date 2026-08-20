# Phase 3 Staff Guide

## Sales role: what you can access

The standard **Sales** role is company-wide for commercial work. It can review and assign incoming enquiries, maintain customers and follow-ups, create and progress quotations, record Customer POs, prepare and submit Sales Orders, view the resulting Projects, prepare the Sales-to-Engineering handoff, and answer Engineering clarifications.

The standard role cannot approve or release its own Sales Order, accept a critical Customer PO difference, cancel operational records, or take Engineering ownership. Those actions remain with an authorized manager or Engineering role. The Home page shows this boundary in plain language under **Your access**.

## Sales: record a Customer PO

Open **Customer POs** and choose **Record Customer PO**. Enter the customer, PO number and date, received date, value, related quotation when available, and upload the original customer document. Less common delivery, payment, and note fields are under **More details**.

If the PO differs from the quotation, the system says **Differences Need Review** and shows the human-readable differences. It does not silently change the quotation or order.

## Sales: create and release a Sales Order

Use **Create Sales Order** from the Sales Order register, or **Create Sales Order** in a quotation that is Ready for Sales Order.

- **From quotation** prefills the accepted customer-facing lines and terms.
- **Direct Sales Order** is shown only with permission. Choose the genuine business reason, record how the customer confirmed, and enter at least one order line.
- Leave **Customer PO pending** on when the customer has confirmed but the formal PO will arrive later.

Review customer, prices, tax, delivery, payment, warranty, scope, and PO state. Save the draft and choose **Submit for approval**. An authorized manager approves and releases the order. Release protects the current revision. If project work is required, Project 360 is created automatically.

To change a released order, choose **Create amendment**. Do not edit released history. When the amendment is later released, Engineering sees a commercial-change warning in Project 360.

## Sales: send the Project to Engineering

Open Project 360 and the **Engineering handoff** tab. Enter the project scope and technical requirement first. Add customer specifications, special commercial commitments, assumptions, open questions, and Sales notes when useful. Save, then choose **Send to Engineering**.

If Engineering asks a question, open the same handoff tab and choose **Respond**. The answer remains attached to the Project.

## Engineering: daily work

Open **Engineering work**. Use:

- **Unassigned** for new handoffs nobody owns;
- **Assigned to me** for your work;
- **Engineering queue** for all active handoffs.

Open a Project and choose **Take This**. If another engineer just took it, the system stops the second assignment and shows the current owner.

Review Overview, Commercial, Customer PO, and Engineering handoff. Choose **Ask Sales a question** if information is missing. Choose **Accept Handoff** only after open questions are answered. The final status means **Project Ready for Detailed Engineering**; it does not mean drawings or BOM have been created.

## Hold, cancel, and realtime

Authorized staff can put Sales Orders or Projects on hold, resume them, or cancel them with a reason. These actions are audited. Live updates are a convenience; PostgreSQL and the API remain authoritative, so normal reads and writes remain safe if realtime temporarily reconnects.
