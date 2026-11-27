"""Build a deterministic, relationally consistent demonstration pharmacy database.

The generator creates a separate, reproducible thesis-project database selected
with ``KHALIS_DAWA_DB_PATH`` and never overwrites the normal database by default.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MEDICINES = [
    ("Paracetamol", "Analgesics", "Tablet", ("500 mg", "650 mg"), False, 420),
    ("Ibuprofen", "Analgesics", "Tablet", ("200 mg", "400 mg"), False, 610),
    ("Naproxen", "Analgesics", "Tablet", ("250 mg", "500 mg"), True, 920),
    ("Diclofenac", "Analgesics", "Tablet", ("25 mg", "50 mg"), True, 880),
    ("Aspirin", "Cardiovascular", "Tablet", ("75 mg", "100 mg"), False, 360),
    ("Amoxicillin", "Antibiotics", "Capsule", ("250 mg", "500 mg"), True, 1250),
    ("Co-amoxiclav", "Antibiotics", "Tablet", ("375 mg", "625 mg"), True, 2450),
    ("Azithromycin", "Antibiotics", "Tablet", ("250 mg", "500 mg"), True, 1720),
    ("Clarithromycin", "Antibiotics", "Tablet", ("250 mg", "500 mg"), True, 1980),
    ("Doxycycline", "Antibiotics", "Capsule", ("50 mg", "100 mg"), True, 1340),
    ("Cephalexin", "Antibiotics", "Capsule", ("250 mg", "500 mg"), True, 1410),
    ("Ciprofloxacin", "Antibiotics", "Tablet", ("250 mg", "500 mg"), True, 1530),
    ("Cetirizine", "Antihistamines", "Tablet", ("5 mg", "10 mg"), False, 390),
    ("Loratadine", "Antihistamines", "Tablet", ("5 mg", "10 mg"), False, 540),
    ("Fexofenadine", "Antihistamines", "Tablet", ("120 mg", "180 mg"), False, 980),
    ("Chlorpheniramine", "Antihistamines", "Tablet", ("2 mg", "4 mg"), False, 350),
    ("Amlodipine", "Cardiovascular", "Tablet", ("5 mg", "10 mg"), True, 920),
    ("Losartan", "Cardiovascular", "Tablet", ("25 mg", "50 mg"), True, 1110),
    ("Atenolol", "Cardiovascular", "Tablet", ("25 mg", "50 mg"), True, 780),
    ("Bisoprolol", "Cardiovascular", "Tablet", ("2.5 mg", "5 mg"), True, 1160),
    ("Lisinopril", "Cardiovascular", "Tablet", ("5 mg", "10 mg"), True, 1080),
    ("Metformin", "Diabetes", "Tablet", ("500 mg", "850 mg"), True, 860),
    ("Gliclazide", "Diabetes", "Tablet", ("40 mg", "80 mg"), True, 970),
    ("Sitagliptin", "Diabetes", "Tablet", ("50 mg", "100 mg"), True, 2980),
    ("Insulin Regular", "Diabetes", "Injection", ("100 IU/mL",), True, 4250),
    ("Omeprazole", "Gastrointestinal", "Capsule", ("20 mg", "40 mg"), False, 760),
    ("Pantoprazole", "Gastrointestinal", "Tablet", ("20 mg", "40 mg"), False, 950),
    ("Famotidine", "Gastrointestinal", "Tablet", ("20 mg", "40 mg"), False, 720),
    ("Domperidone", "Gastrointestinal", "Tablet", ("5 mg", "10 mg"), True, 580),
    ("Loperamide", "Gastrointestinal", "Capsule", ("2 mg",), False, 490),
    ("Salbutamol", "Respiratory", "Inhaler", ("100 mcg",), True, 1180),
    ("Budesonide", "Respiratory", "Inhaler", ("100 mcg", "200 mcg"), True, 2350),
    ("Montelukast", "Respiratory", "Tablet", ("5 mg", "10 mg"), True, 1470),
    ("Ambroxol", "Respiratory", "Syrup", ("15 mg/5 mL", "30 mg/5 mL"), False, 640),
    ("Dextromethorphan", "Respiratory", "Syrup", ("10 mg/5 mL",), False, 710),
    ("Hydrocortisone", "Dermatology", "Cream", ("1%",), False, 680),
    ("Clotrimazole", "Dermatology", "Cream", ("1%",), False, 520),
    ("Mupirocin", "Dermatology", "Ointment", ("2%",), True, 1150),
    ("Calamine", "Dermatology", "Lotion", ("15%",), False, 460),
    ("Zinc Oxide", "Dermatology", "Cream", ("10%", "20%"), False, 570),
    ("Vitamin C", "Vitamins & Supplements", "Tablet", ("500 mg", "1000 mg"), False, 990),
    ("Vitamin D3", "Vitamins & Supplements", "Capsule", ("1000 IU", "2000 IU"), False, 1120),
    ("Folic Acid", "Vitamins & Supplements", "Tablet", ("400 mcg", "5 mg"), False, 320),
    ("Iron", "Vitamins & Supplements", "Tablet", ("65 mg",), False, 690),
    ("Calcium", "Vitamins & Supplements", "Tablet", ("500 mg", "600 mg"), False, 820),
    ("Oral Rehydration Salts", "Paediatric & Hydration", "Sachet", ("20.5 g",), False, 180),
    ("Paracetamol Paediatric", "Paediatric & Hydration", "Syrup", ("120 mg/5 mL",), False, 780),
    ("Ibuprofen Paediatric", "Paediatric & Hydration", "Suspension", ("100 mg/5 mL",), False, 840),
    ("Povidone Iodine", "First Aid", "Solution", ("10%",), False, 620),
    ("Chlorhexidine", "First Aid", "Solution", ("0.5%",), False, 580),
    ("Adhesive Bandage", "First Aid", "Dressing", ("Standard",), False, 240),
    ("Sterile Gauze", "First Aid", "Dressing", ("10 x 10 cm",), False, 280),
    ("Lubricating Eye Drops", "Ophthalmic", "Drops", ("0.5%",), False, 890),
    ("Timolol Eye Drops", "Ophthalmic", "Drops", ("0.5%",), True, 1210),
    ("Sodium Chloride Nasal Spray", "ENT", "Spray", ("0.65%",), False, 780),
    ("Xylometazoline Nasal Drops", "ENT", "Drops", ("0.1%",), False, 650),
]

MANUFACTURERS = [
    "Northstar Laboratories", "Danube Health", "Crescent Pharma", "Atlas Remedies",
    "Greenfield Therapeutics", "Medica Nova", "Helix Healthcare", "Aurora Life Sciences",
    "Caspian Pharmaceuticals", "Horizon Generics", "Riverstone Pharma", "Central Medica",
]
PAYMENTS = ("Cash", "Card", "Mobile wallet")
FIRST_NAMES = ("Amina", "Omar", "Sara", "Yusuf", "Mariam", "Adam", "Lina", "Karim", "Nora", "Tariq")
LAST_NAMES = ("Khan", "Hassan", "Farooq", "Nagy", "Kovacs", "Szabo", "Ahmed", "Rahman", "Farkas", "Molnar")


def ean13(number):
    body = f"{number:012d}"[-12:]
    check = (10 - sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(body)) % 10) % 10
    return body + str(check)


def date_between(rng, start, end):
    return start + timedelta(days=rng.randint(0, max(0, (end - start).days)))


def dt_text(value):
    return value.strftime("%Y-%m-%d %H:%M")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate an isolated Khalis Dawa demonstration database.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "database" / "demo_pharmacy.db")
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--products", type=int, default=92)
    parser.add_argument("--sales", type=int, default=15000)
    parser.add_argument("--audits", type=int, default=50000)
    parser.add_argument("--months", type=int, default=15)
    parser.add_argument("--force", action="store_true", help="Replace an existing demonstration database.")
    return parser.parse_args()


def build_products(rng, count):
    catalogue = [
        (generic, category, form, strength, rx, base_price)
        for generic, category, form, strengths, rx, base_price in MEDICINES
        for strength in strengths
    ]
    if not 1 <= count <= len(catalogue):
        raise ValueError(
            f"Products must be between 1 and {len(catalogue)} so each medicine "
            "and strength remains a single product record."
        )
    rows = []
    for index, (generic, category, form, strength, rx, base_price) in enumerate(
        catalogue[:count]
    ):
        manufacturer = MANUFACTURERS[(index * 7) % len(MANUFACTURERS)]
        name = f"{generic} {strength} {form}"
        price_factor = 0.88 + ((index * 17) % 31) / 100
        price = round(base_price * price_factor / 10) * 10
        purchase_cost = round(price * rng.uniform(0.58, 0.72), 2)
        rows.append((
            name, form, ean13(590000000000 + index), price, purchase_cost,
            rng.randint(8, 30), category, manufacturer, int(rx),
        ))
    return rows


def generate(args):
    output = args.output.expanduser().resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite {output}. Use --force for a demonstration database.")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    os.environ["KHALIS_DAWA_DB_PATH"] = str(output)
    from database.db import get_connection, hash_password, initialize_database
    from database.inventory_audit import operator

    operator.set(("Data Setup", "system"))
    initialize_database()
    rng = random.Random(args.seed)
    now = datetime.now().replace(second=0, microsecond=0)
    history_start = now - timedelta(days=max(30, args.months * 30))
    conn = get_connection("Thesis project dataset generation")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM users")
        users = [
            ("admin", hash_password("1234"), "admin"),
            ("nora", hash_password("Pharmacy2026!"), "pharmacist"),
            ("adam", hash_password("Pharmacy2026!"), "pharmacist"),
            ("lina", hash_password("Pharmacy2026!"), "pharmacist"),
            ("karim", hash_password("Pharmacy2026!"), "pharmacist"),
        ]
        conn.executemany("INSERT INTO users(username,password,role) VALUES(?,?,?)", users)
        user_ids = [row["id"] for row in conn.execute("SELECT id FROM users WHERE role='pharmacist'")]
        usernames = [row[0] for row in users]

        supplier_names = [
            f"{region} {kind}"
            for region in ("Danube", "Central", "Crescent", "Atlas", "Aurora", "Horizon", "Caspian", "Greenfield")
            for kind in ("Pharma Distribution", "Medical Wholesale", "Healthcare Supply", "Medicines Depot")
        ]
        for index, name in enumerate(supplier_names, 1):
            conn.execute("""
                INSERT INTO suppliers(name,contact_person,phone,email,address,created_at,lead_time_days)
                VALUES(?,?,?,?,?,?,?)
            """, (
                name, f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[index % len(LAST_NAMES)]}",
                f"+36 30 555 {index:04d}", f"orders{index}@khalisdawa.example",
                f"{10 + index} Distribution Park, Budapest", dt_text(history_start), rng.randint(2, 14),
            ))

        products = build_products(rng, args.products)
        conn.executemany("""
            INSERT INTO products(name,dosage_form,barcode,selling_price,purchase_cost,min_stock_level,category,manufacturer,prescription_required)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, products)
        product_rows = [dict(row) for row in conn.execute("SELECT * FROM products ORDER BY id")]

        order_statuses = (["fully_received"] * 55 + ["partially_received"] * 30 +
                          ["ordered"] * 45 + ["pending"] * 20 + ["draft"] * 15 + ["cancelled"] * 15)
        rng.shuffle(order_statuses)
        for order_index, status in enumerate(order_statuses, 1):
            order_date = date_between(rng, history_start, now - timedelta(days=8))
            expected = order_date + timedelta(days=rng.randint(3, 14))
            supplier_id = 1 + (order_index * 7) % len(supplier_names)
            order_number = f"PO-{order_date:%Y%m%d}-{order_index:04d}"
            cur = conn.execute("""
                INSERT INTO purchase_orders(order_number,supplier_id,order_date,expected_date,status,notes,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (order_number, supplier_id, order_date.date().isoformat(), expected.date().isoformat(), status,
                  "Routine replenishment order", "admin", dt_text(order_date), dt_text(order_date)))
            order_id = cur.lastrowid
            for product in rng.sample(product_rows, 8):
                ordered = rng.randrange(40, 181, 10)
                received = ordered if status == "fully_received" else (ordered // 2 if status == "partially_received" else 0)
                conn.execute("""
                    INSERT INTO purchase_order_items(purchase_order_id,product_id,ordered_quantity,received_quantity,unit_cost)
                    VALUES(?,?,?,?,?)
                """, (order_id, product["id"], ordered, received, product["purchase_cost"]))

        # Four purchase-backed batches per product, spread over the operating period.
        batches_by_product = defaultdict(list)
        batch_specs = []
        for product in product_rows:
            for slot in range(4):
                received = history_start + timedelta(days=slot * max(45, (now - history_start).days // 4) + rng.randint(0, 28))
                received = min(received, now - timedelta(days=10))
                expiry = received + timedelta(days=rng.randint(240, 900))
                # Keep a controlled set of expired and near-expiry records for reports.
                if product["id"] % 53 == 0 and slot == 0:
                    expiry = now - timedelta(days=rng.randint(5, 90))
                elif product["id"] % 37 == 0 and slot == 1:
                    expiry = now + timedelta(days=rng.randint(5, 45))
                quantity = rng.randint(260, 520)
                cost = float(product["purchase_cost"])
                batch_specs.append({
                    "product": product, "received": received, "expiry": expiry,
                    "initial": quantity, "remaining": quantity, "cost": cost,
                    "batch_number": f"{product['id']:04d}-{received:%y%m}-{slot + 1}",
                })

        receipt_groups = [batch_specs[i:i + 12] for i in range(0, len(batch_specs), 12)]
        for receipt_index, group in enumerate(receipt_groups, 1):
            received = max(spec["received"] for spec in group)
            supplier_id = 1 + (receipt_index * 5) % len(supplier_names)
            receipt = conn.execute("""
                INSERT INTO purchase_receipts(supplier_id,reference_number,received_date,notes,received_by,created_at,purchase_order_id)
                VALUES(?,?,?,?,?,?,NULL)
            """, (supplier_id, f"DN-{received:%Y%m}-{receipt_index:05d}", received.date().isoformat(),
                  "Supplier delivery", "admin", dt_text(received)))
            for spec in group:
                batch = conn.execute("""
                    INSERT INTO batches(product_id,batch_number,expiry_date,quantity,purchase_unit_cost,total_purchase_cost,discount_percent,discount_applied_date)
                    VALUES(?,?,?,?,?,?,0,NULL)
                """, (spec["product"]["id"], spec["batch_number"], spec["expiry"].date().isoformat(),
                      spec["initial"], spec["cost"], round(spec["initial"] * spec["cost"], 2)))
                spec["id"] = batch.lastrowid
                batches_by_product[spec["product"]["id"]].append(spec)
                conn.execute("""
                    INSERT INTO purchase_receipt_items(receipt_id,product_id,batch_id,batch_number,expiry_date,quantity,unit_cost,total_cost,purchase_order_item_id)
                    VALUES(?,?,?,?,?,?,?,?,NULL)
                """, (receipt.lastrowid, spec["product"]["id"], spec["id"], spec["batch_number"],
                      spec["expiry"].date().isoformat(), spec["initial"], spec["cost"],
                      round(spec["initial"] * spec["cost"], 2)))

        # Sales are generated chronologically and allocated FEFO from stock that
        # had already been received and was not expired on the sale date.
        sale_dates = sorted(
            date_between(rng, history_start + timedelta(days=30), now - timedelta(days=4))
            .replace(hour=rng.randint(8, 20), minute=rng.randint(0, 59))
            for _ in range(args.sales)
        )
        sale_items_for_returns = []
        prescription_count = 0
        product_weights = [max(1, 80 - (i % 80)) for i in range(len(product_rows))]

        for sale_index, sale_date in enumerate(sale_dates, 1):
            target_lines = rng.choices((1, 2, 3, 4, 5), weights=(18, 30, 28, 17, 7), k=1)[0]
            chosen = set()
            prepared = []
            for _ in range(target_lines * 5):
                if len(prepared) >= target_lines:
                    break
                product = rng.choices(product_rows, weights=product_weights, k=1)[0]
                if product["id"] in chosen:
                    continue
                eligible = sorted(
                    (b for b in batches_by_product[product["id"]]
                     if b["received"] <= sale_date and b["expiry"] >= sale_date and b["remaining"] > 0),
                    key=lambda b: (b["expiry"], b["id"]),
                )
                wanted = rng.choices((1, 2, 3), weights=(70, 24, 6), k=1)[0]
                if sum(b["remaining"] for b in eligible) < wanted:
                    continue
                quantity_left = wanted
                allocations = []
                for batch in eligible:
                    take = min(quantity_left, batch["remaining"])
                    if take:
                        allocations.append((batch, take))
                        quantity_left -= take
                    if not quantity_left:
                        break
                price = float(product["selling_price"])
                prepared.append((product, wanted, price, allocations))
                chosen.add(product["id"])
            if not prepared:
                continue

            total = round(sum(quantity * price for _, quantity, price, _ in prepared), 2)
            sale = conn.execute("""
                INSERT INTO sales(sale_datetime,total_amount,cashier_id,payment_method) VALUES(?,?,?,?)
            """, (dt_text(sale_date), total, rng.choice(user_ids), rng.choices(PAYMENTS, (46, 43, 11), k=1)[0]))
            for product, quantity, price, allocations in prepared:
                item = conn.execute("""
                    INSERT INTO sale_items(sale_id,product_id,product_name,quantity,unit_price,subtotal)
                    VALUES(?,?,?,?,?,?)
                """, (sale.lastrowid, product["id"], product["name"], quantity, price, round(quantity * price, 2)))
                for batch, allocated in allocations:
                    batch["remaining"] -= allocated
                    conn.execute("""
                        INSERT INTO sale_batch_allocations(sale_item_id,batch_id,batch_number,quantity,expiry_date)
                        VALUES(?,?,?,?,?)
                    """, (item.lastrowid, batch["id"], batch["batch_number"], allocated, batch["expiry"].date().isoformat()))
                sale_items_for_returns.append((item.lastrowid, sale.lastrowid, product, quantity, price, sale_date, allocations))
                if product["prescription_required"] and prescription_count < 3200 and rng.random() < .28:
                    patient = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                    conn.execute("""
                        INSERT INTO prescriptions(sale_id,customer_ssn,customer_name,product_id,medicine_name,amount,created_at)
                        VALUES(?,?,?,?,?,?,?)
                    """, (sale.lastrowid, f"{700000000 + prescription_count:09d}", patient,
                          product["id"], product["name"], quantity, dt_text(sale_date)))
                    prescription_count += 1

            if sale_index % 1000 == 0:
                print(f"Generated {sale_index:,} of {args.sales:,} sales...", flush=True)

        # Apply final stock balances after all FEFO allocations.
        for spec in batch_specs:
            conn.execute("UPDATE batches SET quantity=?, total_purchase_cost=? WHERE id=?",
                         (spec["remaining"], round(spec["remaining"] * spec["cost"], 2), spec["id"]))

        # Returns are sampled from genuine sale items and restore the exact batch.
        rng.shuffle(sale_items_for_returns)
        return_target = min(900, max(1, args.sales // 18), len(sale_items_for_returns))
        for return_index, entry in enumerate(sale_items_for_returns[:return_target], 1):
            sale_item_id, sale_id, product, sold_quantity, price, sale_date, allocations = entry
            return_quantity = 1 if sold_quantity == 1 else rng.randint(1, sold_quantity)
            return_date = min(now, sale_date + timedelta(days=rng.randint(0, 2), hours=rng.randint(1, 8)))
            employee = rng.choice(usernames[1:])
            returned = conn.execute("""
                INSERT INTO returns(sale_id,processed_by_username,processed_by_role,total_amount,return_datetime)
                VALUES(?,?,?,?,?)
            """, (sale_id, employee, "pharmacist", round(return_quantity * price, 2), dt_text(return_date)))
            return_item = conn.execute("""
                INSERT INTO return_items(return_id,sale_item_id,product_id,product_name,quantity,unit_price,subtotal)
                VALUES(?,?,?,?,?,?,?)
            """, (returned.lastrowid, sale_item_id, product["id"], product["name"], return_quantity,
                  price, round(return_quantity * price, 2)))
            remaining_return = return_quantity
            for batch, sold_from_batch in allocations:
                take = min(remaining_return, sold_from_batch)
                if not take:
                    continue
                allocation_id = conn.execute(
                    "SELECT id FROM sale_batch_allocations WHERE sale_item_id=? AND batch_id=?",
                    (sale_item_id, batch["id"]),
                ).fetchone()["id"]
                conn.execute("""
                    INSERT INTO return_batch_allocations(return_item_id,sale_batch_allocation_id,batch_id,batch_number,quantity,expiry_date)
                    VALUES(?,?,?,?,?,?)
                """, (return_item.lastrowid, allocation_id, batch["id"], batch["batch_number"], take,
                      batch["expiry"].date().isoformat()))
                conn.execute("UPDATE batches SET quantity=quantity+? WHERE id=?", (take, batch["id"]))
                remaining_return -= take
                if not remaining_return:
                    break

        # Coherent synthetic audit trail, always marked as demonstration data.
        audit_events = []
        for product in product_rows:
            audit_events.append(("admin", "admin", f"Registered medicine {product['name']}", dt_text(history_start)))
        for sale_id, sale_datetime in conn.execute("SELECT id,sale_datetime FROM sales"):
            audit_events.append((rng.choice(usernames[1:]), "pharmacist", f"Completed sale KD-{sale_datetime[:10].replace('-', '')}-{sale_id:05d}", sale_datetime))
        for return_id, returned_at in conn.execute("SELECT id,return_datetime FROM returns"):
            audit_events.append((rng.choice(usernames[1:]), "pharmacist", f"Processed return RT-{returned_at[:10].replace('-', '')}-{return_id:05d}", returned_at))
        for order_number, created_at in conn.execute("SELECT order_number,created_at FROM purchase_orders"):
            audit_events.append(("admin", "admin", f"Created purchase order {order_number}", created_at))
        action_templates = (
            "Reviewed low-stock recommendations", "Reviewed expiry alerts", "Exported daily sales report",
            "Verified inventory count", "Reviewed supplier delivery history", "Created database backup",
            "Reviewed fast and slow movers", "Verified prescription dispensing record",
        )
        while len(audit_events) < args.audits:
            event_date = date_between(rng, history_start, now).replace(hour=rng.randint(7, 21), minute=rng.randint(0, 59))
            actor = rng.choice(usernames)
            role = "admin" if actor == "demo_admin" else "pharmacist"
            audit_events.append((actor, role, rng.choice(action_templates), dt_text(event_date)))
        audit_events.sort(key=lambda row: row[3])
        conn.executemany("INSERT INTO audit_logs(username,role,description,created_at) VALUES(?,?,?,?)", audit_events[:args.audits])

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    # Verification is intentionally performed after commit on the final file.
    checks = {
        "foreign_key_violations": len(conn.execute("PRAGMA foreign_key_check").fetchall()),
        "integrity": conn.execute("PRAGMA integrity_check").fetchone()[0],
        "negative_batches": conn.execute("SELECT COUNT(*) FROM batches WHERE quantity < 0").fetchone()[0],
        "sale_total_mismatches": conn.execute("""
            SELECT COUNT(*) FROM sales s
            WHERE ABS(s.total_amount - COALESCE((SELECT SUM(subtotal) FROM sale_items WHERE sale_id=s.id),0)) > .01
        """).fetchone()[0],
        "return_total_mismatches": conn.execute("""
            SELECT COUNT(*) FROM returns r
            WHERE ABS(r.total_amount - COALESCE((SELECT SUM(subtotal) FROM return_items WHERE return_id=r.id),0)) > .01
        """).fetchone()[0],
    }
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "products", "batches", "suppliers", "purchase_orders", "purchase_receipts",
            "sales", "sale_items", "prescriptions", "returns", "audit_logs", "users",
        )
    }
    conn.close()
    if checks != {
        "foreign_key_violations": 0,
        "integrity": "ok",
        "negative_batches": 0,
        "sale_total_mismatches": 0,
        "return_total_mismatches": 0,
    }:
        raise RuntimeError(f"Demonstration database verification failed: {checks}")
    summary = {
        "database": str(output),
        "dataset": "thesis-project",
        "seed": args.seed,
        "history_start": history_start.date().isoformat(),
        "history_end": now.date().isoformat(),
        "counts": counts,
        "checks": checks,
        "size_bytes": output.stat().st_size,
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    generate(parse_args())
