"""
seed_demo_data.py — Scoops and Smiles demo data generator

Resets all transactional data (purchases, sales, fixed_expenses,
*_inventory) and seeds realistic data for a class presentation.

Usage:
    python seed_demo_data.py

Requires: scoops_smiles.db to already exist (run scoops_smiles.py once first)
Non-default packages: none (uses only stdlib + sqlite3)
"""

import sqlite3
import os
import sys
import random
import math
from datetime import date, datetime, timedelta

# ── DB path ───────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scoops_smiles.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Step 0: load master IDs from DB ──────────────────────────────────────────

def load_master_data(conn):
    locations = {
        row["location_name"]: row["location_id"]
        for row in conn.execute("SELECT location_id, location_name FROM locations ORDER BY location_id").fetchall()
    }
    flavors = {
        row["flavor_name"]: {"id": row["flavor_id"], "cost": row["cost_per_container"]}
        for row in conn.execute("SELECT flavor_id, flavor_name, cost_per_container FROM flavors ORDER BY flavor_id").fetchall()
    }
    containers = {
        row["container_name"]: {"id": row["container_id"], "cost_per_100": row["cost_per_100"]}
        for row in conn.execute("SELECT container_id, container_name, cost_per_100 FROM containers ORDER BY container_id").fetchall()
    }
    napkin_row = conn.execute("SELECT cost_per_10000 FROM napkins_master WHERE id=1").fetchone()
    napkin_cost = napkin_row["cost_per_10000"] if napkin_row else 20.00
    return locations, flavors, containers, napkin_cost


# ── Step 1: reset transactional tables ───────────────────────────────────────

def reset_tables(conn, locations, flavors, containers):
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM purchases")
    conn.execute("DELETE FROM sales")
    conn.execute("DELETE FROM fixed_expenses")
    conn.execute("DELETE FROM flavor_inventory")
    conn.execute("DELETE FROM container_inventory")
    conn.execute("DELETE FROM napkin_inventory")

    # Re-insert zero rows for all location × flavor
    fi_rows = [
        (loc_id, flav_info["id"], 0.0, now)
        for loc_id in locations.values()
        for flav_info in flavors.values()
    ]
    conn.executemany(
        "INSERT INTO flavor_inventory (location_id, flavor_id, quantity_oz, last_updated) VALUES (?, ?, ?, ?)",
        fi_rows,
    )

    # Re-insert zero rows for all location × container
    ci_rows = [
        (loc_id, cont_info["id"], 0, now)
        for loc_id in locations.values()
        for cont_info in containers.values()
    ]
    conn.executemany(
        "INSERT INTO container_inventory (location_id, container_id, quantity_units, last_updated) VALUES (?, ?, ?, ?)",
        ci_rows,
    )

    # Re-insert zero rows for all locations
    ni_rows = [(loc_id, 0, now) for loc_id in locations.values()]
    conn.executemany(
        "INSERT INTO napkin_inventory (location_id, quantity, last_updated) VALUES (?, ?, ?)",
        ni_rows,
    )
    conn.commit()
    print("  [Step 1] Tables reset and zero-inventory rows inserted.")


# ── Step 2: set starting inventory ───────────────────────────────────────────

