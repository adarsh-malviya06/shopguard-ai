"""Policy documents for ShopGuard AI knowledge base.

Each function returns the full Markdown text for a policy document.
These are loaded by the RAG seeding script.
"""

REFUND_POLICY = """
# Refund Policy

## Overview
ShopGuard AI facilitates refund review requests for eligible orders.
No direct financial refunds are executed by this system.
All cases are routed to the operations team for approval.

## Eligibility
- Refund requests must be submitted within **30 days** of the delivery date.
- The product must be unused, undamaged by the customer, and in original packaging (for physical goods).
- Digital goods, books, and perishable items are **non-refundable** unless defective.
- Orders with a status of **CANCELLED** before shipment are automatically flagged for refund review.

## Ineligible Situations
- Requests submitted more than 30 days after delivery.
- Products showing signs of customer-caused damage.
- Non-returnable product categories (books, digital, consumables).
- Duplicate refund requests for the same order.

## Process
1. Customer submits a refund review request via ShopGuard AI.
2. The system verifies order ownership and eligibility.
3. A refund review case is created and assigned to the operations team.
4. The operations team processes the case within 5–7 business days.
5. The customer is notified of the decision.

## Refund Processing Time
Once approved, refunds are credited within **7–10 business days** to the original payment method.

## Damaged or Defective Products
If you received a damaged or defective item, submit a refund or return request within 30 days.
Please retain the packaging and product for potential courier investigation.
"""

SHIPPING_POLICY = """
# Shipping Policy

## Standard Delivery Timelines
- Metro cities: **2–4 business days**
- Tier-2 cities: **4–6 business days**
- Rural areas: **6–10 business days**

## Delayed Shipments
A shipment is considered delayed if it has not been delivered within **48 hours after the estimated delivery date**.

If your package has not moved in the tracking system for more than **48 hours**, the case qualifies for investigation.

## Stuck Shipments
If a shipment event shows the package stalled at a distribution hub for more than **24 hours** with no subsequent movement, the case is escalated to the carrier operations team.

## Courier Partners
We use BlueDart, DTDC, Delhivery, and Xpressbees depending on your region.
Tracking numbers are assigned at dispatch and are available in your order details.

## Shipment Damage
If your package arrives with visible damage, note the condition before accepting delivery.
Report damaged packages within **48 hours** of receipt.
Photograph the damaged packaging and product before use.

## Missing Deliveries
If the tracking shows "Delivered" but you have not received the package:
1. Check with neighbours and building reception.
2. Wait 24 hours (couriers sometimes mark early).
3. If still missing after 24 hours, raise a missing-delivery investigation.
"""

CANCELLATION_POLICY = """
# Cancellation Policy

## When You Can Cancel
Orders can be cancelled only if their status is **PLACED** or **PROCESSING**.
Once an order status changes to **SHIPPED**, it cannot be cancelled.
Delivered orders must follow the **Refund Policy**.

## How to Cancel
Submit a cancellation request via ShopGuard AI.
The system checks current order status before confirming the cancellation.
Cancellations require explicit confirmation from the customer before execution.

## Cancellation After Payment
If payment was made:
- For eligible cancellations (PLACED/PROCESSING), the amount is flagged for refund review.
- Refunds after cancellation follow the standard refund processing timeline of 7–10 business days.

## Seller-Initiated Cancellations
In rare cases (stock unavailability), the seller may cancel the order.
In such cases, a full refund review is automatically initiated.

## Non-Cancellable Orders
- Orders that have already been shipped.
- Customised or personalised products after production has started.
- Digital goods and software licences after download.
"""

SUPPORT_PROCEDURES = """
# Customer Support Procedures

## Escalation Path
1. **Self-Service via ShopGuard AI**: Check order status, policy, and raise requests.
2. **Automated Investigation**: ShopGuard AI investigates delays, stuck packages, and refund delays.
3. **Human Support Escalation**: Complex, high-severity, or disputed cases are routed to human agents.

## When Human Review Is Required
- Duplicate or suspicious refund requests.
- Cases where AI investigation cannot determine a conclusive root cause.
- Disputes involving shipment loss or high-value orders.
- Security or fraud concerns.
- Refund requests outside the standard 30-day window.

## Response Time Commitments
- Standard inquiries: Responded within **1 business day**.
- Escalated cases: Responded within **2–3 business days**.
- Urgent or high-severity cases: Responded within **4 hours** during business hours.

## Required Information for Support
When escalating, please provide:
- Order ID.
- Customer ID or registered email.
- Description of the issue.
- Any relevant photographs (for damaged or missing items).

## Prohibited Requests
Support agents and automated systems are not permitted to:
- Execute direct financial refunds.
- Modify payment method or bank details.
- Delete or alter audit records.
- Override ownership verification.
"""
