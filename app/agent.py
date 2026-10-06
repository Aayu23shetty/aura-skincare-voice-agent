import json
import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "data" / "orders.json"

with ORDERS_PATH.open("r", encoding="utf-8") as f:
    ORDERS = json.load(f)

BRAND_POLICY = """
Aura Skincare is a premium organic Indian skincare brand focused on simple,
effective skincare products made with thoughtfully selected ingredients.

Shipping:
- Free delivery on orders above ₹499.
- Orders below ₹499 have a ₹50 shipping fee.
- Standard delivery takes 3–5 business days.

Returns/refunds:
- Returns are accepted within 7 days of delivery.
- Product must be unopened, unused, and in original packaging.
- Damaged or defective products must be reported within 48 hours of delivery
  with photos for replacement.

Cancellation:
- Orders can be cancelled only while status is Processing.
- Shipped or Out for Delivery orders cannot be cancelled.
- Customers may refuse delivery at the doorstep.

Cash on delivery:
- COD is available for orders up to ₹2,500.
- Customers can pay by cash or UPI at the doorstep.

Scope:
- Only Aura Skincare customer-support topics are in scope.
- Never invent order information, refund approvals, delivery promises, discounts,
  policy exceptions, tracking events, or product claims.
- If information is missing, say what is missing and ask a focused question.
"""

SYSTEM_PROMPT = f"""
You are Aria, the voice customer-support specialist for Aura Skincare.
You are friendly, professional, concise, and naturally Indian in tone.
Keep spoken responses short: usually 1–3 sentences. Avoid headings, bullets,
markdown, emojis, and long explanations in spoken replies.

Follow the brand policy exactly:
{BRAND_POLICY}

Tool rule:
- Use get_order_details whenever an order-specific fact is needed.
- Do not guess an order's status, delivery date, tracking number, eligibility,
  customer name, or product.
- If an order ID is absent, ask for it.
- If the ID is invalid, say you could not locate it and ask the customer to
  verify/repeat it.
- If a request is outside Aura Skincare, politely state that you can only help
  with Aura Skincare queries.
- For a policy decision, explain the rule rather than promising an exception.
"""

TOOL_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "get_order_details",
        "description": "Retrieve a mock Aura Skincare order by its exact order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Aura order ID such as ORD-101"
                }
            },
            "required": ["order_id"],
            "additionalProperties": False
        }
    }
}]

def get_order_details(order_id: str) -> dict[str, Any]:
    order_id = (order_id or "").strip().upper()
    order = ORDERS.get(order_id)
    if not order:
        return {
            "found": False,
            "order_id": order_id,
            "message": "No Aura Skincare order was found with that ID."
        }
    return {"found": True, "order": order}

def gemini_get_order_details(order_id: str) -> dict[str, Any]:
    """
    Retrieve an Aura Skincare order.

    Normalizes spoken order IDs such as:
    ORD 101, Ord 101, ORD dash 101
    into the database format:
    ORD-101
    """
    order_ids = re_find_order_id(order_id)

    if not order_ids:
        return {
            "found": False,
            "order_id": order_id,
            "error": "Invalid order ID format."
        }

    normalized_id = order_ids[0]
    return get_order_details(normalized_id)

