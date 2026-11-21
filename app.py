import os
import sqlite3
from contextlib import closing
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, State, ctx, dash_table

app = Dash(__name__)
app.title = "MunchUp Food Delivery"
APP_VERSION = "1.0"
server = app.server

@server.route("/version")
def version():
    return APP_VERSION

#  DATA 

MENU = [
    {"name": "Chicken Burger", "price": 899},
    {"name": "Veggie Pizza", "price": 799},
    {"name": "French Fries", "price": 399},
    {"name": "Chocolate Shake", "price": 499},
]

ORDERS = []
EVENTS = []
NEXT_ORDER_ID = 1

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

ORANGE = "#f97316"
DARK = "#202124"
GREEN = "#16a34a"
RED = "#dc2626"


#  DATABASE 

DB_PATH = os.environ.get("MUNCHUP_DB", "munchup.db")

ORDER_COLUMNS = [
    "Order ID", "Customer", "Phone", "Address", "Items", "Subtotal",
    "Delivery Fee", "Total", "Status", "Rider", "Created At", "Updated At",
]


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(get_db()) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                customer TEXT, phone TEXT, address TEXT, items TEXT,
                subtotal INTEGER, delivery_fee INTEGER, total INTEGER,
                status TEXT, rider TEXT, created_at TEXT, updated_at TEXT
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT
            )"""
        )
        db.commit()


def save_order(order):
    with closing(get_db()) as db:
        db.execute(
            "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [order[c] for c in ORDER_COLUMNS],
        )
        db.commit()


def save_event(message):
    with closing(get_db()) as db:
        db.execute("INSERT INTO events (message) VALUES (?)", (message,))
        db.commit()


def load_data():
    global NEXT_ORDER_ID
    with closing(get_db()) as db:
        rows = db.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
        events = db.execute("SELECT message FROM events ORDER BY id DESC").fetchall()
    ORDERS.extend(dict(zip(ORDER_COLUMNS, row)) for row in rows)
    EVENTS.extend(e[0] for e in events)
    if ORDERS:
        NEXT_ORDER_ID = max(o["Order ID"] for o in ORDERS) + 1


init_db()
load_data()


#  HELPERS 

def log_event(message):
    time = datetime.now().strftime("%H:%M:%S")
    entry = f"{time} - {message}"
    EVENTS.insert(0, entry)
    save_event(entry)


def get_order(order_id):
    try:
        order_id = int(float(order_id))
    except (TypeError, ValueError):
        return None

    for order in ORDERS:
        if order["Order ID"] == order_id:
            return order

    return None


def update_status(order, status):
    order["Status"] = status
    order["Updated At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_order(order)
    log_event(f"Order #{order['Order ID']} status changed to {status}")


def get_order_rows():
    return [
        {
            "Order ID": o["Order ID"],
            "Customer": o["Customer"],
            "Phone": o["Phone"],
            "Address": o["Address"],
            "Items": o["Items"],
            "Total (PKR)": o["Total"],
            "Status": o["Status"],
            "Rider": o["Rider"] or "Not assigned",
            "Created At": o["Created At"],
        }
        for o in ORDERS
    ]


def make_table(table_id, columns):
    return dash_table.DataTable(
        id=table_id,
        columns=[{"name": c, "id": c} for c in columns],
        data=[],
        page_size=8,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={
            "padding": "10px",
            "textAlign": "left",
            "fontFamily": "Arial",
            "fontSize": "13px",
            "whiteSpace": "normal",
            "minWidth": "100px",
        },
        style_header={
            "backgroundColor": ORANGE,
            "color": "white",
            "fontWeight": "bold",
        },
    )


def label(text):
    return html.Label(
        text,
        style={
            "display": "block",
            "fontWeight": "bold",
            "marginTop": "12px",
            "marginBottom": "5px",
        },
    )


def text_input(component_id, placeholder, input_type="text"):
    return dcc.Input(
        id=component_id,
        type=input_type,
        placeholder=placeholder,
        style={
            "width": "100%",
            "padding": "10px",
            "boxSizing": "border-box",
            "border": "1px solid #ddd",
            "borderRadius": "6px",
        },
    )


def button(text, component_id, color=ORANGE):
    return html.Button(
        text,
        id=component_id,
        n_clicks=0,
        style={
            "backgroundColor": color,
            "color": "white",
            "border": "none",
            "padding": "11px 16px",
            "borderRadius": "7px",
            "cursor": "pointer",
            "marginTop": "12px",
            "marginRight": "8px",
        },
    )


def panel(children, max_width=None):
    style = {
        "backgroundColor": "white",
        "padding": "20px",
        "borderRadius": "12px",
        "marginBottom": "20px",
        "boxShadow": "0 2px 8px #00000010",
    }

    if max_width:
        style["maxWidth"] = max_width

    return html.Div(children, style=style)


def stat_card(title, value):
    return html.Div(
        [
            html.Div(title, style={"color": "#666"}),
            html.H2(value, style={"color": ORANGE}),
        ],
        style={
            "backgroundColor": "white",
            "padding": "18px",
            "borderRadius": "10px",
            "flex": "1",
            "minWidth": "130px",
        },
    )


# CUSTOMER PAGE

food_cards = []

for i, item in enumerate(MENU):
    food_cards.append(
        panel([
            html.H3(item["name"]),
            html.H3(
                f"PKR {item['price']:,}",
                style={"color": ORANGE},
            ),
            label("Quantity"),
            dcc.Input(
                id=f"qty-{i}",
                type="number",
                min=0,
                step=1,
                value=0,
                style={"width": "100%", "padding": "9px"},
            ),
        ])
    )


customer_page = html.Div([
    html.H2("Order Your Favourite Food"),
    html.P("Choose your food and get it delivered to your door."),

    html.Div(
        food_cards,
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
            "gap": "15px",
        },
    ),

    panel([
        html.H3("Delivery Details"),

        label("Full Name"),
        text_input("customer-name", "Enter your name"),

        label("Phone Number"),
        text_input("customer-phone", "Enter your phone number"),

        label("Delivery Address"),
        dcc.Textarea(
            id="customer-address",
            placeholder="House number, street, area, city",
            style={
                "width": "100%",
                "height": "85px",
                "padding": "10px",
                "boxSizing": "border-box",
            },
        ),

        html.P(
            "Delivery fee: PKR 150",
            style={"color": ORANGE, "fontWeight": "bold"},
        ),

        button("Place Order", "place-order"),
        html.Div(id="order-message", style={"marginTop": "15px"}),
    ], "650px"),

    html.Hr(),

    html.H2("Track Your Order"),
    html.P("Enter your order ID and phone number."),

    panel([
        label("Order ID"),
        text_input("track-order-id", "e.g. 1", "number"),

        label("Phone Number"),
        text_input("track-phone", "Your ordering phone number"),

        button("Track Order", "track-order", DARK),

        html.Div(id="tracking-result", style={"marginTop": "15px"}),
    ], "650px"),
])


#  RESTAURANT PAGE

restaurant_page = html.Div([
    html.H2("Restaurant Dashboard"),
    html.P("Accept orders and prepare food for delivery."),

    panel([
        label("Order ID"),
        text_input("restaurant-order-id", "Enter order ID", "number"),

        label("Choose Action"),
        dcc.Dropdown(
            id="restaurant-action",
            options=[
                {"label": "Accept Order", "value": "accept"},
                {"label": "Reject Order", "value": "reject"},
                {"label": "Start Preparing", "value": "preparing"},
                {"label": "Ready for Pickup", "value": "ready"},
            ],
            placeholder="Select an action",
            clearable=True,
        ),

        button("Update Order", "restaurant-update"),
        html.Div(id="restaurant-message", style={"marginTop": "12px"}),
    ], "550px"),

    html.H3("All Orders"),
    make_table(
        "restaurant-table",
        [
            "Order ID", "Customer", "Phone", "Address", "Items",
            "Total (PKR)", "Status", "Rider", "Created At",
        ],
    ),
])


#  DELIVERY RIDER PAGE 

delivery_page = html.Div([
    html.H2("Delivery Rider Dashboard"),
    html.P(
        "Pick up prepared orders, deliver them, and update their status."
    ),

    panel([
        html.H3("Orders Ready for Pickup"),
        make_table(
            "pickup-table",
            [
                "Order ID", "Customer", "Address",
                "Items", "Total (PKR)", "Status",
            ],
        ),
    ]),

    panel([
        html.H3("Update Delivery"),

        label("Rider Name"),
        text_input("rider-name", "Enter rider name"),

        label("Order ID"),
        text_input("delivery-order-id", "Enter order ID", "number"),

        html.Div([
            button("Pick Up Order", "pickup-order"),
            button("Out for Delivery", "out-for-delivery", "#2563eb"),
            button("Mark Delivered", "mark-delivered", GREEN),
        ], style={"display": "flex", "flexWrap": "wrap"}),

        html.Div(id="delivery-message", style={"marginTop": "12px"}),
    ], "700px"),

    html.H3("Delivery Progress"),
    make_table(
        "active-deliveries-table",
        ["Order ID", "Customer", "Address", "Status", "Rider"],
    ),
])


# ADMIN PAGE 

admin_page = html.Div([
    panel([
        html.H2("Admin Login"),
        html.P("Sign in to view MunchUp orders and performance."),

        label("Username"),
        text_input("admin-username", "Enter username"),

        label("Password"),
        text_input("admin-password", "Enter password", "password"),

        button("Login", "admin-login"),
        html.Div(id="admin-login-message", style={"marginTop": "12px"}),
    ], "450px"),

    html.Div(
        id="admin-dashboard",
        style={"display": "none"},
        children=[
            html.Div([
                html.H2("Admin Dashboard"),
                button("Logout", "admin-logout", DARK),
            ]),

            html.Div(
                id="admin-stats",
                style={
                    "display": "flex",
                    "gap": "15px",
                    "flexWrap": "wrap",
                    "margin": "20px 0",
                },
            ),

            html.H3("All Orders"),
            make_table(
                "admin-orders-table",
                [
                    "Order ID", "Customer", "Phone", "Address", "Items",
                    "Total (PKR)", "Status", "Rider", "Created At",
                ],
            ),

            html.H3("Menu and Prices"),
            dash_table.DataTable(
                id="admin-menu-table",
                columns=[
                    {"name": "Food Item", "id": "Food Item"},
                    {"name": "Price (PKR)", "id": "Price (PKR)"},
                ],
                data=[
                    {
                        "Food Item": item["name"],
                        "Price (PKR)": item["price"],
                    }
                    for item in MENU
                ],
                style_header={
                    "backgroundColor": ORANGE,
                    "color": "white",
                    "fontWeight": "bold",
                },
                style_cell={"padding": "10px", "textAlign": "left"},
            ),

            html.H3("Activity Log"),
            html.Div(
                id="admin-events",
                style={
                    "backgroundColor": "white",
                    "padding": "15px",
                    "borderRadius": "10px",
                    "whiteSpace": "pre-wrap",
                },
            ),
        ],
    ),
])


#  MAIN APP LAYOUT 

app.layout = html.Div([
    dcc.Interval(id="refresh-timer", interval=2000, n_intervals=0),

    html.Div([
        html.H1("MunchUp", style={"margin": "0", "fontSize": "36px"}),
        html.P(
            f"Good Food. Delivered to Your Door. (v{APP_VERSION})",
            style={"marginBottom": "0"},
        ),
    ], style={
        "backgroundColor": ORANGE,
        "color": "white",
        "textAlign": "center",
        "padding": "25px",
    }),

    dcc.Tabs(
        id="main-tabs",
        value="customer-tab",
        children=[
            dcc.Tab(
                label="Customer",
                value="customer-tab",
                children=html.Div(
                    customer_page,
                    style={"padding": "22px"},
                ),
            ),
            dcc.Tab(
                label="Restaurant",
                value="restaurant-tab",
                children=html.Div(
                    restaurant_page,
                    style={"padding": "22px"},
                ),
            ),
            dcc.Tab(
                label="Delivery Rider",
                value="delivery-tab",
                children=html.Div(
                    delivery_page,
                    style={"padding": "22px"},
                ),
            ),
            dcc.Tab(
                label="Admin",
                value="admin-tab",
                children=html.Div(
                    admin_page,
                    style={"padding": "22px"},
                ),
            ),
        ],
    ),
], style={
    "fontFamily": "Arial, sans-serif",
    "backgroundColor": "#f5f5f5",
    "minHeight": "100vh",
    "color": DARK,
})


#  PLACE ORDER 
@app.callback(
    Output("order-message", "children"),
    Input("place-order", "n_clicks"),
    State("customer-name", "value"),
    State("customer-phone", "value"),
    State("customer-address", "value"),
    *[State(f"qty-{i}", "value") for i in range(len(MENU))],
    prevent_initial_call=True,
)
def place_order(n_clicks, name, phone, address, *quantities):
    global NEXT_ORDER_ID

    if not name or not phone or not address:
        return html.P(
            "Please fill in your name, phone number, and address.",
            style={"color": RED},
        )

    name = name.strip()
    phone = phone.strip()
    address = address.strip()

    if not name or not phone or not address:
        return html.P("Please complete all delivery details.", style={"color": RED})

    selected_items = []
    subtotal = 0

    for item, quantity in zip(MENU, quantities):
        if quantity is None:
            quantity = 0

        try:
            number = float(quantity)
        except (TypeError, ValueError):
            return html.P("Enter valid quantities.", style={"color": RED})

        if number < 0 or not number.is_integer():
            return html.P(
                "Quantities must be whole numbers and cannot be negative.",
                style={"color": RED},
            )

        quantity = int(number)

        if quantity > 0:
            selected_items.append(f"{item['name']} x {quantity}")
            subtotal += item["price"] * quantity

    if not selected_items:
        return html.P("Select at least one food item.", style={"color": RED})

    delivery_fee = 150
    total = subtotal + delivery_fee

    order = {
        "Order ID": NEXT_ORDER_ID,
        "Customer": name,
        "Phone": phone,
        "Address": address,
        "Items": ", ".join(selected_items),
        "Subtotal": subtotal,
        "Delivery Fee": delivery_fee,
        "Total": total,
        "Status": "Placed",
        "Rider": "",
        "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Updated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    ORDERS.append(order)
    save_order(order)
    log_event(f"Order #{NEXT_ORDER_ID} placed by {name}.")

    order_id = NEXT_ORDER_ID
    NEXT_ORDER_ID += 1

    return html.Div([
        html.H3(
            f"Order #{order_id} placed successfully!",
            style={"color": GREEN},
        ),
        html.P(f"Items: {order['Items']}"),
        html.P(f"Subtotal: PKR {subtotal:,}"),
        html.P(f"Delivery fee: PKR {delivery_fee:,}"),
        html.H3(f"Total: PKR {total:,}"),
        html.P("Save your order ID and phone number to track delivery."),
    ])


# RESTAURANT ACTIONS

@app.callback(
    Output("restaurant-message", "children"),
    Input("restaurant-update", "n_clicks"),
    State("restaurant-order-id", "value"),
    State("restaurant-action", "value"),
    prevent_initial_call=True,
)
def restaurant_update(n_clicks, order_id, action):
    if not order_id or not action:
        return html.P("Enter an order ID and choose an action.", style={"color": RED})

    order = get_order(order_id)

    if order is None:
        return html.P("Order not found.", style={"color": RED})

    transitions = {
        "accept": ("Placed", "Accepted"),
        "reject": ("Placed", "Rejected"),
        "preparing": ("Accepted", "Preparing"),
        "ready": ("Preparing", "Ready for Pickup"),
    }

    old_status, new_status = transitions[action]

    if order["Status"] != old_status:
        return html.P(
            f"Cannot perform this action. Current status: {order['Status']}.",
            style={"color": RED},
        )

    update_status(order, new_status)

    return html.P(
        f"Order #{order['Order ID']} updated to {new_status}.",
        style={"color": GREEN},
    )


# DELIVERY ACTIONS 
@app.callback(
    Output("delivery-message", "children"),
    Input("pickup-order", "n_clicks"),
    Input("out-for-delivery", "n_clicks"),
    Input("mark-delivered", "n_clicks"),
    State("delivery-order-id", "value"),
    State("rider-name", "value"),
    prevent_initial_call=True,
)
def delivery_update(pickup_clicks, delivery_clicks, delivered_clicks,
                    order_id, rider_name):
    if not order_id:
        return html.P("Enter an order ID.", style={"color": RED})

    order = get_order(order_id)

    if order is None:
        return html.P("Order not found.", style={"color": RED})

    action = ctx.triggered_id

    if action == "pickup-order":
        if not rider_name or not rider_name.strip():
            return html.P("Enter the rider's name.", style={"color": RED})

        if order["Status"] != "Ready for Pickup":
            return html.P(
                "The restaurant must mark this order Ready for Pickup first.",
                style={"color": RED},
            )

        order["Rider"] = rider_name.strip()
        update_status(order, "Picked Up")

    elif action == "out-for-delivery":
        if order["Status"] != "Picked Up":
            return html.P(
                "Pick up the order before starting delivery.",
                style={"color": RED},
            )

        if rider_name and rider_name.strip() != order["Rider"]:
            return html.P(
                f"This order is assigned to {order['Rider']}.",
                style={"color": RED},
            )

        update_status(order, "Out for Delivery")

    elif action == "mark-delivered":
        if order["Status"] != "Out for Delivery":
            return html.P(
                "The order must be Out for Delivery first.",
                style={"color": RED},
            )

        if rider_name and rider_name.strip() != order["Rider"]:
            return html.P(
                f"This order is assigned to {order['Rider']}.",
                style={"color": RED},
            )

        update_status(order, "Delivered")

    return html.P(
        f"Order #{order['Order ID']} status: {order['Status']}",
        style={"color": GREEN},
    )


# CUSTOMER TRACKING 

@app.callback(
    Output("tracking-result", "children"),
    Input("track-order", "n_clicks"),
    State("track-order-id", "value"),
    State("track-phone", "value"),
    prevent_initial_call=True,
)
def track_order(n_clicks, order_id, phone):
    if not order_id or not phone:
        return html.P("Enter your order ID and phone number.", style={"color": RED})

    order = get_order(order_id)

    if order is None or order["Phone"] != phone.strip():
        return html.P(
            "No matching order found. Check your order ID and phone number.",
            style={"color": RED},
        )

    steps = [
        "Placed",
        "Accepted",
        "Preparing",
        "Ready for Pickup",
        "Picked Up",
        "Out for Delivery",
        "Delivered",
    ]

    if order["Status"] == "Rejected":
        progress = html.P(
            "The restaurant rejected this order.",
            style={"color": RED},
        )
    else:
        current_index = steps.index(order["Status"])

        progress = html.Div([
            html.P(
                ("✓ " if i <= current_index else "○ ") + step,
                style={
                    "color": GREEN if i <= current_index else "#888",
                    "fontWeight": "bold" if i == current_index else "normal",
                },
            )
            for i, step in enumerate(steps)
        ])

    return html.Div([
        html.H3(f"Order #{order['Order ID']}"),
        html.P(f"Items: {order['Items']}"),
        html.P(f"Total: PKR {order['Total']:,}"),
        html.P(f"Delivery address: {order['Address']}"),
        html.H3(f"Current status: {order['Status']}"),
        html.P(f"Rider: {order['Rider'] or 'Not assigned yet'}"),
        html.H4("Delivery Progress"),
        progress,
    ])


# REFRESH TABLES

@app.callback(
    Output("restaurant-table", "data"),
    Output("pickup-table", "data"),
    Output("active-deliveries-table", "data"),
    Input("refresh-timer", "n_intervals"),
)
def refresh_tables(n_intervals):
    restaurant_rows = get_order_rows()

    pickup_rows = [
        {
            "Order ID": o["Order ID"],
            "Customer": o["Customer"],
            "Address": o["Address"],
            "Items": o["Items"],
            "Total (PKR)": o["Total"],
            "Status": o["Status"],
        }
        for o in ORDERS
        if o["Status"] == "Ready for Pickup"
    ]

    delivery_rows = [
        {
            "Order ID": o["Order ID"],
            "Customer": o["Customer"],
            "Address": o["Address"],
            "Status": o["Status"],
            "Rider": o["Rider"] or "Not assigned",
        }
        for o in ORDERS
        if o["Status"] in [
            "Picked Up", "Out for Delivery", "Delivered"
        ]
    ]

    return restaurant_rows, pickup_rows, delivery_rows


#  ADMIN LOGIN 

@app.callback(
    Output("admin-login-message", "children"),
    Output("admin-dashboard", "style"),
    Input("admin-login", "n_clicks"),
    Input("admin-logout", "n_clicks"),
    State("admin-username", "value"),
    State("admin-password", "value"),
    prevent_initial_call=True,
)
def admin_login(login_clicks, logout_clicks, username, password):
    if ctx.triggered_id == "admin-logout":
        return "Logged out.", {"display": "none"}

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return "Login successful.", {"display": "block"}

    return (
        html.Span("Incorrect username or password.", style={"color": RED}),
        {"display": "none"},
    )


# ADMIN DASHBOARD REFRESH

@app.callback(
    Output("admin-orders-table", "data"),
    Output("admin-stats", "children"),
    Output("admin-events", "children"),
    Input("refresh-timer", "n_intervals"),
)
def refresh_admin(n_intervals):
    total_orders = len(ORDERS)

    revenue = sum(
        o["Total"] for o in ORDERS if o["Status"] != "Rejected"
    )

    pending = sum(1 for o in ORDERS if o["Status"] == "Placed")

    in_progress = sum(
        1 for o in ORDERS
        if o["Status"] in [
            "Accepted", "Preparing", "Ready for Pickup",
            "Picked Up", "Out for Delivery",
        ]
    )

    delivered = sum(1 for o in ORDERS if o["Status"] == "Delivered")

    stats = [
        stat_card("Total Orders", str(total_orders)),
        stat_card("Order Value (PKR)", f"{revenue:,}"),
        stat_card("Pending", str(pending)),
        stat_card("In Progress", str(in_progress)),
        stat_card("Delivered", str(delivered)),
    ]

    event_text = "\n".join(EVENTS[:30]) if EVENTS else "No activity yet."

    return get_order_rows(), stats, event_text


#  RUN APP 

if __name__ == "__main__":
    print("Starting MunchUp...")
    print("Open http://127.0.0.1:8050")
    app.run(debug=False, port=8050)