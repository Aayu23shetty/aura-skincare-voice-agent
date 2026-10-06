import json
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, request

from .agent import ai_reply, get_order_details, ORDERS

main = Blueprint("main", __name__)

@main.get("/")
def index():
    return render_template("index.html", orders=ORDERS)

@main.get("/api/health")
def health():
    live_ai = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("DEMO_MODE", "0") != "1"
    return jsonify({
        "ok": True,
        "mode": "ai" if live_ai else "demo",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@main.post("/api/order")
def order_lookup():
    body = request.get_json(silent=True) or {}
    return jsonify(get_order_details(body.get("order_id", "")))

@main.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    history = body.get("history", [])
    if not isinstance(history, list):
        return jsonify({"error": "history must be a list"}), 400

    clean_history = []
    for item in history[-14:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            clean_history.append({"role": role, "content": content.strip()})

    if not clean_history or clean_history[-1]["role"] != "user":
        return jsonify({"error": "A latest user message is required."}), 400

    try:
        answer, tool_events = ai_reply(clean_history)
        return jsonify({
            "reply": answer,
            "tool_events": tool_events,
            "mode": (
                "gemini"
                if os.getenv("GEMINI_API_KEY") and os.getenv("DEMO_MODE", "0") != "1"
                else "demo"
            )
        })
    except Exception as exc:
        import traceback
        traceback.print_exc()

        return jsonify({
            "error": "The agent could not complete that turn.",
            "detail": str(exc)
        }), 500

@main.post("/api/summary")
def summary():
    body = request.get_json(silent=True) or {}
    transcript = body.get("transcript", [])

    if not isinstance(transcript, list):
        return jsonify({"error": "transcript must be a list"}), 400

    customer_lines = [
        x.get("text", "")
        for x in transcript
        if x.get("speaker") == "customer"
    ]

    joined = " ".join(customer_lines)
    joined_lower = joined.lower()

    # Recognise common speech-to-text variations:
    # ORD-101
    # Ord 101
    # Ord dash 101
    # Order 101
    import re

    normalized = joined.upper()

    normalized = re.sub(
        r"\bORD\s*(?:DASH|HYPHEN)?\s*-?\s*(\d{3})\b",
        r"ORD-\1",
        normalized
    )

    normalized = re.sub(
        r"\bORDER\s*(?:DASH|HYPHEN)?\s*-?\s*(\d{3})\b",
        r"ORD-\1",
        normalized
    )

    order_match = re.search(r"\bORD-\d{3}\b", normalized)
    order_id = order_match.group(0) if order_match else None

    # Determine intent.
    # Put specific intents before generic "order" detection.
    if "cancel" in joined_lower:
        intent = "CANCELLATION"
    elif "return" in joined_lower or "refund" in joined_lower:
        intent = "RETURN_REFUND"
    elif "shipping" in joined_lower or "delivery charge" in joined_lower:
        intent = "SHIPPING"
    elif "cod" in joined_lower or "cash on delivery" in joined_lower:
        intent = "CASH_ON_DELIVERY"
    elif any(
        k in joined_lower
        for k in ["where", "track", "delivery", "status", "order"]
    ):
        intent = "ORDER_TRACKING"
    else:
        intent = "GENERAL_SUPPORT"

    # Default resolution status.
    resolution = "UNRESOLVED"

    if any(x.get("speaker") == "agent" for x in transcript):
        resolution = "RESOLVED"

    # Build a more useful summary.
    summary_text = "Customer contacted Aura Skincare support."

    if order_id and order_id in ORDERS:
        order = ORDERS[order_id]

        if intent == "CANCELLATION":
            if order["status"] == "Processing":
                summary_text = (
                    f"Customer asked to cancel {order_id}. "
                    f"The order is currently processing and is eligible for cancellation."
                )
            else:
                summary_text = (
                    f"Customer asked to cancel {order_id}. "
                    f"The order is already {order['status'].lower()} and cannot be cancelled."
                )

        elif intent == "ORDER_TRACKING":
            summary_text = (
                f"Customer asked about {order_id}. "
                f"The order is currently {order['status'].lower()}."
            )

            if order["notes"]:
                summary_text += f" {order['notes']}"

        elif intent == "RETURN_REFUND":
            summary_text = (
                f"Customer asked about a return or refund involving {order_id}. "
                f"Return eligibility was explained according to Aura Skincare policy."
            )

        else:
            summary_text = (
                f"Customer contacted support regarding {order_id}. "
                f"The order is currently {order['status'].lower()}."
            )

    elif intent == "RETURN_REFUND":
        summary_text = (
            "Customer asked about a return or refund. "
            "Aura Skincare's return policy was explained."
        )

    elif intent == "CANCELLATION":
        summary_text = (
            "Customer asked about cancelling an order. "
            "Aura Skincare's cancellation policy was explained."
        )

    return jsonify({
        "customer_intent": intent,
        "order_id": order_id,
        "resolution_status": resolution,
        "call_summary": summary_text
    })