def set_starting_inventory(locations, flavors, containers):
    """Return in-memory dicts with starting inventory levels (not yet written to DB)."""
    # Downtown needs much larger starting stock due to high volume
    flavor_ranges = {
        "Downtown Rochester": {"Vanilla":(30,45), "Chocolate":(30,45), "Cookies & Cream":(25,38), "Neapolitan":(18,28), "Cookie Dough":(18,28)},
        "Pittsford":          {"Vanilla":(22,32), "Chocolate":(22,32), "Cookies & Cream":(18,26), "Neapolitan":(12,20), "Cookie Dough":(12,20)},
        "Henrietta":          {"Vanilla":(14,22), "Chocolate":(14,22), "Cookies & Cream":(11,18), "Neapolitan":(8,14),  "Cookie Dough":(8,14)},
    }
    container_ranges = {
        "Downtown Rochester": {"Standard Ice Cream Cone":(1000,1800), "Waffle Cone":(700,1200),  "Dish with Spoon":(1000,1800)},
        "Pittsford":          {"Standard Ice Cream Cone":(700,1200),  "Waffle Cone":(500,900),   "Dish with Spoon":(700,1200)},
        "Henrietta":          {"Standard Ice Cream Cone":(500,900),   "Waffle Cone":(350,650),   "Dish with Spoon":(500,900)},
    }

    # flavor_inv[loc_id][flavor_id] = oz
    flavor_inv = {}
    loc_id_to_name = {v: k for k, v in locations.items()}
    for loc_id in locations.values():
        loc_name = loc_id_to_name[loc_id]
        flavor_inv[loc_id] = {}
        for fname, finfo in flavors.items():
            lo, hi = flavor_ranges[loc_name][fname]
            flavor_inv[loc_id][finfo["id"]] = random.randint(lo, hi) * 640

    # container_inv[loc_id][container_id] = units
    container_inv = {}
    for loc_id in locations.values():
        loc_name = loc_id_to_name[loc_id]
        container_inv[loc_id] = {}
        for cname, cinfo in containers.items():
            lo, hi = container_ranges[loc_name][cname]
            container_inv[loc_id][cinfo["id"]] = random.randint(lo, hi)

    # napkin_inv[loc_id] = qty
    napkin_inv = {loc_id: 10000 for loc_id in locations.values()}

    print("  [Step 2] Starting inventory levels computed.")
    return flavor_inv, container_inv, napkin_inv


# ── Step 3: weekly purchase history ──────────────────────────────────────────

def get_last_n_mondays(n, reference_date):
    """Return list of the last n Mondays (as date objects) on or before reference_date."""
    mondays = []
    d = reference_date
    # Walk back to the most recent Monday
    while d.weekday() != 0:
        d -= timedelta(days=1)
    for _ in range(n):
        mondays.append(d)
        d -= timedelta(weeks=1)
    mondays.reverse()
    return mondays


