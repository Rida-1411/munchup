import os
import tempfile
from contextlib import closing

os.environ["MUNCHUP_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

import app as m


def setup_function():
    m.ORDERS.clear()
    m.EVENTS.clear()


def make_order(i=1):
    o = {c: "" for c in m.ORDER_COLUMNS}
    o.update({
        "Order ID": i, "Status": "Placed",
        "Subtotal": 0, "Delivery Fee": 0, "Total": 0,
    })
    m.ORDERS.append(o)
    return o


def test_get_order_found():
    o = make_order(5)
    assert m.get_order("5") is o


def test_get_order_invalid():
    assert m.get_order("abc") is None
    assert m.get_order(None) is None
    assert m.get_order(99) is None


def test_update_status_logs_event():
    o = make_order(1)
    m.update_status(o, "Accepted")
    assert o["Status"] == "Accepted"
    assert "Order #1 status changed to Accepted" in m.EVENTS[0]


def test_order_saved_to_database():
    o = make_order(7)
    m.save_order(o)
    with closing(m.get_db()) as db:
        row = db.execute(
            "SELECT status FROM orders WHERE order_id = 7"
        ).fetchone()
    assert row[0] == "Placed"


def test_menu_prices_positive():
    assert all(i["price"] > 0 for i in m.MENU)


def test_homepage_loads():
    assert m.server.test_client().get("/").status_code == 200


def test_version_endpoint():
    assert m.server.test_client().get("/version").data.decode() == m.APP_VERSION