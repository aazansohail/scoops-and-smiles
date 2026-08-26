"""
Scoops and Smiles — Business logic module
"""

from datetime import date, datetime
from database import get_connection

# Size map: name -> {scoops, ounces, price}
SIZE_MAP = {
    'Kiddie': {'scoops': 1, 'ounces': 4,  'price': 3.00},
    'Small':  {'scoops': 2, 'ounces': 8,  'price': 3.50},
    'Medium': {'scoops': 3, 'ounces': 12, 'price': 4.00},
    'Large':  {'scoops': 4, 'ounces': 16, 'price': 4.50},
}


# ── Purchase functions ────────────────────────────────────────────────────────

def purchase_flavor(location_id, flavor_id, num_containers, purchase_date):
    """
    Add num_containers * 640 oz to flavor_inventory and log in purchases.

    purchase_date: YYYY-MM-DD string or datetime.date object
    """
    if isinstance(purchase_date, date):
        purchase_date = purchase_date.strftime("%Y-%m-%d")

    oz_added = num_containers * 640
    now = datetime.now().isoformat()

    with get_connection() as conn:
        flavor = conn.execute(
            "SELECT cost_per_container FROM flavors WHERE flavor_id = ?",
            (flavor_id,)
        ).fetchone()
        if flavor is None:
            raise ValueError(f"No flavor found with flavor_id={flavor_id}")

        total_cost = num_containers * flavor["cost_per_container"]

        conn.execute(
            """UPDATE flavor_inventory
               SET quantity_oz = quantity_oz + ?, last_updated = ?
               WHERE location_id = ? AND flavor_id = ?""",
            (oz_added, now, location_id, flavor_id),
        )

        conn.execute(
            """INSERT INTO purchases
                   (location_id, purchase_date, item_type, item_id, quantity_purchased, total_cost)
               VALUES (?, ?, 'flavor', ?, ?, ?)""",
            (location_id, purchase_date, flavor_id, num_containers, total_cost),
        )


def purchase_containers(location_id, container_id, num_packs, purchase_date):
    """
    Add num_packs * 100 units to container_inventory and log in purchases.

    purchase_date: YYYY-MM-DD string or datetime.date object
    """
    if isinstance(purchase_date, date):
        purchase_date = purchase_date.strftime("%Y-%m-%d")

    units_added = num_packs * 100
    now = datetime.now().isoformat()

    with get_connection() as conn:
        container = conn.execute(
            "SELECT cost_per_100 FROM containers WHERE container_id = ?",
            (container_id,)
        ).fetchone()
        if container is None:
            raise ValueError(f"No container found with container_id={container_id}")

        total_cost = num_packs * container["cost_per_100"]

        conn.execute(
            """UPDATE container_inventory
               SET quantity_units = quantity_units + ?, last_updated = ?
               WHERE location_id = ? AND container_id = ?""",
            (units_added, now, location_id, container_id),
        )

        conn.execute(
            """INSERT INTO purchases
                   (location_id, purchase_date, item_type, item_id, quantity_purchased, total_cost)
               VALUES (?, ?, 'container', ?, ?, ?)""",
            (location_id, purchase_date, container_id, num_packs, total_cost),
        )


def purchase_napkins(location_id, num_packs, purchase_date):
    """
    Add num_packs * 10000 units to napkin_inventory and log in purchases.

    purchase_date: YYYY-MM-DD string or datetime.date object
    """
    if isinstance(purchase_date, date):
        purchase_date = purchase_date.strftime("%Y-%m-%d")

    units_added = num_packs * 10000
    now = datetime.now().isoformat()
    total_cost = num_packs * 20.00

    with get_connection() as conn:
        conn.execute(
            """UPDATE napkin_inventory
               SET quantity = quantity + ?, last_updated = ?
               WHERE location_id = ?""",
            (units_added, now, location_id),
        )

        conn.execute(
            """INSERT INTO purchases
                   (location_id, purchase_date, item_type, item_id, quantity_purchased, total_cost)
               VALUES (?, ?, 'napkins', NULL, ?, ?)""",
            (location_id, purchase_date, num_packs, total_cost),
        )


# ── Sales function ────────────────────────────────────────────────────────────

