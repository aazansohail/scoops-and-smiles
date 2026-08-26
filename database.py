"""
Scoops and Smiles — Database module
Auto-creates scoops_smiles.db with the full schema on first launch.
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "scoops_smiles.db")


def get_connection():
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _needs_migration(conn):
    """Return True if the existing DB uses the old schema (lacks required columns)."""
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "flavor_inventory" not in tables:
        return True
    if "purchases" not in tables:
        return True
    # Check flavors table uses new column names
    flavor_cols = {row[1] for row in conn.execute("PRAGMA table_info(flavors)").fetchall()}
    if "flavor_name" not in flavor_cols:
        return True
    return False


def _backup_old_db():
    """Move the old DB out of the way so we can start fresh."""
    if os.path.exists(DB_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = DB_PATH.replace(".db", f"_backup_{ts}.db")
        shutil.move(DB_PATH, backup)
        print(f"[database] Old schema detected — backed up to {os.path.basename(backup)}")


def _create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            location_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flavors (
            flavor_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            flavor_name         TEXT NOT NULL,
            cost_per_container  REAL NOT NULL,
            container_size_oz   INTEGER NOT NULL DEFAULT 640
        );

        CREATE TABLE IF NOT EXISTS containers (
            container_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            container_name TEXT NOT NULL,
            cost_per_100   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS napkins_master (
            id                INTEGER PRIMARY KEY DEFAULT 1,
            cost_per_10000    REAL NOT NULL DEFAULT 20.00,
            napkins_per_order INTEGER NOT NULL DEFAULT 2
        );

        CREATE TABLE IF NOT EXISTS flavor_inventory (
            location_id  INTEGER NOT NULL,
            flavor_id    INTEGER NOT NULL,
            quantity_oz  REAL NOT NULL DEFAULT 0,
            last_updated DATETIME,
            PRIMARY KEY (location_id, flavor_id),
            FOREIGN KEY (location_id) REFERENCES locations(location_id),
            FOREIGN KEY (flavor_id)   REFERENCES flavors(flavor_id)
        );

        CREATE TABLE IF NOT EXISTS container_inventory (
            location_id    INTEGER NOT NULL,
            container_id   INTEGER NOT NULL,
            quantity_units INTEGER NOT NULL DEFAULT 0,
            last_updated   DATETIME,
            PRIMARY KEY (location_id, container_id),
            FOREIGN KEY (location_id)  REFERENCES locations(location_id),
            FOREIGN KEY (container_id) REFERENCES containers(container_id)
        );

        CREATE TABLE IF NOT EXISTS napkin_inventory (
            location_id  INTEGER PRIMARY KEY,
            quantity     INTEGER NOT NULL DEFAULT 0,
            last_updated DATETIME,
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        );

        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id         INTEGER NOT NULL,
            purchase_date       DATE NOT NULL,
            item_type           TEXT NOT NULL,
            item_id             INTEGER,
            quantity_purchased  INTEGER NOT NULL,
            total_cost          REAL NOT NULL,
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            sale_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            sale_date   DATETIME NOT NULL,
            flavor_id   INTEGER NOT NULL,
            container_id INTEGER NOT NULL,
            size        TEXT NOT NULL,
            scoops      INTEGER NOT NULL,
            ounces      INTEGER NOT NULL,
            sale_price  REAL NOT NULL,
            FOREIGN KEY (location_id)  REFERENCES locations(location_id),
            FOREIGN KEY (flavor_id)    REFERENCES flavors(flavor_id),
            FOREIGN KEY (container_id) REFERENCES containers(container_id)
        );

        CREATE TABLE IF NOT EXISTS fixed_expenses (
            expense_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id     INTEGER NOT NULL,
            expense_month   DATE NOT NULL,
            rent            REAL NOT NULL DEFAULT 1000.00,
            utilities       REAL NOT NULL DEFAULT 250.00,
            labor           REAL NOT NULL DEFAULT 15000.00,
            equipment_lease REAL NOT NULL DEFAULT 2000.00,
            total           REAL NOT NULL DEFAULT 18250.00,
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        );
    """)


