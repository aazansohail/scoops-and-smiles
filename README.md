# Scoops & Smiles 🍨

A multi-location ice cream shop management system built in Python with SQLite. Tracks inventory, purchases, and sales across three store locations, and generates financial reports from a menu-driven CLI.

## Features

- **Inventory tracking** for flavors (by the ounce), containers, and napkins at each location, with automatic low-stock / reorder status flags
- **Purchase recording** that updates inventory and logs every transaction
- **Sales recording** with four cup sizes (Kiddie → Large) that deducts the right amount of ice cream, containers, and napkins per sale
- **Financial reports**: monthly income statement, flavor sales by date range, and current inventory report
- **Input validation** layer — every ID, date, size, and quantity is checked before it touches the database
- **Auto-migrating schema** — the database is created (or upgraded from an older schema) automatically on first launch
- **Demo data generator** that seeds ~6 months of realistic sales history

## Sample output

```
SCOOPS AND SMILES — INCOME STATEMENT
Location: Downtown Rochester
Period: April 2026
─────────────────────────────────────────────
Revenue                          $35,734.00

Variable Expenses
  Flavors                           $317.40
  Containers                        $530.00
  Napkins                            $40.00
  Total Variable                    $887.40

Fixed Expenses
  Rent                            $1,000.00
  Utilities                         $250.00
  Labor                          $15,000.00
  Equipment Lease                 $2,000.00
  Total Fixed                    $18,250.00
─────────────────────────────────────────────
Net Income                       $16,596.60
```

## Architecture

| Module | Role |
|---|---|
| `scoops_smiles.py` | Entry point — initializes the DB and launches the menu |
| `menu.py` | Menu-driven CLI (all user interaction) |
| `logic.py` | Business logic: purchases, sales, inventory math, income statements |
| `database.py` | Schema creation, migration, and data-access helpers |
| `validation.py` | Input validators (raise `ValueError` with descriptive messages) |
| `reports.py` | Formatted text reports |
| `seed_demo_data.py` | Resets transactional data and seeds realistic demo history |

The SQLite database (`scoops_smiles.db`) uses 9 tables — master data (`locations`, `flavors`, `containers`, `napkins_master`), per-location inventory tables, and transaction logs (`purchases`, `sales`, `fixed_expenses`) — with foreign keys enforced.

## Getting started

Requires Python 3 only — no third-party packages (standard library + `sqlite3`).

```bash
python scoops_smiles.py        # run the app (creates the DB on first launch)
python seed_demo_data.py       # optional: fill it with demo data
```

## Tech

Python 3 · SQLite (`sqlite3` stdlib) · no external dependencies
