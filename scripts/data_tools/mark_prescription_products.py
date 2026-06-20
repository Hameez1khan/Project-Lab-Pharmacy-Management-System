import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "database" / "pharmacy.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

products_to_mark = [
    "Amoxicillin",
    "Augmentin",
    "Azithromycin",
    "Metronidazole",
    "Insulin Regular",
]

for name in products_to_mark:
    cursor.execute("""
        UPDATE products
        SET prescription_required = 1
        WHERE name = ?
    """, (name,))

conn.commit()
conn.close()

print("Selected products marked as prescription-required.")
