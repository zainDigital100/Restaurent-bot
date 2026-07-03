"""
These four functions are handed directly to Gemini as tools. The SDK reads
each function's type hints and docstring to build the schema the model
uses to decide when and how to call them — so the docstrings below aren't
just documentation, they're literally what the model reads to make
decisions. Vague docstrings = bad tool-calling decisions. Keep them precise.
"""

import bot.data_store as data_store

def get_menu(category: str = "") -> str:
    """Get the restaurant's menu items. Optionally filter by category.

    Args:
        category: One of "Starters", "Main Course", "Bread", "Beverages",
            "Dessert". Leave empty to return the entire menu.
    """
    menu = data_store.load_menu()
    if category:
        menu = menu[menu["Category"].str.lower() == category.lower()]
    if menu.empty:
        return f"No items found in category '{category}'."

    lines = []
    for _, row in menu.iterrows():
        status = "" if row["Available"] == "Yes" else " (currently unavailable)"
        lines.append(f"{row['Name']} - Rs.{row['Price']} - {row['Description']}{status}")
    return "\n".join(lines)


def search_faq_tool(query: str) -> str:
    """Search restaurant FAQs (hours, delivery, payment, reservations, etc.)
    to answer a customer's general question that is NOT about placing an
    order or checking an existing order.

    Args:
        query: The customer's question, in their own words.
    """
    from Projects.chatbot.bot.faq_search import search_faq
    results = search_faq(query)
    if not results:
        return "No matching FAQ found. Tell the customer you don't have that information and suggest they call the restaurant directly."
    return "\n".join(f"Q: {r['question']}\nA: {r['answer']}" for r in results)


def place_order(customer_name: str, items: list[dict]) -> str:
    """Place a food order after the customer has confirmed exactly what
    they want. Do NOT call this until the customer has explicitly confirmed
    their order — always read back the items and total price first and
    wait for confirmation.

    Args:
        customer_name: The customer's name.
        items: List of items, each a dict with "name" (str) and "quantity"
            (int). Example: [{"name": "Chicken Karahi", "quantity": 1}]
    """
    resolved_items = []
    total = 0.0
    unavailable = []

    for item in items:
        match = data_store.find_menu_item(item["name"])
        if match is None:
            return f"Could not find '{item['name']}' on the menu. Ask the customer to clarify or check get_menu."
        if match["Available"] != "Yes":
            unavailable.append(match["Name"])
            continue
        qty = item.get("quantity", 1)
        line_total = match["Price"] * qty
        total += line_total
        resolved_items.append({"name": match["Name"], "quantity": qty, "price": match["Price"]})

    if unavailable:
        return f"These items are currently unavailable: {', '.join(unavailable)}. Ask the customer to choose something else."

    order_id = data_store.append_order(customer_name, resolved_items, total)
    return f"Order placed successfully. Order_ID: {order_id}, Total: Rs.{total}. Read this confirmation back to the customer."


def get_order_status(order_id: str) -> str:
    """Look up an existing order by its Order ID to check its status.

    Args:
        order_id: The order ID, e.g. "ORD3F9A2C".
    """
    order = data_store.get_order(order_id)
    if order is None:
        return f"No order found with ID '{order_id}'. Ask the customer to double check the ID."
    return (
        f"Order {order['Order_ID']}: {order['Items']} | "
        f"Total: Rs.{order['Total']} | Status: {order['Status']} | "
        f"Placed: {order['Timestamp']}"
    )
