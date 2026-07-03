"""
Reads/writes the three Excel sheets. Nothing in here knows about Gemini,
FastAPI, or chat — it's pure data access. Keep it that way: when you swap
sample data for real restaurant data, or swap Excel for a real database
later, only this file changes.
"""

import os
import uuid
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MENU_PATH = os.path.join(BASE_DIR, "data", "menu.xlsx")
FAQS_PATH = os.path.join(BASE_DIR, "data", "faqs.xlsx")
ORDERS_PATH = os.path.join(BASE_DIR, "data", "orders.xlsx")


def load_menu() -> pd.DataFrame:
    return pd.read_excel(MENU_PATH)


def load_faqs() -> pd.DataFrame:
    return pd.read_excel(FAQS_PATH)


def load_orders() -> pd.DataFrame:
    return pd.read_excel(ORDERS_PATH)


def find_menu_item(name: str) -> dict | None:
    """Case-insensitive partial match on item name. Returns the first match."""
    menu = load_menu()
    matches = menu[menu["Name"].str.lower().str.contains(name.lower(), na=False)]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def append_order(customer_name: str, items: list[dict], total: float) -> str:
    """
    items: list of {"name": str, "quantity": int, "price": float}
    Returns the generated Order_ID.

    NOTE: this reads the whole file, appends a row, writes the whole file
    back. Fine for a single-restaurant demo with low order volume. It is
    NOT safe for concurrent writes — two orders placed at the same instant
    can race and overwrite each other. A real deployment needs a database
    (SQLite minimum, Postgres realistically) with proper transactions.
    This is a known, deliberate limitation — not an oversight.
    """
    orders = load_orders()
    order_id = f"ORD{uuid.uuid4().hex[:6].upper()}"
    items_str = "; ".join(f"{i['quantity']}x {i['name']} (Rs.{i['price']})" for i in items)

    new_row = {
        "Order_ID": order_id,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Customer_Name": customer_name,
        "Items": items_str,
        "Total": total,
        "Status": "Received",
    }
    orders = pd.concat([orders, pd.DataFrame([new_row])], ignore_index=True)
    orders.to_excel(ORDERS_PATH, index=False)
    return order_id


def get_order(order_id: str) -> dict | None:
    orders = load_orders()
    match = orders[orders["Order_ID"] == order_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()
