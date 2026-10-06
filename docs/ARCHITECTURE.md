# Architecture Notes

## Request lifecycle

1. The customer speaks into the browser.
2. Browser speech recognition converts speech to text.
3. The browser posts the conversation history to `/api/chat`.
4. Flask adds the Aura policy and available tool definition.
5. The model can answer directly or request `get_order_details`.
6. Flask executes the tool against `data/orders.json`.
7. The tool result is returned to the model.
8. The final short answer is returned to the browser.
9. Browser speech synthesis speaks the answer.
10. The same transcript is sent to `/api/summary` when the call ends.

## Trust boundaries

The browser is not trusted with the OpenAI key. The key stays in `.env` on the server.

The model is not given raw database access. It can only call the explicit `get_order_details` function.

Policy text is included in the server-side agent prompt. The order JSON is the source of truth for sample-order facts.

## Latency trade-off

This prototype uses a simple request/response turn. It is intentionally easy to understand and deploy. For a production version, the first upgrade would be streaming/realtime audio so the customer does not wait for an entire recognition → reasoning → speech cycle.