def _seed_master_data(conn):
    """Seed all master / reference data if tables are empty."""
    # Locations
    if conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO locations (location_name) VALUES (?)",
            [("Downtown Rochester",), ("Pittsford",), ("Henrietta",)],
        )

    # Flavors
    if conn.execute("SELECT COUNT(*) FROM flavors").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO flavors (flavor_name, cost_per_container) VALUES (?, ?)",
            [
                ("Vanilla",         1.80),
                ("Chocolate",       1.80),
                ("Cookies & Cream", 1.90),
                ("Neapolitan",      1.85),
                ("Cookie Dough",    1.95),
            ],
        )

    # Containers
    if conn.execute("SELECT COUNT(*) FROM containers").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO containers (container_name, cost_per_100) VALUES (?, ?)",
            [
                ("Standard Ice Cream Cone", 5.00),
                ("Waffle Cone",             6.00),
                ("Dish with Spoon",         4.50),
            ],
        )

    # Napkins master (single row, id=1)
    if conn.execute("SELECT COUNT(*) FROM napkins_master").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO napkins_master (id, cost_per_10000, napkins_per_order) VALUES (1, 20.00, 2)"
        )

    # Seed flavor_inventory (0 oz) for every location × flavor
    if conn.execute("SELECT COUNT(*) FROM flavor_inventory").fetchone()[0] == 0:
        locations = [row[0] for row in conn.execute("SELECT location_id FROM locations")]
        flavors   = [row[0] for row in conn.execute("SELECT flavor_id FROM flavors")]
        now = datetime.now().isoformat()
        rows = [(loc, flav, 0.0, now) for loc in locations for flav in flavors]
        conn.executemany(
            "INSERT INTO flavor_inventory (location_id, flavor_id, quantity_oz, last_updated) VALUES (?, ?, ?, ?)",
            rows,
        )

    # Seed container_inventory (0 units) for every location × container
    if conn.execute("SELECT COUNT(*) FROM container_inventory").fetchone()[0] == 0:
        locations  = [row[0] for row in conn.execute("SELECT location_id FROM locations")]
        containers = [row[0] for row in conn.execute("SELECT container_id FROM containers")]
        now = datetime.now().isoformat()
        rows = [(loc, cont, 0, now) for loc in locations for cont in containers]
        conn.executemany(
            "INSERT INTO container_inventory (location_id, container_id, quantity_units, last_updated) VALUES (?, ?, ?, ?)",
            rows,
        )

    # Seed napkin_inventory (0 units) for every location
    if conn.execute("SELECT COUNT(*) FROM napkin_inventory").fetchone()[0] == 0:
        locations = [row[0] for row in conn.execute("SELECT location_id FROM locations")]
        now = datetime.now().isoformat()
        rows = [(loc, 0, now) for loc in locations]
        conn.executemany(
            "INSERT INTO napkin_inventory (location_id, quantity, last_updated) VALUES (?, ?, ?)",
            rows,
        )


def initialize_database():
    """Create all tables and seed master data. Backs up old schema if detected."""
    # Check for old schema before connecting for writes
    if os.path.exists(DB_PATH):
        probe = sqlite3.connect(DB_PATH)
        probe.row_factory = sqlite3.Row
        try:
            needs = _needs_migration(probe)
        finally:
            probe.close()
        if needs:
            _backup_old_db()

    with get_connection() as conn:
        _create_tables(conn)
        _seed_master_data(conn)


def get_locations():
    """Return list of dicts with location_id and location_name."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT location_id, location_name FROM locations ORDER BY location_id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_flavors():
    """Return list of dicts for all flavors."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT flavor_id, flavor_name, cost_per_container, container_size_oz "
            "FROM flavors ORDER BY flavor_id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_containers():
    """Return list of dicts for all container types."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT container_id, container_name, cost_per_100 "
            "FROM containers ORDER BY container_id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_napkins_master():
    """Return the single napkins configuration row as a dict."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM napkins_master WHERE id = 1").fetchone()
    return dict(row) if row else {"id": 1, "cost_per_10000": 20.00, "napkins_per_order": 2}
