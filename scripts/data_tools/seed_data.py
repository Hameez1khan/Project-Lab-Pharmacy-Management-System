from pathlib import Path
import sys
import random

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import initialize_database, insert_product, insert_batch, get_connection

initialize_database()

products = [
    {"name": "Paracetamol", "category": "Pain Relief", "price": 450, "min_stock": 12, "dosage_form": "Tablet"},
    {"name": "Brufen", "category": "Pain Relief", "price": 850, "min_stock": 10, "dosage_form": "Tablet"},
    {"name": "Calpol", "category": "Children", "price": 780, "min_stock": 8, "dosage_form": "Syrup"},
    {"name": "Amoxicillin", "category": "Antibiotic", "price": 1200, "min_stock": 10, "dosage_form": "Capsule"},
    {"name": "Cetrizine", "category": "Allergy", "price": 390, "min_stock": 10, "dosage_form": "Tablet"},
    {"name": "Augmentin", "category": "Antibiotic", "price": 2450, "min_stock": 6, "dosage_form": "Tablet"},
    {"name": "Panadol", "category": "Pain Relief", "price": 620, "min_stock": 14, "dosage_form": "Tablet"},
    {"name": "ORS Sachet", "category": "Hydration", "price": 180, "min_stock": 20, "dosage_form": "Sachet"},
    {"name": "Vitamin C", "category": "Supplement", "price": 990, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Loratadine", "category": "Allergy", "price": 540, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Azithromycin", "category": "Antibiotic", "price": 1650, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Metronidazole", "category": "Antibiotic", "price": 720, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Ibuprofen", "category": "Pain Relief", "price": 610, "min_stock": 10, "dosage_form": "Tablet"},
    {"name": "Diclofenac", "category": "Pain Relief", "price": 890, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Omeprazole", "category": "Gastro", "price": 760, "min_stock": 8, "dosage_form": "Capsule"},
    {"name": "Pantoprazole", "category": "Gastro", "price": 950, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Domperidone", "category": "Gastro", "price": 580, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Zinc Tablets", "category": "Supplement", "price": 430, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Multivitamin", "category": "Supplement", "price": 1350, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Folic Acid", "category": "Supplement", "price": 320, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Cetirizine Syrup", "category": "Allergy", "price": 470, "min_stock": 8, "dosage_form": "Syrup"},
    {"name": "Chlorpheniramine", "category": "Allergy", "price": 360, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Salbutamol", "category": "Respiratory", "price": 1180, "min_stock": 8, "dosage_form": "Inhaler"},
    {"name": "Ambroxol Syrup", "category": "Respiratory", "price": 640, "min_stock": 8, "dosage_form": "Syrup"},
    {"name": "Cough Syrup", "category": "Respiratory", "price": 710, "min_stock": 8, "dosage_form": "Syrup"},
    {"name": "Insulin Regular", "category": "Diabetes", "price": 4200, "min_stock": 6, "dosage_form": "Injection"},
    {"name": "Metformin", "category": "Diabetes", "price": 860, "min_stock": 10, "dosage_form": "Tablet"},
    {"name": "Glibenclamide", "category": "Diabetes", "price": 540, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Amlodipine", "category": "Cardiac", "price": 920, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Losartan", "category": "Cardiac", "price": 1100, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Atenolol", "category": "Cardiac", "price": 780, "min_stock": 8, "dosage_form": "Tablet"},
    {"name": "Hydrocortisone Cream", "category": "Dermatology", "price": 680, "min_stock": 6, "dosage_form": "Cream"},
    {"name": "Clotrimazole Cream", "category": "Dermatology", "price": 520, "min_stock": 6, "dosage_form": "Cream"},
    {"name": "Gentamicin Cream", "category": "Dermatology", "price": 740, "min_stock": 6, "dosage_form": "Cream"},
    {"name": "Eye Drops", "category": "Ophthalmic", "price": 890, "min_stock": 6, "dosage_form": "Drops"},
    {"name": "Ear Drops", "category": "ENT", "price": 640, "min_stock": 6, "dosage_form": "Drops"},
    {"name": "Nasal Spray", "category": "ENT", "price": 980, "min_stock": 6, "dosage_form": "Spray"},
    {"name": "Pregnancy Test Kit", "category": "Diagnostic", "price": 350, "min_stock": 10, "dosage_form": "Kit"},
    {"name": "Blood Glucose Strips", "category": "Diagnostic", "price": 2100, "min_stock": 10, "dosage_form": "Strips"},
    {"name": "Digital Thermometer", "category": "Equipment", "price": 1850, "min_stock": 4, "dosage_form": "Device"},
]


def generate_barcode():
    return str(random.randint(100000000000, 999999999999))


def get_product_id_by_name(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?)", (name,))
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def batch_exists(batch_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM batches WHERE batch_number = ?", (batch_number,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def seed_products():
    for product in products:
        existing_id = get_product_id_by_name(product["name"])
        if existing_id:
            print(f"Skipped existing product: {product['name']}")
            continue

        try:
            insert_product(
                name=product["name"],
                dosage_form=product["dosage_form"],
                barcode=generate_barcode(),
                price=product["price"],
                min_stock=product["min_stock"],
                category=product["category"],
                manufacturer="Sample Pharma"
            )
            print(f"Inserted product: {product['name']}")
        except Exception as error:
            print(f"Skipped product {product['name']}: {error}")


def seed_batches():
    for index, product in enumerate(products, start=1):
        product_id = get_product_id_by_name(product["name"])
        if not product_id:
            continue

        batch_1 = f"B{index:03d}-A"
        batch_2 = f"B{index:03d}-B"

        if not batch_exists(batch_1):
            try:
                insert_batch(product_id, batch_1, "2026-06-15", 4 + (index % 4))
                print(f"Inserted batch {batch_1} for {product['name']}")
            except Exception as error:
                print(f"Skipped batch {batch_1}: {error}")

        if not batch_exists(batch_2):
            try:
                insert_batch(product_id, batch_2, "2026-10-20", 6 + (index % 5))
                print(f"Inserted batch {batch_2} for {product['name']}")
            except Exception as error:
                print(f"Skipped batch {batch_2}: {error}")

        if product["name"] == "Panadol":
            special_batch = "PAN-LOW-001"
            if not batch_exists(special_batch):
                try:
                    insert_batch(product_id, special_batch, "2026-05-10", 2)
                    print(f"Inserted low-stock FEFO batch for {product['name']}")
                except Exception as error:
                    print(f"Skipped special batch {special_batch}: {error}")

        if product["name"] == "Loratadine":
            special_batch = "LOR-EXP-001"
            if not batch_exists(special_batch):
                try:
                    insert_batch(product_id, special_batch, "2026-05-02", 3)
                    print(f"Inserted near-expiry batch for {product['name']}")
                except Exception as error:
                    print(f"Skipped special batch {special_batch}: {error}")

        if product["name"] == "Vitamin C":
            special_batch = "VTC-OLD-001"
            if not batch_exists(special_batch):
                try:
                    insert_batch(product_id, special_batch, "2025-01-15", 5)
                    print(f"Inserted expired batch for {product['name']}")
                except Exception as error:
                    print(f"Skipped special batch {special_batch}: {error}")


if __name__ == "__main__":
    seed_products()
    seed_batches()
