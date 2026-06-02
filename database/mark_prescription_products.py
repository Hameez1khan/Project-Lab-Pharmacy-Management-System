import sqlite3

conn = sqlite3.connect("database/pharmacy.db")
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
