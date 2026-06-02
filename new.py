import sqlite3

DB_PATH = "database/pharmacy.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM products
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY name
""")
duplicate_names = [row["name"] for row in cursor.fetchall()]

if not duplicate_names:
    print("No duplicate products found.")
    conn.close()
    raise SystemExit

for name in duplicate_names:
    cursor.execute("""
    SELECT *
    FROM products
    WHERE name = ?
    ORDER BY id ASC
    """, (name,))
    rows = cursor.fetchall()

    keeper = rows[0]
    duplicates = rows[1:]

    keeper_id = keeper["id"]

    merged_dosage_form = keeper["dosage_form"]
    merged_barcode = keeper["barcode"]
    merged_price = keeper["selling_price"]
    merged_min_stock = keeper["min_stock_level"]
    merged_category = keeper["category"]
    merged_manufacturer = keeper["manufacturer"]
    merged_prescription_required = keeper["prescription_required"]

    for row in rows[1:]:
        if not merged_dosage_form and row["dosage_form"]:
            merged_dosage_form = row["dosage_form"]
        if not merged_barcode and row["barcode"]:
            merged_barcode = row["barcode"]
        if not merged_category and row["category"]:
            merged_category = row["category"]
        if not merged_manufacturer and row["manufacturer"]:
            merged_manufacturer = row["manufacturer"]

        if row["selling_price"] is not None:
            merged_price = row["selling_price"]

        if row["min_stock_level"] is not None:
            merged_min_stock = max(merged_min_stock or 0, row["min_stock_level"] or 0)

        merged_prescription_required = max(
            merged_prescription_required or 0,
            row["prescription_required"] or 0
        )

    cursor.execute("""
    UPDATE products
    SET dosage_form = ?, barcode = ?, selling_price = ?, min_stock_level = ?,
        category = ?, manufacturer = ?, prescription_required = ?
    WHERE id = ?
    """, (
        merged_dosage_form,
        merged_barcode,
        merged_price,
        merged_min_stock,
        merged_category,
        merged_manufacturer,
        merged_prescription_required,
        keeper_id
    ))

    for dup in duplicates:
        dup_id = dup["id"]

        cursor.execute("UPDATE batches SET product_id = ? WHERE product_id = ?", (keeper_id, dup_id))
        cursor.execute("UPDATE prescriptions SET product_id = ? WHERE product_id = ?", (keeper_id, dup_id))
        cursor.execute("UPDATE sale_items SET product_id = ? WHERE product_id = ?", (keeper_id, dup_id))
        cursor.execute("DELETE FROM products WHERE id = ?", (dup_id,))

    print(f"Merged duplicates for {name} into product id {keeper_id}")

conn.commit()
conn.close()
print("Duplicate product cleanup completed.")