def generate_purchases(conn, locations, flavors, containers, napkin_cost,
                       flavor_inv, container_inv, napkin_inv):
    today = date(2026, 5, 3)
    mondays = get_last_n_mondays(12, today)

    purchase_rows = []

    # Pre-build the full sales data in memory so we can look up prior-week consumption
    # We'll generate purchases week by week using the in-memory flavor/container/napkin_inv
    # which gets updated by purchases, then generate sales day by day

    # Actually: since sales haven't been generated yet when we call this,
    # we use a simpler approach: estimate weekly consumption based on location volume
    # Downtown ~250/day × 7 = 1750 sales/week; avg 10oz/sale = 17,500oz = 27.3 containers
    # Split across 5 flavors by weight = about 5.5 containers per flavor per week
    # Pittsford ~185/day × 7 = 1295 sales/week; ~13oz avg = 16,835oz = 26 containers total
    # Henrietta ~120/day × 7 = 840 sales/week; avg 10oz = 8,400oz = 13.1 containers total

    # Flavor distribution weights (same as sales): 28/25/22/13/12 = 100
    flavor_weights_pct = {"Vanilla":0.28, "Chocolate":0.25, "Cookies & Cream":0.22, "Neapolitan":0.13, "Cookie Dough":0.12}
    # Container distribution: 40/25/35
    container_weights_pct = {"Standard Ice Cream Cone":0.40, "Waffle Cone":0.25, "Dish with Spoon":0.35}
    # Size distribution (oz per sale): Kiddie 18%×4oz + Small 32%×8oz + Medium 32%×12oz + Large 18%×16oz
    avg_oz_per_sale = 0.18*4 + 0.32*8 + 0.32*12 + 0.18*16  # = 9.92 oz avg

    # Expected weekly sales per location (baseline, before day multiplier avg)
    # avg multiplier over week = (4×1.0 + 1×1.5 + 1×1.9 + 1×1.6)/7 = 9.0/7 = 1.286
    avg_multiplier = (4*1.0 + 1*1.5 + 1*1.9 + 1*1.6) / 7

    loc_daily_midpoint = {
        "Downtown Rochester": (220 + 280) / 2,  # 250
        "Pittsford":          (160 + 210) / 2,  # 185
        "Henrietta":          (100 + 140) / 2,  # 120
    }

    # Simulate running napkin balance per location so purchases fire at the right cadence.
    # All purchases are pre-generated before sales run, so we track a simulated balance
    # that represents expected depletion from sales.
    napkin_sim = {loc_id: napkin_inv[loc_id] for loc_id in locations.values()}

    for week_index, monday in enumerate(mondays):
        monday_str = monday.strftime("%Y-%m-%d")

        for loc_name, loc_id in locations.items():
            daily_mid = loc_daily_midpoint[loc_name]
            weekly_sales_est = daily_mid * avg_multiplier * 7
            weekly_oz_est = weekly_sales_est * avg_oz_per_sale

            # FLAVORS: buy enough to cover estimated next-week consumption + 15% buffer
            for fname, finfo in flavors.items():
                frac = flavor_weights_pct[fname]
                oz_needed = weekly_oz_est * frac * 1.15  # +15% buffer
                containers_to_buy = max(1, math.ceil(oz_needed / 640))
                oz_added = containers_to_buy * 640
                total_cost = round(finfo["cost"] * containers_to_buy, 2)
                flavor_inv[loc_id][finfo["id"]] += oz_added
                purchase_rows.append((
                    loc_id, monday_str, "flavor", finfo["id"],
                    containers_to_buy, total_cost
                ))

            # CONTAINERS: buy enough to cover estimated next-week sales + 10% buffer
            for cname, cinfo in containers.items():
                frac = container_weights_pct[cname]
                units_needed = weekly_sales_est * frac * 1.10
                packs_to_buy = max(1, math.ceil(units_needed / 100))
                units_added = packs_to_buy * 100
                total_cost = round(cinfo["cost_per_100"] * packs_to_buy, 2)
                container_inv[loc_id][cinfo["id"]] += units_added
                purchase_rows.append((
                    loc_id, monday_str, "container", cinfo["id"],
                    packs_to_buy, total_cost
                ))

            # NAPKINS: simulate expected consumption this week and buy if projected to go below 4,000.
            # 2 napkins per sale; check simulated balance after this week's expected usage.
            weekly_napkin_use = int(weekly_sales_est * 2)
            napkin_sim[loc_id] -= weekly_napkin_use
            if napkin_sim[loc_id] < 4000:
                total_cost = napkin_cost * 1
                napkin_sim[loc_id] += 10000
                napkin_inv[loc_id] += 10000
                purchase_rows.append((
                    loc_id, monday_str, "napkins", None,
                    1, total_cost
                ))

    conn.executemany(
        """INSERT INTO purchases
               (location_id, purchase_date, item_type, item_id, quantity_purchased, total_cost)
           VALUES (?, ?, ?, ?, ?, ?)""",
        purchase_rows,
    )
    conn.commit()
    print(f"  [Step 3] {len(purchase_rows)} purchase records inserted across 12 weeks.")
    return purchase_rows


# ── Step 4: daily sales ───────────────────────────────────────────────────────

