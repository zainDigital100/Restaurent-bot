"""
Core chat logic. Deliberately has zero FastAPI imports — this file should
be fully testable by running it directly (see __main__ block) before it
ever touches a web framework. If something breaks after you wrap this in
FastAPI, run this file standalone first to check whether the bug is in
your bot logic or in the API layer.

Session model: an in-memory dict of {session_id: Chat}. This means:
  - Conversation history lives only in RAM.
  - Restarting the server wipes every active conversation.
  - This will NOT work if you run multiple server processes/workers,
    since each process has its own dict — a customer's session could
    land on a process that's never seen their history.
For a real deployment: move session storage to Redis (your own roadmap
already lists Redis for "memory/state" — this is exactly where it plugs
in). Don't add that now; know it's the next step when this matters.
"""

from google import genai
from google.genai import types
from bot.tools import get_menu, search_faq_tool, place_order, get_order_status

GEN_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are a friendly assistant for a restaurant.

You can help customers:
- Browse the menu (use get_menu)
- Ask general questions about hours, delivery, payment, etc. (use search_faq_tool)
- Place an order (use place_order) — but ALWAYS read back the exact items
  and total price and get explicit confirmation from the customer before
  calling place_order.
- Check the status of an existing order (use get_order_status)

Keep responses short and conversational, like a real waiter texting.
Never invent menu items, prices, or FAQ answers that the tools didn't return.
"""

_client = genai.Client()
_sessions: dict[str, "genai.chats.Chat"] = {}


def _new_chat():
    return _client.chats.create(
        model=GEN_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[get_menu, search_faq_tool, place_order, get_order_status],
        ),
    )


def send_message(session_id: str, message: str) -> str:
    if session_id not in _sessions:
        _sessions[session_id] = _new_chat()
    chat = _sessions[session_id]
    response = chat.send_message(message)
    return response.text


def reset_session(session_id: str):
    _sessions.pop(session_id, None)


if __name__ == "__main__":
    # Standalone CLI test — run this before touching FastAPI.
    print("Restaurant bot (CLI test mode). Type 'quit' to exit.\n")
    session_id = "cli-test"
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        reply = send_message(session_id, user_input)
        print(f"Bot: {reply}\n")
