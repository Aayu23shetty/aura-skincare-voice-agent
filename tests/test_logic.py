import os
os.environ["DEMO_MODE"] = "1"

from app.agent import get_order_details, demo_reply

def test_known_order():
    result = get_order_details("ord-101")
    assert result["found"] is True
    assert result["order"]["status"] == "Out for Delivery"

def test_unknown_order():
    result = get_order_details("ORD-999")
    assert result["found"] is False

def test_demo_policy_guardrail():
    reply, calls = demo_reply("I bought this 20 days ago and opened it. Can I return it?")
    assert "7 days" in reply
    assert calls == []

def test_demo_order_lookup():
    reply, calls = demo_reply("Where is order ORD-101?")
    assert "out for delivery" in reply.lower()
    assert calls[0]["tool"] == "get_order_details"