def generate_sales(conn, locations, flavors, containers,
                   flavor_inv, container_inv, napkin_inv):
    # Weighted choices
    flavor_names   = ["Vanilla", "Chocolate", "Cookies & Cream", "Neapolitan", "Cookie Dough"]
    flavor_weights = [28, 25, 22, 13, 12]

    size_names   = ["Kiddie", "Small", "Medium", "Large"]
    size_weights = [18, 32, 32, 18]
    size_map = {
        "Kiddie": {"scoops": 1, "ounces": 4,  "price": 3.00},
        "Small":  {"scoops": 2, "ounces": 8,  "price": 3.50},
        "Medium": {"scoops": 3, "ounces": 12, "price": 4.00},
        "Large":  {"scoops": 4, "ounces": 16, "price": 4.50},
    }

    container_names   = ["Standard Ice Cream Cone", "Waffle Cone", "Dish with Spoon"]
    container_weights = [40, 25, 35]

    day_multipliers = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.5, 5: 1.9, 6: 1.6}

    location_base_sales = {
        "Downtown Rochester": (220, 280),
        "Pittsford":          (160, 210),
        "Henrietta":          (100, 140),
    }

    start_date = date(2026, 2, 1)
    end_date   = date(2026, 5, 3)

    sale_rows = []
    skipped = 0

    current = start_date
    while current <= end_date:
        dow = current.weekday()
        multiplier = day_multipliers[dow]
        day_str = current.strftime("%Y-%m-%d")

        for loc_name, loc_id in locations.items():
            lo, hi = location_base_sales[loc_name]
            base_n = random.randint(lo, hi)
            n_sales = int(base_n * multiplier)

            for _ in range(n_sales):
                fname = random.choices(flavor_names, weights=flavor_weights, k=1)[0]
                size  = random.choices(size_names,   weights=size_weights,   k=1)[0]
                cname = random.choices(container_names, weights=container_weights, k=1)[0]

                fid  = flavors[fname]["id"]
                cid  = containers[cname]["id"]
                info = size_map[size]
                ounces = info["ounces"]
                price  = info["price"]
                scoops = info["scoops"]

                # Stock check
                if (flavor_inv[loc_id][fid]  >= ounces and
                        container_inv[loc_id][cid] >= 1 and
                        napkin_inv[loc_id]         >= 2):
                    # Decrement in-memory inventory
                    flavor_inv[loc_id][fid]    -= ounces
                    container_inv[loc_id][cid] -= 1
                    napkin_inv[loc_id]         -= 2

                    # Build datetime string
                    hour   = random.randint(12, 20)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    sale_dt = f"{day_str} {hour:02d}:{minute:02d}:{second:02d}"

                    sale_rows.append((
                        loc_id, sale_dt, fid, cid,
                        size, scoops, ounces, price
                    ))
                else:
                    skipped += 1

        current += timedelta(days=1)

    # Bulk insert all sales
    conn.executemany(
        """INSERT INTO sales
               (location_id, sale_date, flavor_id, container_id,
                size, scoops, ounces, sale_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        sale_rows,
    )
    conn.commit()
    print(f"  [Step 4] {len(sale_rows)} sale records inserted. {skipped} sales skipped (low stock).")
    return sale_rows, skipped


# ── Step 5: fixed expenses ────────────────────────────────────────────────────

def generate_fixed_expenses(conn, locations):
    months = [
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]
    expense_rows = []
    for loc_id in locations.values():
        for m in months:
            expense_rows.append((
                loc_id, m.strftime("%Y-%m-%d"),
                1000.00, 250.00, 15000.00, 2000.00, 18250.00
            ))
    conn.executemany(
        """INSERT INTO fixed_expenses
               (location_id, expense_month, rent, utilities, labor, equipment_lease, total)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        expense_rows,
    )
    conn.commit()
    print(f"  [Step 5] {len(expense_rows)} fixed expense records inserted (3 locations × 3 months).")


# ── Write final inventory to DB ───────────────────────────────────────────────

def write_inventory_to_db(conn, flavor_inv, container_inv, napkin_inv):
    now = datetime.now().isoformat()

    fi_rows = [
        (qty, now, loc_id, fid)
        for loc_id, fmap in flavor_inv.items()
        for fid, qty in fmap.items()
    ]
    conn.executemany(
        "UPDATE flavor_inventory SET quantity_oz=?, last_updated=? WHERE location_id=? AND flavor_id=?",
        fi_rows,
    )

    ci_rows = [
        (qty, now, loc_id, cid)
        for loc_id, cmap in container_inv.items()
        for cid, qty in cmap.items()
    ]
    conn.executemany(
        "UPDATE container_inventory SET quantity_units=?, last_updated=? WHERE location_id=? AND container_id=?",
        ci_rows,
    )

    ni_rows = [(qty, now, loc_id) for loc_id, qty in napkin_inv.items()]
    conn.executemany(
        "UPDATE napkin_inventory SET quantity=?, last_updated=? WHERE location_id=?",
        ni_rows,
    )
    conn.commit()
    print("  [Inventory] Final inventory written to DB.")


# ── Step 6: low-stock overrides ───────────────────────────────────────────────

