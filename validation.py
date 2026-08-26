"""
Scoops and Smiles — Validation utilities
All validators raise ValueError with a descriptive message on failure.
"""

from datetime import date

VALID_SIZES = ['Kiddie', 'Small', 'Medium', 'Large']


def validate_location(location_id, conn):
    """Raise ValueError if location_id is not in the locations table."""
    row = conn.execute(
        "SELECT location_id FROM locations WHERE location_id = ?", (location_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Invalid location_id: {location_id}")


def validate_flavor(flavor_id, conn):
    """Raise ValueError if flavor_id is not in the flavors table."""
    row = conn.execute(
        "SELECT flavor_id FROM flavors WHERE flavor_id = ?", (flavor_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Invalid flavor_id: {flavor_id}")


def validate_container(container_id, conn):
    """Raise ValueError if container_id is not in the containers table."""
    row = conn.execute(
        "SELECT container_id FROM containers WHERE container_id = ?", (container_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Invalid container_id: {container_id}")


def validate_size(size):
    """Raise ValueError if size is not one of the valid sizes."""
    if size not in VALID_SIZES:
        raise ValueError(f"Invalid size '{size}'. Valid sizes: {VALID_SIZES}")


def validate_quantity(qty):
    """Raise ValueError if qty is not a positive integer."""
    try:
        val = int(qty)
        if val <= 0:
            raise ValueError(f"Quantity must be a positive integer, got {qty}")
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a positive integer, got {qty!r}")


def validate_date_not_future(d):
    """
    Raise ValueError if d is in the future.
    d can be a datetime.date object or a YYYY-MM-DD string.
    """
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            raise ValueError(f"Invalid date format '{d}'. Expected YYYY-MM-DD.")
    if d > date.today():
        raise ValueError(f"Date {d} cannot be in the future.")


def validate_inventory_for_sale(location_id, flavor_id, container_id, size, conn):
    """
    Raise ValueError with a specific message if there is not enough stock to complete
    a sale of the given size at the specified location.
    """
    from logic import SIZE_MAP
    if size not in SIZE_MAP:
        raise ValueError(f"Invalid size '{size}'.")

    ounces = SIZE_MAP[size]['ounces']

    fi = conn.execute(
        "SELECT quantity_oz FROM flavor_inventory WHERE location_id = ? AND flavor_id = ?",
        (location_id, flavor_id)
    ).fetchone()
    have_oz = fi["quantity_oz"] if fi else 0
    if have_oz < ounces:
        raise ValueError(
            f"Insufficient flavor stock: need {ounces} oz, have {have_oz:.0f} oz"
        )

    ci = conn.execute(
        "SELECT quantity_units FROM container_inventory WHERE location_id = ? AND container_id = ?",
        (location_id, container_id)
    ).fetchone()
    have_units = ci["quantity_units"] if ci else 0
    if have_units < 1:
        raise ValueError(
            f"Insufficient container stock: need 1 unit, have {have_units} units"
        )

    ni = conn.execute(
        "SELECT quantity FROM napkin_inventory WHERE location_id = ?",
        (location_id,)
    ).fetchone()
    have_napkins = ni["quantity"] if ni else 0
    if have_napkins < 2:
        raise ValueError(
            f"Insufficient napkins: need 2, have {have_napkins} units"
        )


# ── Legacy helpers kept for backward compatibility ────────────────────────────

def validate_positive_integer(value, field_name):
    """Return (True, None) if valid, else (False, error_message)."""
    try:
        num = int(value)
        if num > 0:
            return (True, None)
        return (False, f"{field_name} must be a positive whole number")
    except (ValueError, TypeError):
        return (False, f"{field_name} must be a positive whole number")


def validate_date(value):
    """Return (True, None) if YYYY-MM-DD format, else (False, error_message)."""
    try:
        date.fromisoformat(str(value))
        return (True, None)
    except (ValueError, TypeError):
        return (False, "Date must be in YYYY-MM-DD format (e.g. 2026-03-15)")


def validate_month(value):
    """Return (True, None) if 1-12, else (False, error_message)."""
    try:
        num = int(value)
        if 1 <= num <= 12:
            return (True, None)
        return (False, "Month must be a number between 1 and 12")
    except (ValueError, TypeError):
        return (False, "Month must be a number between 1 and 12")


def validate_year(value):
    """Return (True, None) if 4-digit year 2000-2099, else (False, error_message)."""
    try:
        num = int(value)
        if 2000 <= num <= 2099:
            return (True, None)
        return (False, "Year must be a 4-digit year (e.g. 2026)")
    except (ValueError, TypeError):
        return (False, "Year must be a 4-digit year (e.g. 2026)")
