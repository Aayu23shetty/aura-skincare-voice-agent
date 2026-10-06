# 3–5 Minute Demo Script

## 0:00–0:30 — Product intro

“Aria is a browser-based customer-support agent for Aura Skincare. The goal is not a fancy UI; it is a controlled voice workflow that can answer policy questions and use an order tool when it needs live order data.”

## 0:30–1:30 — Order lookup

Start the call and say:

“Where is order ORD-101?”

Expected: Aria identifies the order, uses `get_order_details`, and says it is Out for Delivery with BlueDart, expected by 6 PM today.

Follow with:

“Can I cancel it?”

Expected: no. It is already Out for Delivery.

## 1:30–2:20 — Policy guardrail

Say:

“I bought this 20 days ago and opened it. Can I return it?”

Expected: Aria explains the 7-day and unopened/unused policy without promising a refund.

## 2:20–2:50 — Graceful degradation

Say:

“Where is order ORD-999?”

Expected: Aria does not invent a result.

Then:

“Can you book me a flight to Goa?”

Expected: Aria declines the out-of-scope request politely.

## 2:50–3:40 — Post-call result

End the call and show:

- chronological customer/agent transcript;
- structured JSON;
- detected intent;
- order ID when present;
- resolution status.

## 3:40–5:00 — Architecture

Show:

- `app/agent.py`
- `get_order_details`
- policy prompt
- `data/orders.json`
- browser voice layer
- `/api/chat` and `/api/summary`

Close with the production improvement: realtime streaming + interruption handling.