def apply_low_stock_overrides(conn, locations, flavors, containers,
                               flavor_inv, container_inv, napkin_inv):
    now = datetime.now().isoformat()
    dt_id  = locations["Downtown Rochester"]
    pit_id = locations["Pittsford"]
    hen_id = locations["Henrietta"]

    cd_id  = flavors["Cookie Dough"]["id"]
    neo_id = flavors["Neapolitan"]["id"]
    van_id = flavors["Vanilla"]["id"]

    sc_id  = containers["Standard Ice Cream Cone"]["id"]
    dws_id = containers["Dish with Spoon"]["id"]

    overrides = [
        # (table, set_col, value, where_col1, val1, where_col2, val2)
        ("flavor_inventory",    "quantity_oz",    500,  "location_id", dt_id,  "flavor_id",    cd_id),
        ("container_inventory", "quantity_units",  40,  "location_id", dt_id,  "container_id", sc_id),
        ("flavor_inventory",    "quantity_oz",    1500, "location_id", pit_id, "flavor_id",    neo_id),
        ("flavor_inventory",    "quantity_oz",    1800, "location_id", hen_id, "flavor_id",    van_id),
        ("container_inventory", "quantity_units",  35,  "location_id", hen_id, "container_id", dws_id),
    ]

    for tbl, col, val, wc1, wv1, wc2, wv2 in overrides:
        conn.execute(
            f"UPDATE {tbl} SET {col}=?, last_updated=? WHERE {wc1}=? AND {wc2}=?",
            (val, now, wv1, wv2),
        )
        # Keep in-memory dicts in sync too
        if tbl == "flavor_inventory":
            flavor_inv[wv1][wv2] = val
        elif tbl == "container_inventory":
            container_inv[wv1][wv2] = val

    # Pittsford napkins
    conn.execute(
        "UPDATE napkin_inventory SET quantity=?, last_updated=? WHERE location_id=?",
        (800, now, pit_id),
    )
    napkin_inv[pit_id] = 800

    conn.commit()
    print("  [Step 6] Low-stock overrides applied.")


# ── Step 7: print summary ─────────────────────────────────────────────────────

def status_label_flavor(qty):
    if qty <= 640:
        return "CRITICAL"
    elif qty <= 1920:
        return "LOW"
    return "OK"


def status_label_container(qty):
    if qty <= 50:
        return "CRITICAL"
    elif qty <= 150:
        return "LOW"
    return "OK"


def status_label_napkin(qty):
    if qty <= 1000:
        return "CRITICAL"
    elif qty <= 3000:
        return "LOW"
    return "OK"


