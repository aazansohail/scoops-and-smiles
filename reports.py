"""
Scoops and Smiles — Reports Module
Generates formatted text reports for all 3 report types.
"""

from datetime import date

SEP = "─" * 45


def _currency(amount):
    return f"${amount:,.2f}"


def _rjust(label, value, width=43):
    """Right-justify a currency value with a left-aligned label in a fixed-width line."""
    return f"{label:<{width - 12}}{value:>12}"


# ── Monthly Income Statement ──────────────────────────────────────────────────

def format_income_statement(data, location_name, year, month):
    """
    Return a formatted income statement string.

    data: dict from logic.get_monthly_income_statement()
    """
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    month_name = month_names[month - 1] if 1 <= month <= 12 else str(month)

    lines = [
        "SCOOPS AND SMILES — INCOME STATEMENT",
        f"Location: {location_name}",
        f"Period: {month_name} {year}",
        SEP,
        _rjust("Revenue", _currency(data["revenue"])),
        "",
        "Variable Expenses",
        _rjust("  Flavors",     _currency(data["variable_flavor"])),
        _rjust("  Containers",  _currency(data["variable_containers"])),
        _rjust("  Napkins",     _currency(data["variable_napkins"])),
        _rjust("  Total Variable", _currency(data["variable_total"])),
        "",
        "Fixed Expenses",
        _rjust("  Rent",            _currency(data["fixed_rent"])),
        _rjust("  Utilities",       _currency(data["fixed_utilities"])),
        _rjust("  Labor",           _currency(data["fixed_labor"])),
        _rjust("  Equipment Lease", _currency(data["fixed_equipment"])),
        _rjust("  Total Fixed",     _currency(data["fixed_total"])),
        SEP,
        _rjust("Net Income", _currency(data["net_income"])),
    ]
    return "\n".join(lines)


# ── Flavor Sales Report ───────────────────────────────────────────────────────

def format_flavor_sales(data, location_name, start_date, end_date):
    """
    Return a formatted flavor sales report string.

    data: list of dicts from logic.get_flavor_sales_quantity()
    start_date / end_date: datetime.date objects or YYYY-MM-DD strings
    """
    if isinstance(start_date, date):
        start_str = start_date.strftime("%Y-%m-%d")
    else:
        start_str = str(start_date)
    if isinstance(end_date, date):
        end_str = end_date.strftime("%Y-%m-%d")
    else:
        end_str = str(end_date)

    header_line = f"{'Flavor':<20} {'Scoops':>8} {'Ounces':>8} {'Revenue':>10}"
    row_sep     = "─" * len(header_line)

    lines = [
        "SCOOPS AND SMILES — FLAVOR SALES",
        f"Location: {location_name}",
        f"Period: {start_str} to {end_str}",
        row_sep,
        header_line,
        row_sep,
    ]

    total_scoops  = 0
    total_ounces  = 0
    total_revenue = 0.0

    for row in data:
        s = row["total_scoops"]
        o = row["total_ounces"]
        r = row["total_revenue"]
        total_scoops  += s
        total_ounces  += o
        total_revenue += r
        lines.append(
            f"{row['flavor_name']:<20} {s:>8,} {o:>8,} {_currency(r):>10}"
        )

    lines += [
        row_sep,
        f"{'TOTAL':<20} {total_scoops:>8,} {total_ounces:>8,} {_currency(total_revenue):>10}",
    ]
    return "\n".join(lines)


# ── Inventory Report ──────────────────────────────────────────────────────────

def format_inventory_report(inv, location_name):
    """
    Return a formatted inventory report string.

    inv: dict from logic.get_current_inventory()
    """
    lines = [
        "SCOOPS AND SMILES — CURRENT INVENTORY",
        f"Location: {location_name}",
        SEP,
        "FLAVORS",
    ]

    for f in inv.get("flavors", []):
        oz     = f["quantity_oz"]
        equiv  = oz / 640
        status = f["status"].upper()
        lines.append(
            f"  {f['flavor_name']:<22} {oz:>8,.0f} oz  ({equiv:.1f} containers)  [{status}]"
        )

    lines += ["", "CONTAINERS"]
    for c in inv.get("containers", []):
        units  = c["quantity_units"]
        status = c["status"].upper()
        lines.append(
            f"  {c['container_name']:<24} {units:>6,} units  [{status}]"
        )

    lines += ["", "NAPKINS"]
    nap    = inv.get("napkins", {"quantity": 0, "status": "critical"})
    qty    = nap["quantity"]
    status = nap["status"].upper()
    lines.append(f"  {'Napkins':<24} {qty:>6,} units  [{status}]")

    return "\n".join(lines)