def demo_reply(user_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Small deterministic fallback so the UI remains testable without an API key."""
    text = user_text.lower()
    calls = []
    ids = re_find_order_id(user_text)

    if any(x in text for x in ["flight", "hotel", "goa", "book a cab", "movie ticket"]):
        return ("I can help only with Aura Skincare orders, policies, and product-support questions.", calls)

    if ids:
        oid = ids[0]
        result = get_order_details(oid)
        calls.append({"tool": "get_order_details", "arguments": {"order_id": oid}, "result": result})
        if not result["found"]:
            return (f"I couldn't locate {oid}. Could you please repeat or verify the order ID?", calls)
        o = result["order"]
        if "where" in text or "track" in text or "status" in text or "delivery" in text:
            if o["status"] == "Out for Delivery":
                return (f"{oid} is out for delivery with {o['carrier']}. The current note says it's expected by 6 PM today.", calls)
            if o["status"] == "Delivered":
                return (f"{oid} was delivered 14 days ago via {o['carrier']}.", calls)
            return (f"{oid} is currently processing. It was ordered 3 hours ago and is eligible for cancellation.", calls)
        if "cancel" in text:
            if o["status"] == "Processing":
                return (f"Yes. {oid} is still processing, so it is eligible for cancellation.", calls)
            return (f"I can't cancel {oid} because it is already {o['status'].lower()}.", calls)
        return (f"I found {oid}: {o['product']} for ₹{o['value']}, currently {o['status'].lower()}.", calls)

    if "return" in text or "refund" in text:
        if "20" in text or "14" in text or "opened" in text:
            return ("Returns are accepted within 7 days of delivery only for unopened and unused products in original packaging. So that request would fall outside the return policy.", calls)
        return ("Returns are accepted within 7 days of delivery for unopened, unused products in original packaging. Damaged or defective items should be reported within 48 hours with photos.", calls)

    if "shipping" in text or "delivery" in text:
        return ("Delivery is free above ₹499; orders below ₹499 have a ₹50 shipping fee. Standard delivery takes 3 to 5 business days.", calls)

    if "cod" in text or "cash" in text or "upi" in text:
        return ("COD is available for orders up to ₹2,500, and payment can be made by cash or UPI at the doorstep.", calls)

    if "cancel" in text:
        return ("An order can be cancelled only while it is Processing. Once it is Shipped or Out for Delivery, it cannot be cancelled.", calls)

    return ("I can help with Aura Skincare products, shipping, returns, cancellations, COD, or an order lookup. What would you like to check?", calls)

def re_find_order_id(text: str) -> list[str]:
    import re

    text = text.upper()

    # Handle common speech-recognition variations:
    # "ORD-101", "ORD 101", "ORD dash 101", "ORDER 101"
    text = re.sub(
        r"\bORD\s*(?:DASH|HYPHEN)?\s*-?\s*(\d{3})\b",
        r"ORD-\1",
        text
    )

    text = re.sub(
        r"\bORDER\s*(?:DASH|HYPHEN)?\s*-?\s*(\d{3})\b",
        r"ORD-\1",
        text
    )

    return re.findall(r"\bORD-\d{3}\b", text)

def ai_reply(history: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    """
    Generate an Aria response.

    Demo mode remains available for local testing.
    When GEMINI_API_KEY is configured and DEMO_MODE=0,
    Gemini handles the conversation and can call the order tool.
    """

    latest = history[-1]["content"] if history else ""

    # ---------------------------------------------------------
    # DEMO MODE
    # ---------------------------------------------------------
    if os.getenv("DEMO_MODE", "0") == "1":
        return demo_reply(latest)

    # ---------------------------------------------------------
    # GEMINI MODE
    # ---------------------------------------------------------
    if os.getenv("GEMINI_API_KEY"):
        if genai is None:
            raise RuntimeError(
                "Gemini SDK is not installed. Run: pip install google-genai"
            )

        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        )

        # Convert our application's history format into
        # Gemini's expected conversation roles.
        contents = []

        for item in history[-14:]:
            role = item.get("role", "user")
            content = item.get("content", "")

            if not content:
                continue

            # Gemini uses "model" rather than "assistant".
            if role == "assistant":
                role = "model"

            contents.append({
                "role": role,
                "parts": [
                    {"text": content}
                ]
            })

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            tools=[gemini_get_order_details],
        )

        import time

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                  model=model,
                  contents=contents,
                  config=config,
                )
                break
            except Exception as exc:
                if attempt == 2:
                  raise
        time.sleep(2 ** attempt)

        answer = (response.text or "").strip()

        if not answer:
            answer = (
                "I'm sorry, I wasn't able to generate a response. "
                "Could you please repeat that?"
            )

        return answer, []

    # ---------------------------------------------------------
    # OPENAI FALLBACK
    # ---------------------------------------------------------
    if os.getenv("OPENAI_API_KEY"):
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK is not installed.")

        client = OpenAI()

        model = os.getenv("OPENAI_MODEL", "gpt-5")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + history[-14:]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMA,
            tool_choice="auto",
            temperature=0.2
        )

        tool_events = []
        message = response.choices[0].message

        if message.tool_calls:
            tool_messages = []

            for call in message.tool_calls:
                if call.function.name != "get_order_details":
                    continue

                args = json.loads(
                    call.function.arguments or "{}"
                )

                result = get_order_details(
                    args.get("order_id", "")
                )

                tool_events.append({
                    "tool": call.function.name,
                    "arguments": args,
                    "result": result
                })

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False
                    )
                })

            followup_messages = messages + [{
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments
                        }
                    }
                    for c in message.tool_calls
                ]
            }] + tool_messages

            final = client.chat.completions.create(
                model=model,
                messages=followup_messages,
                temperature=0.2
            )

            return (
                final.choices[0].message.content.strip(),
                tool_events
            )

        return (
            (message.content or "").strip(),
            tool_events
        )

    # ---------------------------------------------------------
    # NO AI PROVIDER AVAILABLE
    # ---------------------------------------------------------
    return demo_reply(latest)