def print_summary(conn, locations, flavors, containers,
                  flavor_inv, container_inv, napkin_inv,
                  purchase_rows, sale_rows, skipped):

    # Purchases totals
    total_purchase_records = len(purchase_rows)
    total_purchase_spend = sum(r[5] for r in purchase_rows)

    # Sales totals
    total_sale_records = len(sale_rows)
    total_revenue = sum(r[7] for r in sale_rows)

    # April 2026 income statement (all locations combined)
    rev_april = conn.execute(
        "SELECT COALESCE(SUM(sale_price),0) FROM sales "
        "WHERE strftime('%Y-%m', sale_date)='2026-04'"
    ).fetchone()[0]

    var_april = conn.execute(
        "SELECT COALESCE(SUM(total_cost),0) FROM purchases "
        "WHERE strftime('%Y-%m', purchase_date)='2026-04'"
    ).fetchone()[0]

    fixed_april = 18250.00 * 3  # 3 locations
    net_april = rev_april - var_april - fixed_april

    # Build flavor/container name lists ordered by id
    flavor_ordered = sorted(flavors.items(), key=lambda x: x[1]["id"])
    container_ordered = sorted(containers.items(), key=lambda x: x[1]["id"])

    print()
    print("=" * 60)
    print("  SCOOPS AND SMILES — DEMO DATA SUMMARY")
    print("=" * 60)
    print()
    print(f"DATABASE: scoops_smiles.db")
    print(f"SEEDED:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("PURCHASES")
    print(f"  Total purchase records:   {total_purchase_records}")
    print(f"  Total purchase spend:     ${total_purchase_spend:,.2f}")
    print(f"  Weekly orders × weeks:    3 locations × 12 weeks")
    print()
    print("SALES")
    print(f"  Total sale records:       {total_sale_records:,}")
    print(f"  Total revenue:            ${total_revenue:,.2f}")
    print(f"  Date range:               2026-02-01 to 2026-05-03")
    print(f"  Sales skipped (low stock): {skipped}")
    print()
    print("FIXED EXPENSES")
    print(f"  Records inserted:         9  (3 locations × 3 months)")
    print(f"  Total fixed costs:        $164,250.00")
    print()
    print("FINAL INVENTORY (after low-stock overrides)")

    loc_order = ["Downtown Rochester", "Pittsford", "Henrietta"]
    container_short = {
        "Standard Ice Cream Cone": "Standard Cone",
        "Waffle Cone":             "Waffle Cone",
        "Dish with Spoon":         "Dish w/ Spoon",
    }

    for loc_name in loc_order:
        loc_id = locations[loc_name]
        print(f"  {loc_name}:")
        for fname, finfo in flavor_ordered:
            qty = flavor_inv[loc_id][finfo["id"]]
            st  = status_label_flavor(qty)
            print(f"    {fname:<18} {qty:>6,.0f} oz   [{st}]")
        for cname, cinfo in container_ordered:
            qty = container_inv[loc_id][cinfo["id"]]
            st  = status_label_container(qty)
            short = container_short.get(cname, cname)
            print(f"    {short:<18} {qty:>6,} units [{st}]")
        nqty = napkin_inv[loc_id]
        nst  = status_label_napkin(nqty)
        print(f"    {'Napkins':<18} {nqty:>6,} units  [{nst}]")

    print()
    print("REPORTS PREVIEW")
    print("  Monthly Income Statement (April 2026, All Locations):")
    print(f"    Revenue:          ${rev_april:,.2f}")
    print(f"    Variable Costs:   ${var_april:,.2f}")
    print(f"    Fixed Costs:      ${fixed_april:,.2f}")
    print(f"    Net Income:       ${net_april:,.2f}")
    print()
    print("=" * 60)
    print("  Ready for your class presentation!")
    print("=" * 60)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Please run scoops_smiles.py once to initialize the database first.")
        sys.exit(1)

    answer = input("This will reset all demo data. Continue? (y/n): ").strip().lower()
    if answer != "y":
        print("Aborted.")
        sys.exit(0)

    print()
    print("Seeding demo data...")

    random.seed(42)

    conn = get_conn()

    # Step 0: load master data
    locations, flavors, containers, napkin_cost = load_master_data(conn)
    print(f"  [Step 0] Loaded master data: {len(locations)} locations, "
          f"{len(flavors)} flavors, {len(containers)} containers.")

    # Step 1: reset
    reset_tables(conn, locations, flavors, containers)

    # Step 2: starting inventory (in memory)
    flavor_inv, container_inv, napkin_inv = set_starting_inventory(locations, flavors, containers)

    # Step 3: purchases (also updates in-memory inventory)
    purchase_rows = generate_purchases(
        conn, locations, flavors, containers, napkin_cost,
        flavor_inv, container_inv, napkin_inv
    )

    # Step 4: daily sales (decrements in-memory inventory)
    sale_rows, skipped = generate_sales(
        conn, locations, flavors, containers,
        flavor_inv, container_inv, napkin_inv
    )

    # Write final inventory state to DB
    write_inventory_to_db(conn, flavor_inv, container_inv, napkin_inv)

    # Step 5: fixed expenses
    generate_fixed_expenses(conn, locations)

    # Step 6: low-stock overrides
    apply_low_stock_overrides(conn, locations, flavors, containers,
                               flavor_inv, container_inv, napkin_inv)

    # Step 7: summary
    print_summary(conn, locations, flavors, containers,
                  flavor_inv, container_inv, napkin_inv,
                  purchase_rows, sale_rows, skipped)

    conn.close()


if __name__ == "__main__":
    main()