def record_sale(location_id, flavor_id, container_id, size, sale_date, quantity=1):
    """
    Record one or more ice cream sales of the same item.

    Validates stock for the full quantity, decrements inventory in bulk,
    and inserts one sale record per unit sold.
    Returns total sale price.

    sale_date: YYYY-MM-DD string or datetime.date object
    quantity:  number of units to sell (default 1)
    """
    if size not in SIZE_MAP:
        raise ValueError(f"Invalid size '{size}'. Valid sizes: {list(SIZE_MAP.keys())}")

    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    if isinstance(sale_date, date):
        sale_date = sale_date.strftime("%Y-%m-%d")

    info = SIZE_MAP[size]
    ounces = info['ounces']
    scoops = info['scoops']
    sale_price = info['price']
    now = datetime.now().isoformat()

    total_ounces = ounces * quantity
    total_napkins = 2 * quantity

    with get_connection() as conn:
        # Check flavor stock
        fi = conn.execute(
            "SELECT quantity_oz FROM flavor_inventory WHERE location_id = ? AND flavor_id = ?",
            (location_id, flavor_id)
        ).fetchone()
        if fi is None or fi["quantity_oz"] < total_ounces:
            have = fi["quantity_oz"] if fi else 0
            raise ValueError(
                f"Insufficient flavor stock: need {total_ounces} oz for {quantity} sale(s), have {have:.0f} oz"
            )

        # Check container stock
        ci = conn.execute(
            "SELECT quantity_units FROM container_inventory WHERE location_id = ? AND container_id = ?",
            (location_id, container_id)
        ).fetchone()
        if ci is None or ci["quantity_units"] < quantity:
            have = ci["quantity_units"] if ci else 0
            raise ValueError(
                f"Insufficient container stock: need {quantity} unit(s), have {have} units"
            )

        # Check napkin stock (2 napkins per sale)
        ni = conn.execute(
            "SELECT quantity FROM napkin_inventory WHERE location_id = ?",
            (location_id,)
        ).fetchone()
        if ni is None or ni["quantity"] < total_napkins:
            have = ni["quantity"] if ni else 0
            raise ValueError(
                f"Insufficient napkins: need {total_napkins} for {quantity} sale(s), have {have} units"
            )

        # Decrement inventories in bulk
        conn.execute(
            """UPDATE flavor_inventory
               SET quantity_oz = quantity_oz - ?, last_updated = ?
               WHERE location_id = ? AND flavor_id = ?""",
            (total_ounces, now, location_id, flavor_id),
        )
        conn.execute(
            """UPDATE container_inventory
               SET quantity_units = quantity_units - ?, last_updated = ?
               WHERE location_id = ? AND container_id = ?""",
            (quantity, now, location_id, container_id),
        )
        conn.execute(
            """UPDATE napkin_inventory
               SET quantity = quantity - ?, last_updated = ?
               WHERE location_id = ?""",
            (total_napkins, now, location_id),
        )

        # Insert one sale record per unit
        for _ in range(quantity):
            conn.execute(
                """INSERT INTO sales
                       (location_id, sale_date, flavor_id, container_id, size,
                        scoops, ounces, sale_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (location_id, sale_date, flavor_id, container_id, size,
                 scoops, ounces, sale_price),
            )

    return sale_price * quantity


# ── Inventory queries ─────────────────────────────────────────────────────────

def _flavor_status(qty_oz):
    if qty_oz <= 640:
        return "critical"
    elif qty_oz <= 1920:
        return "low"
    return "ok"


def _container_status(qty_units):
    if qty_units <= 50:
        return "critical"
    elif qty_units <= 150:
        return "low"
    return "ok"


def _napkin_status(qty):
    if qty <= 1000:
        return "critical"
    elif qty <= 3000:
        return "low"
    return "ok"


def get_current_inventory(location_id):
    """
    Return current inventory for a location.

    Returns dict:
    {
      'flavors': [{'flavor_id', 'flavor_name', 'quantity_oz', 'status'}],
      'containers': [{'container_id', 'container_name', 'quantity_units', 'status'}],
      'napkins': {'quantity', 'status'}
    }
    """
    with get_connection() as conn:
        flavor_rows = conn.execute(
            """SELECT f.flavor_id, f.flavor_name, COALESCE(fi.quantity_oz, 0) AS quantity_oz
               FROM flavors f
               LEFT JOIN flavor_inventory fi
                      ON fi.flavor_id = f.flavor_id AND fi.location_id = ?
               ORDER BY f.flavor_id""",
            (location_id,)
        ).fetchall()

        container_rows = conn.execute(
            """SELECT c.container_id, c.container_name,
                      COALESCE(ci.quantity_units, 0) AS quantity_units
               FROM containers c
               LEFT JOIN container_inventory ci
                      ON ci.container_id = c.container_id AND ci.location_id = ?
               ORDER BY c.container_id""",
            (location_id,)
        ).fetchall()

        napkin_row = conn.execute(
            "SELECT COALESCE(quantity, 0) AS quantity FROM napkin_inventory WHERE location_id = ?",
            (location_id,)
        ).fetchone()

    flavors = [
        {
            "flavor_id":   row["flavor_id"],
            "flavor_name": row["flavor_name"],
            "quantity_oz": row["quantity_oz"],
            "status":      _flavor_status(row["quantity_oz"]),
        }
        for row in flavor_rows
    ]

    containers = [
        {
            "container_id":   row["container_id"],
            "container_name": row["container_name"],
            "quantity_units": row["quantity_units"],
            "status":         _container_status(row["quantity_units"]),
        }
        for row in container_rows
    ]

    napkin_qty = napkin_row["quantity"] if napkin_row else 0
    napkins = {"quantity": napkin_qty, "status": _napkin_status(napkin_qty)}

    return {"flavors": flavors, "containers": containers, "napkins": napkins}


# ── Reporting queries ─────────────────────────────────────────────────────────

def get_monthly_income_statement(location_id, year, month):
    """
    Return income statement dict for a location (or company-wide if location_id=None).

    Returns dict with revenue, variable_* and fixed_* breakdowns, net_income.
    """
    month_str = f"{year}-{month:02d}"
    conn = get_connection()

    def _q(sql, params):
        if location_id is not None:
            sql += " AND location_id = ?"
            params = list(params) + [location_id]
        return conn.execute(sql, params).fetchone()[0]

    revenue = _q(
        "SELECT COALESCE(SUM(sale_price),0) FROM sales WHERE strftime('%Y-%m', sale_date)=?",
        (month_str,)
    )
    flavor_cost = _q(
        "SELECT COALESCE(SUM(total_cost),0) FROM purchases WHERE strftime('%Y-%m', purchase_date)=? AND item_type='flavor'",
        (month_str,)
    )
    container_cost = _q(
        "SELECT COALESCE(SUM(total_cost),0) FROM purchases WHERE strftime('%Y-%m', purchase_date)=? AND item_type='container'",
        (month_str,)
    )
    napkin_cost = _q(
        "SELECT COALESCE(SUM(total_cost),0) FROM purchases WHERE strftime('%Y-%m', purchase_date)=? AND item_type='napkins'",
        (month_str,)
    )

    # Fixed expenses: pull from fixed_expenses table, fall back to per-location default
    if location_id is not None:
        fixed_row = conn.execute(
            "SELECT rent, utilities, labor, equipment_lease, total FROM fixed_expenses WHERE strftime('%Y-%m', expense_month)=? AND location_id=?",
            (month_str, location_id)
        ).fetchone()
        if fixed_row:
            rent, utilities, labor, equip, fixed_total = fixed_row
        else:
            rent, utilities, labor, equip, fixed_total = 1000.00, 250.00, 15000.00, 2000.00, 18250.00
    else:
        # Company-wide: sum all locations' fixed expenses (3 locations × $18,250 = $54,750)
        fixed_rows = conn.execute(
            "SELECT rent, utilities, labor, equipment_lease, total FROM fixed_expenses WHERE strftime('%Y-%m', expense_month)=?",
            (month_str,)
        ).fetchall()
        if fixed_rows:
            rent      = sum(r[0] for r in fixed_rows)
            utilities = sum(r[1] for r in fixed_rows)
            labor     = sum(r[2] for r in fixed_rows)
            equip     = sum(r[3] for r in fixed_rows)
            fixed_total = sum(r[4] for r in fixed_rows)
        else:
            # Fall back: 3 locations × defaults
            rent, utilities, labor, equip, fixed_total = 3000.00, 750.00, 45000.00, 6000.00, 54750.00

    variable_total = flavor_cost + container_cost + napkin_cost
    net_income = revenue - variable_total - fixed_total

    conn.close()
    return {
        'revenue':             revenue,
        'variable_flavor':     flavor_cost,
        'variable_containers': container_cost,
        'variable_napkins':    napkin_cost,
        'variable_total':      variable_total,
        'fixed_rent':          rent,
        'fixed_utilities':     utilities,
        'fixed_labor':         labor,
        'fixed_equipment':     equip,
        'fixed_total':         fixed_total,
        'net_income':          net_income,
    }


def get_flavor_sales_quantity(location_id, start_date, end_date):
    """
    Return flavor sales summary sorted by total_scoops DESC.

    location_id=None means all locations.
    start_date / end_date: YYYY-MM-DD strings or datetime.date objects.

    Returns list of dicts: [{'flavor_name', 'total_scoops', 'total_ounces', 'total_revenue'}]
    """
    if isinstance(start_date, date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, date):
        end_date = end_date.strftime("%Y-%m-%d")

    loc_filter = "AND s.location_id = ?" if location_id is not None else ""

    with get_connection() as conn:
        params = [start_date, end_date]
        if location_id is not None:
            params.append(location_id)

        rows = conn.execute(
            f"""SELECT f.flavor_name,
                       COALESCE(SUM(s.scoops), 0)     AS total_scoops,
                       COALESCE(SUM(s.ounces), 0)     AS total_ounces,
                       COALESCE(SUM(s.sale_price), 0) AS total_revenue
                FROM flavors f
                LEFT JOIN sales s ON s.flavor_id = f.flavor_id
                    AND s.sale_date >= ?
                    AND s.sale_date <= ?
                    {loc_filter}
                GROUP BY f.flavor_id, f.flavor_name
                ORDER BY total_scoops DESC""",
            params,
        ).fetchall()

    return [dict(row) for row in rows]


# ── Legacy helpers (used by menu.py) ─────────────────────────────────────────

def get_all_locations():
    """Return list of dicts: [{'location_id', 'location_name'}]."""
    from database import get_locations
    return get_locations()


def get_all_flavors():
    """Return list of dicts: [{'flavor_id', 'flavor_name', 'cost_per_container'}]."""
    from database import get_flavors
    return get_flavors()


def get_all_containers():
    """Return list of dicts: [{'container_id', 'container_name', 'cost_per_100'}]."""
    from database import get_containers
    return get_containers()
