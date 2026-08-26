"""
Scoops and Smiles — Entry Point
Run with: python3 scoops_smiles.py
"""

import database
import menu

if __name__ == "__main__":
    database.initialize_database()
    menu.main()
