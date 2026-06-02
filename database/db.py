import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent / "pharmacy.db"
RETURN_WINDOW_DAYS = 3


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_customer_ssn(ssn):
    return "".join(char for char in (ssn or "").strip() if char.isdigit())


def is_valid_customer_ssn(ssn):
    return len(normalize_customer_ssn(ssn)) == 9


def format_receipt_number(record_id):
    return f"#{int(record_id):05d}"



def refresh_expiring_soon_discounts():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Activate discount for valid batches expiring within 30 days
    cursor.execute("""
        UPDATE batches
        SET
            discount_percent = 10,
            discount_applied_date = COALESCE(discount_applied_date, ?)
        WHERE quantity > 0
          AND date(expiry_date) >= date('now')
          AND date(expiry_date) <= date('now', '+30 days')
    """, (today,))

    # Remove discount from batches that are no longer valid or have no stock
    cursor.execute("""
        UPDATE batches
        SET
            discount_percent = 0,
            discount_applied_date = NULL
        WHERE quantity <= 0
           OR date(expiry_date) < date('now')
    """)

    conn.commit()
    conn.close()


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        role TEXT,
        description TEXT NOT NULL,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        dosage_form TEXT,
        barcode TEXT UNIQUE,
        selling_price REAL NOT NULL,
        min_stock_level INTEGER DEFAULT 0,
        category TEXT,
        manufacturer TEXT,
        prescription_required INTEGER DEFAULT 0
    )
    """)

    cursor.execute("PRAGMA table_info(products)")
    product_columns = [row["name"] for row in cursor.fetchall()]
    if "prescription_required" not in product_columns:
        cursor.execute("""
            ALTER TABLE products
            ADD COLUMN prescription_required INTEGER DEFAULT 0
        """)



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL UNIQUE,
        expiry_date TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        purchase_unit_cost REAL NOT NULL,
        total_purchase_cost REAL NOT NULL,
        discount_percent REAL DEFAULT 0,
        discount_applied_date TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    cursor.execute("PRAGMA table_info(batches)")
    batch_columns = [row["name"] for row in cursor.fetchall()]

    if "discount_percent" not in batch_columns:
        cursor.execute("""
            ALTER TABLE batches
            ADD COLUMN discount_percent REAL DEFAULT 0
        """)

    if "discount_applied_date" not in batch_columns:
        cursor.execute("""
            ALTER TABLE batches
            ADD COLUMN discount_applied_date TEXT
        """)



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        customer_ssn TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        amount INTEGER NOT NULL,
        created_at TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (sale_id) REFERENCES sales(id)
    )
    """)


    cursor.execute("PRAGMA table_info(prescriptions)")
    prescription_columns = [row["name"] for row in cursor.fetchall()]

    expected_prescription_columns = {
        "id",
        "sale_id",
        "customer_ssn",
        "customer_name",
        "product_id",
        "medicine_name",
        "amount",
        "created_at",
    }

    if set(prescription_columns) != expected_prescription_columns:
        cursor.execute("DROP TABLE IF EXISTS prescriptions")

        cursor.execute("""
        CREATE TABLE prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            customer_ssn TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (sale_id) REFERENCES sales(id)
        )
        """)





    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_datetime TEXT,
        total_amount REAL,
        cashier_id INTEGER,
        payment_method TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(sales)")
    sales_columns = [row["name"] for row in cursor.fetchall()]
    if "payment_method" not in sales_columns:
        cursor.execute("""
            ALTER TABLE sales
            ADD COLUMN payment_method TEXT
        """)



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        unit_price REAL,
        subtotal REAL
    )
    """)

    cursor.execute("PRAGMA table_info(sale_items)")
    sale_item_columns = [row["name"] for row in cursor.fetchall()]
    if "product_name" not in sale_item_columns:
        cursor.execute("""
            ALTER TABLE sale_items
            ADD COLUMN product_name TEXT
        """)



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sale_batch_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_item_id INTEGER,
        batch_id INTEGER,
        batch_number TEXT,
        quantity INTEGER,
        expiry_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        processed_by_username TEXT NOT NULL,
        processed_by_role TEXT,
        total_amount REAL NOT NULL,
        return_datetime TEXT,
        FOREIGN KEY (sale_id) REFERENCES sales(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id INTEGER NOT NULL,
        sale_item_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (return_id) REFERENCES returns(id),
        FOREIGN KEY (sale_item_id) REFERENCES sale_items(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS return_batch_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_item_id INTEGER NOT NULL,
        sale_batch_allocation_id INTEGER NOT NULL,
        batch_id INTEGER,
        batch_number TEXT,
        quantity INTEGER NOT NULL,
        expiry_date TEXT,
        FOREIGN KEY (return_item_id) REFERENCES return_items(id),
        FOREIGN KEY (sale_batch_allocation_id) REFERENCES sale_batch_allocations(id)
    )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', '1234', 'admin')
    """)



    conn.commit()
    conn.close()


def insert_product(name, dosage_form, barcode, price, min_stock=10, category=None, manufacturer=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO products
        (name, dosage_form, barcode, selling_price, min_stock_level, category, manufacturer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, dosage_form, barcode, price, min_stock, category, manufacturer))

    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, password, role
        FROM users
        WHERE username = ?
    """, (username.strip(),))
    user = cursor.fetchone()

    conn.close()

    if not user:
        return None

    if str(user["password"]).strip() != str(password).strip():
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }

def register_pharmacist(username, password):
    username = (username or "").strip()
    password = (password or "").strip()

    if not username or not password:
        return False, "Username and password are required."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE LOWER(username) = LOWER(?)
    """, (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return False, "This username already exists."

    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, 'pharmacist')
    """, (username, password))

    add_audit_log(
        username,
        "Created pharmacist account",
        role="pharmacist",
        conn=conn,
        cursor=cursor
    )

    conn.commit()
    conn.close()

    return True, "Registration has been completed."




def get_password_manageable_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username
        FROM users
        WHERE role IN ('admin', 'pharmacist')
        ORDER BY
            CASE WHEN role = 'admin' THEN 0 ELSE 1 END,
            LOWER(username)
    """)

    users = [row["username"] for row in cursor.fetchall()]
    conn.close()
    return users


def add_audit_log(username, description, role=None, conn=None, cursor=None):
    own_connection = conn is None or cursor is None

    if own_connection:
        conn = get_connection()
        cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (
            username,
            role,
            description,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        (username or "Unknown").strip(),
        (role or "").strip() or None,
        description.strip(),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))

    if own_connection:
        conn.commit()
        conn.close()


def get_audit_log_rows(search_text=""):
    conn = get_connection()
    cursor = conn.cursor()

    normalized = f"%{search_text.strip().lower()}%"

    cursor.execute("""
        SELECT
            id,
            username,
            role,
            description,
            created_at
        FROM audit_logs
        WHERE LOWER(username) LIKE ?
           OR LOWER(COALESCE(role, '')) LIKE ?
           OR LOWER(description) LIKE ?
        ORDER BY id DESC
    """, (normalized, normalized, normalized))

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "username": row["username"],
            "role": row["role"] or "",
            "description": row["description"],
            "created_at": row["created_at"] or "",
        })

    conn.close()
    return rows


def get_product_by_name(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE LOWER(name) = LOWER(?)
    """, (name.strip(),))

    row = cursor.fetchone()
    conn.close()
    return row


def get_product_by_barcode(barcode):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, selling_price
        FROM products
        WHERE barcode = ?
    """, (barcode,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row["id"], row["name"], row["selling_price"]


def insert_batch(product_id, batch_number, expiry_date, quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT selling_price FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    if not product:
        conn.close()
        return False

    unit_cost = float(product["selling_price"])
    total_cost = unit_cost * int(quantity)

    cursor.execute("""
        INSERT INTO batches (
            product_id,
            batch_number,
            expiry_date,
            quantity,
            purchase_unit_cost,
            total_purchase_cost
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        batch_number.strip(),
        expiry_date.strip(),
        int(quantity),
        unit_cost,
        total_cost
    ))

    conn.commit()
    conn.close()
    return True


def add_batch_record(product_name, batch_number, quantity, expiry_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, selling_price
        FROM products
        WHERE LOWER(name) = LOWER(?)
    """, (product_name.strip(),))
    product = cursor.fetchone()

    if not product:
        conn.close()
        return False, "Product does not exist in the products table."

    cursor.execute("""
        SELECT id
        FROM batches
        WHERE LOWER(batch_number) = LOWER(?)
    """, (batch_number.strip(),))
    existing_batch = cursor.fetchone()

    if existing_batch:
        conn.close()
        return False, "Batch number already exists."

    unit_cost = float(product["selling_price"])
    total_cost = unit_cost * int(quantity)

    cursor.execute("""
        INSERT INTO batches (
            product_id,
            batch_number,
            expiry_date,
            quantity,
            purchase_unit_cost,
            total_purchase_cost
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product["id"],
        batch_number.strip(),
        expiry_date.strip(),
        int(quantity),
        unit_cost,
        total_cost
    ))

    conn.commit()
    conn.close()
    return True, "Batch added successfully."


def update_batch_record(batch_id, quantity, expiry_date, price, min_stock_level):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_id
        FROM batches
        WHERE id = ?
    """, (batch_id,))
    batch = cursor.fetchone()

    if not batch:
        conn.close()
        return False

    cursor.execute("""
        UPDATE batches
        SET quantity = ?, expiry_date = ?
        WHERE id = ?
    """, (int(quantity), expiry_date.strip(), batch_id))

    cursor.execute("""
        UPDATE products
        SET selling_price = ?, min_stock_level = ?
        WHERE id = ?
    """, (
        float(price),
        int(min_stock_level),
        batch["product_id"]
    ))

    conn.commit()
    conn.close()
    return True


def delete_batch_record(batch_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM batches WHERE id = ?", (batch_id,))

    conn.commit()
    conn.close()


def get_categories():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL AND TRIM(category) != ''
        ORDER BY category
    """)

    rows = [row["category"] for row in cursor.fetchall()]
    conn.close()
    return rows

def get_product_rows(search_text="", category="All Categories"):
    conn = get_connection()
    cursor = conn.cursor()

    search_value = f"%{search_text.strip().lower()}%"

    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.dosage_form,
            p.barcode,
            p.selling_price,
            p.min_stock_level,
            p.category,
            p.prescription_required,

            COALESCE(SUM(
                CASE
                    WHEN date(b.expiry_date) >= date('now') THEN b.quantity
                    ELSE 0
                END
            ), 0) AS available_stock
        FROM products p
        LEFT JOIN batches b ON b.product_id = p.id
        WHERE LOWER(p.name) LIKE ?
          AND (? = 'All Categories' OR p.category = ?)
        GROUP BY
            p.id,
            p.name,
            p.dosage_form,
            p.barcode,
            p.selling_price,
            p.min_stock_level,
            p.category,
            p.prescription_required

        ORDER BY LOWER(p.name)
    """, (search_value, category, category))

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "name": row["name"],
            "dosage_form": row["dosage_form"] or "",
            "barcode": row["barcode"] or "",
            "selling_price": row["selling_price"],
            "min_stock_level": row["min_stock_level"],
            "category": row["category"] or "General",
            "available_stock": row["available_stock"],
            "prescription_required": bool(row["prescription_required"]),

        })

    conn.close()
    return rows


def add_product_record(
    name,
    dosage_form,
    barcode,
    selling_price,
    min_stock_level,
    category,
    manufacturer=None,
    prescription_required=False
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM products
        WHERE LOWER(name) = LOWER(?)
    """, (name.strip(),))
    existing_name = cursor.fetchone()

    if existing_name:
        conn.close()
        return False, "A product with this name already exists."

    if barcode.strip():
        cursor.execute("""
            SELECT id
            FROM products
            WHERE barcode = ?
        """, (barcode.strip(),))
        existing_barcode = cursor.fetchone()

        if existing_barcode:
            conn.close()
            return False, "This barcode already exists."

    cursor.execute("""
        INSERT INTO products (
            name,
            dosage_form,
            barcode,
            selling_price,
            min_stock_level,
            category,
            manufacturer,
            prescription_required
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name.strip(),
        dosage_form.strip(),
        barcode.strip() or None,
        float(selling_price),
        int(min_stock_level),
        category.strip() or "General",
        manufacturer,
        1 if prescription_required else 0
    ))


    conn.commit()
    conn.close()
    return True, "Product added successfully."


def update_product_record(
    product_id,
    name,
    dosage_form,
    barcode,
    selling_price,
    min_stock_level,
    category,
    prescription_required
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM products
        WHERE LOWER(name) = LOWER(?) AND id != ?
    """, (name.strip(), product_id))
    existing_name = cursor.fetchone()

    if existing_name:
        conn.close()
        return False, "A product with this name already exists."

    if barcode.strip():
        cursor.execute("""
            SELECT id
            FROM products
            WHERE barcode = ? AND id != ?
        """, (barcode.strip(), product_id))
        existing_barcode = cursor.fetchone()

        if existing_barcode:
            conn.close()
            return False, "This barcode already exists."

    cursor.execute("""
        UPDATE products
        SET
            name = ?,
            dosage_form = ?,
            barcode = ?,
            selling_price = ?,
            min_stock_level = ?,
            category = ?,
            prescription_required = ?
        WHERE id = ?
    """, (
        name.strip(),
        dosage_form.strip(),
        barcode.strip() or None,
        float(selling_price),
        int(min_stock_level),
        category.strip() or "General",
        1 if prescription_required else 0,
        product_id
    ))


    conn.commit()
    conn.close()
    return True, "Product updated successfully."


def delete_product_record(product_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name
        FROM products
        WHERE id = ?
    """, (product_id,))
    product = cursor.fetchone()

    if not product:
        conn.close()
        return False, "Product not found."

    cursor.execute("""
        DELETE FROM batches
        WHERE product_id = ?
    """, (product_id,))

    cursor.execute("""
        DELETE FROM products
        WHERE id = ?
    """, (product_id,))

    conn.commit()
    conn.close()
    return True, "Product deleted successfully."


def get_available_stock(product_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_stock
        FROM batches
        WHERE product_id = ?
          AND quantity > 0
          AND date(expiry_date) >= date('now')
    """, (product_id,))

    row = cursor.fetchone()
    conn.close()
    return row["total_stock"] if row else 0


def get_products_for_pos(search_text="", category="All Categories"):
    refresh_expiring_soon_discounts()

    conn = get_connection()
    cursor = conn.cursor()

    normalized = search_text.strip().lower()
    search_value = f"%{normalized}%"

    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.category,
            p.selling_price,
            p.prescription_required,
            COALESCE(SUM(
                CASE
                    WHEN date(b.expiry_date) >= date('now') THEN b.quantity
                    ELSE 0
                END
            ), 0) AS available_stock,
            COALESCE(MAX(
                CASE
                    WHEN b.quantity > 0
                     AND date(b.expiry_date) >= date('now')
                     AND b.discount_percent > 0
                    THEN b.discount_percent
                    ELSE 0
                END
            ), 0) AS active_discount_percent
        FROM products p
        LEFT JOIN batches b ON b.product_id = p.id
        WHERE (
            LOWER(p.name) LIKE ?
            OR COALESCE(p.barcode, '') LIKE ?
        )
          AND (? = 'All Categories' OR p.category = ?)
        GROUP BY p.id, p.name, p.category, p.selling_price, p.prescription_required
        ORDER BY p.name ASC
    """, (search_value, search_value, category, category))

    products = []
    for row in cursor.fetchall():
        discount_percent = float(row["active_discount_percent"] or 0)
        original_price = float(row["selling_price"])
        discounted_price = original_price

        if discount_percent > 0:
            discounted_price = round(original_price * (1 - discount_percent / 100), 2)

        products.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"] or "General",
            "price": discounted_price,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "has_discount": discount_percent > 0,
            "available_stock": row["available_stock"],
            "prescription_required": bool(row["prescription_required"]),
        })

    conn.close()
    return products


def get_prescription_rows(search_text=""):
    conn = get_connection()
    cursor = conn.cursor()

    if search_text.strip():
        search_value = f"%{search_text.strip().lower()}%"
        cursor.execute("""
            SELECT
                id,
                customer_ssn,
                customer_name,
                medicine_name,
                amount,
                created_at
            FROM prescriptions
            WHERE LOWER(customer_ssn) LIKE ?
               OR LOWER(customer_name) LIKE ?
               OR LOWER(medicine_name) LIKE ?
            ORDER BY id DESC
        """, (search_value, search_value, search_value))
    else:
        cursor.execute("""
            SELECT
                id,
                customer_ssn,
                customer_name,
                medicine_name,
                amount,
                created_at
            FROM prescriptions
            ORDER BY id DESC
        """)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "customer_ssn": row["customer_ssn"],
            "customer_name": row["customer_name"],
            "medicine_name": row["medicine_name"],
            "amount": row["amount"],
            "created_at": row["created_at"] or "",
        })

    conn.close()
    return rows




def delete_prescription_record(prescription_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM prescriptions WHERE id = ?", (prescription_id,))

    conn.commit()
    conn.close()





def cart_requires_prescription(cart_items):
    conn = get_connection()
    cursor = conn.cursor()

    for item in cart_items:
        cursor.execute("""
            SELECT prescription_required
            FROM products
            WHERE id = ?
        """, (item["product_id"],))
        row = cursor.fetchone()

        if row and row["prescription_required"]:
            conn.close()
            return True

    conn.close()
    return False

def log_prescription_sale(sale_id, customer_ssn, customer_name, product_id, medicine_name, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO prescriptions (
            sale_id,
            customer_ssn,
            customer_name,
            product_id,
            medicine_name,
            amount,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        sale_id,
        normalize_customer_ssn(customer_ssn),
        customer_name.strip(),
        product_id,
        medicine_name,
        int(amount),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))

    conn.commit()
    conn.close()


def _build_sale_return_context(cursor, sale_id):
    cursor.execute("""
        SELECT
            id,
            sale_datetime,
            total_amount
        FROM sales
        WHERE id = ?
    """, (sale_id,))
    sale = cursor.fetchone()

    if not sale:
        raise ValueError("Sale not found.")

    sale_datetime = datetime.strptime(sale["sale_datetime"], "%Y-%m-%d %H:%M")
    return_deadline = sale_datetime + timedelta(days=RETURN_WINDOW_DAYS)
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            id,
            product_id,
            product_name,
            quantity,
            unit_price,
            subtotal
        FROM sale_items
        WHERE sale_id = ?
        ORDER BY id ASC
    """, (sale_id,))
    sale_items = cursor.fetchall()

    items = []

    for sale_item in sale_items:
        cursor.execute("""
            SELECT
                sba.id,
                sba.batch_id,
                sba.batch_number,
                sba.quantity AS sold_quantity,
                sba.expiry_date,
                COALESCE((
                    SELECT SUM(rba.quantity)
                    FROM return_batch_allocations rba
                    WHERE rba.sale_batch_allocation_id = sba.id
                ), 0) AS returned_quantity
            FROM sale_batch_allocations sba
            WHERE sba.sale_item_id = ?
            ORDER BY date(sba.expiry_date) ASC, sba.id ASC
        """, (sale_item["id"],))
        batch_rows = cursor.fetchall()

        returned_quantity = 0
        returnable_quantity = 0
        expired_blocked_quantity = 0
        batch_options = []

        for batch in batch_rows:
            sold_quantity = int(batch["sold_quantity"])
            returned_from_batch = int(batch["returned_quantity"] or 0)
            returned_quantity += returned_from_batch

            remaining_quantity = sold_quantity - returned_from_batch
            if remaining_quantity <= 0:
                continue

            if batch["expiry_date"] < today:
                expired_blocked_quantity += remaining_quantity
                continue

            returnable_quantity += remaining_quantity
            batch_options.append({
                "sale_batch_allocation_id": batch["id"],
                "batch_id": batch["batch_id"],
                "batch_number": batch["batch_number"],
                "expiry_date": batch["expiry_date"],
                "remaining_quantity": remaining_quantity,
            })

        items.append({
            "sale_item_id": sale_item["id"],
            "product_id": sale_item["product_id"],
            "product_name": sale_item["product_name"],
            "sold_quantity": int(sale_item["quantity"]),
            "returned_quantity": returned_quantity,
            "returnable_quantity": returnable_quantity,
            "expired_blocked_quantity": expired_blocked_quantity,
            "unit_price": float(sale_item["unit_price"]),
            "subtotal": float(sale_item["subtotal"]),
            "batch_options": batch_options,
        })

    return {
        "sale_id": sale["id"],
        "receipt_number": format_receipt_number(sale["id"]),
        "sale_datetime": sale["sale_datetime"],
        "return_deadline": return_deadline.strftime("%Y-%m-%d %H:%M"),
        "return_window_open": datetime.now() <= return_deadline,
        "items": items,
    }


def get_sale_return_candidates(sale_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        return _build_sale_return_context(cursor, sale_id)
    finally:
        conn.close()


def _restore_batch_quantity(cursor, product_id, batch_id, batch_number, expiry_date, quantity):
    cursor.execute("""
        UPDATE batches
        SET quantity = quantity + ?
        WHERE id = ?
    """, (quantity, batch_id))

    if cursor.rowcount:
        return

    cursor.execute("""
        INSERT OR IGNORE INTO batches (
            id,
            product_id,
            batch_number,
            expiry_date,
            quantity,
            purchase_unit_cost,
            total_purchase_cost,
            discount_percent,
            discount_applied_date
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, NULL)
    """, (
        batch_id,
        product_id,
        batch_number,
        expiry_date,
        quantity,
    ))

    if cursor.rowcount:
        return

    cursor.execute("""
        UPDATE batches
        SET quantity = quantity + ?
        WHERE batch_number = ?
    """, (quantity, batch_number))


def process_sale_return(sale_id, return_requests, acting_username=None, acting_role=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM returns
            WHERE sale_id = ?
        """, (sale_id,))
        existing_returns = int(cursor.fetchone()["total"] or 0)

        sale_context = _build_sale_return_context(cursor, sale_id)

        if not sale_context["return_window_open"]:
            return False, (
                f"Items from {sale_context['receipt_number']} can only be returned until "
                f"{sale_context['return_deadline']}."
            )

        valid_requests = []
        for request in return_requests:
            quantity = int(request.get("quantity", 0) or 0)
            if quantity > 0:
                valid_requests.append({
                    "sale_item_id": int(request["sale_item_id"]),
                    "quantity": quantity,
                })

        if not valid_requests:
            return False, "Select at least one item to return."

        items_by_id = {
            item["sale_item_id"]: item
            for item in sale_context["items"]
        }

        prepared_returns = []
        total_amount = 0

        for request in valid_requests:
            item = items_by_id.get(request["sale_item_id"])
            if item is None:
                return False, "One of the selected sale items could not be found."

            if item["returnable_quantity"] <= 0:
                if item["expired_blocked_quantity"] > 0:
                    return False, (
                        f"{item['product_name']} can no longer be returned because the sold "
                        "units have already expired."
                    )
                return False, f"No returnable quantity remains for {item['product_name']}."

            if request["quantity"] > item["returnable_quantity"]:
                return False, (
                    f"Only {item['returnable_quantity']} unit(s) of {item['product_name']} "
                    "can be returned."
                )

            remaining_quantity = request["quantity"]
            allocations = []

            for batch in item["batch_options"]:
                take = min(batch["remaining_quantity"], remaining_quantity)
                if take <= 0:
                    continue

                allocations.append({
                    "sale_batch_allocation_id": batch["sale_batch_allocation_id"],
                    "batch_id": batch["batch_id"],
                    "batch_number": batch["batch_number"],
                    "expiry_date": batch["expiry_date"],
                    "quantity": take,
                })
                remaining_quantity -= take

                if remaining_quantity == 0:
                    break

            if remaining_quantity > 0:
                return False, (
                    f"The original batch mapping for {item['product_name']} is incomplete, "
                    "so the return could not be processed."
                )

            subtotal = round(request["quantity"] * item["unit_price"], 2)
            total_amount += subtotal

            prepared_returns.append({
                "sale_item_id": item["sale_item_id"],
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "quantity": request["quantity"],
                "unit_price": item["unit_price"],
                "subtotal": subtotal,
                "allocations": allocations,
            })

        cursor.execute("""
            INSERT INTO returns (
                sale_id,
                processed_by_username,
                processed_by_role,
                total_amount,
                return_datetime
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            sale_id,
            (acting_username or "Unknown").strip(),
            (acting_role or "").strip() or None,
            total_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        return_id = cursor.lastrowid

        for returned_item in prepared_returns:
            cursor.execute("""
                INSERT INTO return_items (
                    return_id,
                    sale_item_id,
                    product_id,
                    product_name,
                    quantity,
                    unit_price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                return_id,
                returned_item["sale_item_id"],
                returned_item["product_id"],
                returned_item["product_name"],
                returned_item["quantity"],
                returned_item["unit_price"],
                returned_item["subtotal"],
            ))
            return_item_id = cursor.lastrowid

            for allocation in returned_item["allocations"]:
                _restore_batch_quantity(
                    cursor,
                    returned_item["product_id"],
                    allocation["batch_id"],
                    allocation["batch_number"],
                    allocation["expiry_date"],
                    allocation["quantity"],
                )

                cursor.execute("""
                    INSERT INTO return_batch_allocations (
                        return_item_id,
                        sale_batch_allocation_id,
                        batch_id,
                        batch_number,
                        quantity,
                        expiry_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    return_item_id,
                    allocation["sale_batch_allocation_id"],
                    allocation["batch_id"],
                    allocation["batch_number"],
                    allocation["quantity"],
                    allocation["expiry_date"],
                ))

            if acting_username:
                add_audit_log(
                    acting_username,
                    f"Carried out item return for {returned_item['product_name']} "
                    f"x{returned_item['quantity']} from {format_receipt_number(sale_id)}",
                    role=acting_role,
                    conn=conn,
                    cursor=cursor
                )

        conn.commit()

        action_word = "return" if existing_returns == 0 else "additional return"
        return True, (
            f"Processed {action_word} for {sale_context['receipt_number']}. "
            f"Refunded {total_amount:g} Ft."
        )
    except ValueError as error:
        return False, str(error)
    finally:
        conn.close()


def delete_return_record(return_id, acting_username=None, acting_role=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            sale_id
        FROM returns
        WHERE id = ?
    """, (return_id,))
    returned_sale = cursor.fetchone()

    if not returned_sale:
        conn.close()
        return False, "Return record not found."

    cursor.execute("""
        SELECT
            rba.batch_id,
            rba.batch_number,
            rba.quantity,
            rba.expiry_date
        FROM return_batch_allocations rba
        JOIN return_items ri ON ri.id = rba.return_item_id
        WHERE ri.return_id = ?
    """, (return_id,))
    allocations = cursor.fetchall()

    for allocation in allocations:
        cursor.execute("""
            SELECT quantity
            FROM batches
            WHERE id = ?
        """, (allocation["batch_id"],))
        batch = cursor.fetchone()

        if not batch:
            conn.close()
            return False, (
                f"Batch {allocation['batch_number']} no longer exists, so this return "
                "cannot be deleted safely."
            )

        if int(batch["quantity"] or 0) < int(allocation["quantity"] or 0):
            conn.close()
            return False, (
                f"Not enough stock remains in batch {allocation['batch_number']} to undo "
                f"return {format_receipt_number(return_id)}."
            )

    for allocation in allocations:
        cursor.execute("""
            UPDATE batches
            SET quantity = quantity - ?
            WHERE id = ?
        """, (
            allocation["quantity"],
            allocation["batch_id"],
        ))

    cursor.execute("""
        DELETE FROM return_batch_allocations
        WHERE return_item_id IN (
            SELECT id
            FROM return_items
            WHERE return_id = ?
        )
    """, (return_id,))

    cursor.execute("""
        DELETE FROM return_items
        WHERE return_id = ?
    """, (return_id,))

    cursor.execute("""
        DELETE FROM returns
        WHERE id = ?
    """, (return_id,))

    if acting_username:
        add_audit_log(
            acting_username,
            f"Deleted return {format_receipt_number(return_id)} for "
            f"{format_receipt_number(returned_sale['sale_id'])}",
            role=acting_role,
            conn=conn,
            cursor=cursor
        )

    conn.commit()
    conn.close()
    return True, "Return deleted successfully."


def get_batch_rows(search_text="", category="All Categories"):
    conn = get_connection()
    cursor = conn.cursor()

    search_value = f"%{search_text.strip().lower()}%"

    cursor.execute("""
        SELECT
            b.id AS batch_id,
            p.id AS product_id,
            p.name,
            p.category,
            p.selling_price,
            p.min_stock_level,
            b.batch_number,
            b.quantity,
            b.expiry_date,
            CASE
                WHEN date(b.expiry_date) < date('now') THEN 1
                ELSE 0
            END AS expired
        FROM batches b
        JOIN products p ON p.id = b.product_id
        WHERE LOWER(p.name) LIKE ?
          AND (? = 'All Categories' OR p.category = ?)
        ORDER BY LOWER(p.name), date(b.expiry_date), b.batch_number
    """, (search_value, category, category))

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "batch_id": row["batch_id"],
            "product_id": row["product_id"],
            "name": row["name"],
            "category": row["category"] or "General",
            "price": row["selling_price"],
            "min_stock_level": row["min_stock_level"],
            "batch_number": row["batch_number"],
            "stock": row["quantity"],
            "expiry_date": row["expiry_date"],
            "expired": bool(row["expired"]),
        })

    conn.close()
    return rows


def get_fefo_allocations(product_id, requested_quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, batch_number, expiry_date, quantity
        FROM batches
        WHERE product_id = ?
          AND quantity > 0
          AND date(expiry_date) >= date('now')
        ORDER BY date(expiry_date) ASC, id ASC
    """, (product_id,))

    batches = cursor.fetchall()
    conn.close()

    allocations = []
    remaining = int(requested_quantity)

    for batch in batches:
        if remaining <= 0:
            break

        take = min(batch["quantity"], remaining)
        if take > 0:
            allocations.append({
                "batch_id": batch["id"],
                "batch_number": batch["batch_number"],
                "expiry_date": batch["expiry_date"],
                "quantity": take,
            })
            remaining -= take

    if remaining > 0:
        return None

    return allocations


def preview_sale_allocations(cart_items):
    conn = get_connection()
    cursor = conn.cursor()

    plan = []
    total_amount = 0

    for item in cart_items:
        cursor.execute("""
            SELECT
                p.id,
                p.name,
                p.selling_price,
                COALESCE(MAX(
                    CASE
                        WHEN b.quantity > 0
                         AND date(b.expiry_date) >= date('now')
                         AND b.discount_percent > 0
                        THEN b.discount_percent
                        ELSE 0
                    END
                ), 0) AS active_discount_percent
            FROM products p
            LEFT JOIN batches b ON b.product_id = p.id
            WHERE p.id = ?
            GROUP BY p.id, p.name, p.selling_price
        """, (item["product_id"],))
        product = cursor.fetchone()

        if not product:
            conn.close()
            raise ValueError("Product not found.")

        allocations = get_fefo_allocations(item["product_id"], item["quantity"])
        if not allocations:
            conn.close()
            raise ValueError(f"Insufficient non-expired stock for {product['name']}.")

        discount_percent = float(product["active_discount_percent"] or 0)
        current_price = float(product["selling_price"])

        if discount_percent > 0:
            current_price = round(current_price * (1 - discount_percent / 100), 2)

        subtotal = item["quantity"] * current_price
        total_amount += subtotal

        plan.append({
            "product_id": item["product_id"],
            "product_name": product["name"],
            "quantity": item["quantity"],
            "price": current_price,
            "subtotal": subtotal,
            "allocations": allocations,
        })

    conn.close()
    return plan, total_amount


def create_sale(
    cart_items,
    payment_method,
    cashier_id=1,
    acting_username=None,
    acting_role=None,
    customer_ssn=None,
    customer_name=None
):
    plan, total_amount = preview_sale_allocations(cart_items)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sales (sale_datetime, total_amount, cashier_id, payment_method)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        total_amount,
        cashier_id,
        payment_method
    ))

    sale_id = cursor.lastrowid
    normalized_ssn = normalize_customer_ssn(customer_ssn)
    normalized_name = (customer_name or "").strip()

    for item in plan:
        cursor.execute("""
            SELECT prescription_required
            FROM products
            WHERE id = ?
        """, (item["product_id"],))
        prescription_row = cursor.fetchone()

        if prescription_row and prescription_row["prescription_required"]:
            if not normalized_ssn or not normalized_name:
                conn.close()
                raise ValueError("Customer SSN and name are required for prescription medicines.")

            cursor.execute("""
                INSERT INTO prescriptions (
                    sale_id,
                    customer_ssn,
                    customer_name,
                    product_id,
                    medicine_name,
                    amount,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                sale_id,
                normalized_ssn,
                normalized_name,
                item["product_id"],
                item["product_name"],
                int(item["quantity"]),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))

        cursor.execute("""
            INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sale_id,
            item["product_id"],
            item["product_name"],
            item["quantity"],
            item["price"],
            item["subtotal"]
        ))

        sale_item_id = cursor.lastrowid

        if acting_username:
            add_audit_log(
                acting_username,
                f"Sold {item['product_name']} x{int(item['quantity'])}",
                role=acting_role,
                conn=conn,
                cursor=cursor
            )

        for allocation in item["allocations"]:
            cursor.execute("""
                UPDATE batches
                SET quantity = quantity - ?
                WHERE id = ?
            """, (allocation["quantity"], allocation["batch_id"]))

            cursor.execute("""
                INSERT INTO sale_batch_allocations (
                    sale_item_id,
                    batch_id,
                    batch_number,
                    quantity,
                    expiry_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                sale_item_id,
                allocation["batch_id"],
                allocation["batch_number"],
                allocation["quantity"],
                allocation["expiry_date"]
            ))



    conn.commit()
    conn.close()

    return plan, total_amount


def delete_sale_record(sale_id, acting_username=None, acting_role=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM sales
        WHERE id = ?
    """, (sale_id,))
    sale = cursor.fetchone()

    if not sale:
        conn.close()
        return False, "Sale not found."

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM returns
        WHERE sale_id = ?
    """, (sale_id,))
    if int(cursor.fetchone()["total"] or 0) > 0:
        conn.close()
        return False, "This sale already has processed returns and can no longer be deleted."

    cursor.execute("""
        SELECT
            si.product_id,
            sba.batch_id,
            sba.batch_number,
            sba.quantity,
            sba.expiry_date
        FROM sale_batch_allocations sba
        JOIN sale_items si ON si.id = sba.sale_item_id
        WHERE si.sale_id = ?
    """, (sale_id,))
    allocations = cursor.fetchall()

    for allocation in allocations:
        _restore_batch_quantity(
            cursor,
            allocation["product_id"],
            allocation["batch_id"],
            allocation["batch_number"],
            allocation["expiry_date"],
            allocation["quantity"],
        )

    cursor.execute("""
        DELETE FROM sale_batch_allocations
        WHERE sale_item_id IN (
            SELECT id
            FROM sale_items
            WHERE sale_id = ?
        )
    """, (sale_id,))

    cursor.execute("""
        DELETE FROM prescriptions
        WHERE sale_id = ?
    """, (sale_id,))


    cursor.execute("""
        DELETE FROM sale_items
        WHERE sale_id = ?
    """, (sale_id,))

    cursor.execute("""
        DELETE FROM sales
        WHERE id = ?
    """, (sale_id,))

    if acting_username:
        add_audit_log(
            acting_username,
            f"Deleted sale {format_receipt_number(sale_id)}",
            role=acting_role,
            conn=conn,
            cursor=cursor
        )

    conn.commit()
    conn.close()

    return True, "Sale deleted successfully."



def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM products")
    medicines = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM sales")
    sales = cursor.fetchone()["total"]

    cursor.execute("SELECT COALESCE(SUM(quantity), 0) AS total FROM return_items")
    returned_items = int(cursor.fetchone()["total"] or 0)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM batches
        WHERE date(expiry_date) < date('now')
    """)
    expired = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM products p
        WHERE (
            SELECT COALESCE(SUM(b.quantity), 0)
            FROM batches b
            WHERE b.product_id = p.id
              AND date(b.expiry_date) >= date('now')
        ) < p.min_stock_level
    """)
    low_stock = cursor.fetchone()["total"]

    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) AS revenue FROM sales")
    gross_revenue = float(cursor.fetchone()["revenue"] or 0)

    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) AS refunded FROM returns")
    refunded_amount = float(cursor.fetchone()["refunded"] or 0)
    revenue = gross_revenue - refunded_amount

    conn.close()
    return medicines, sales, returned_items, expired, low_stock, revenue

def get_low_stock_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.name,
            p.min_stock_level,
            COALESCE(SUM(
                CASE
                    WHEN date(b.expiry_date) >= date('now') THEN b.quantity
                    ELSE 0
                END
            ), 0) AS available_units
        FROM products p
        LEFT JOIN batches b ON b.product_id = p.id
        GROUP BY p.id, p.name, p.min_stock_level
        HAVING available_units < p.min_stock_level
        ORDER BY available_units ASC, p.name ASC
    """)

    rows = []
    for row in cursor.fetchall():
        rows.append((
            row["name"],
            row["available_units"],
            row["min_stock_level"],
        ))

    conn.close()
    return rows

def get_recent_sales():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            total_amount,
            sale_datetime
        FROM sales
        ORDER BY id DESC
        LIMIT 5
    """)

    rows = []
    for row in cursor.fetchall():
        rows.append((
            row["id"],
            format_receipt_number(row["id"]),
            row["total_amount"],
        ))

    conn.close()
    return rows


def get_sales_history(search_text=""):
    conn = get_connection()
    cursor = conn.cursor()

    search_text = search_text.strip().replace("#", "")

    if search_text:
        if not search_text.isdigit():
            conn.close()
            return []

        cursor.execute("""
            SELECT
                s.id,
                s.sale_datetime,
                s.total_amount,
                s.payment_method,
                COALESCE(SUM(si.quantity), 0) AS total_items
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.id
            WHERE s.id = ?
            GROUP BY s.id, s.sale_datetime, s.total_amount, s.payment_method
            ORDER BY s.id DESC
        """, (int(search_text),))

    else:
        cursor.execute("""
            SELECT
                s.id,
                s.sale_datetime,
                s.total_amount,
                s.payment_method,
                COALESCE(SUM(si.quantity), 0) AS total_items
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.id
            GROUP BY s.id, s.sale_datetime, s.total_amount, s.payment_method
            ORDER BY s.id DESC
        """)


    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "items": row["total_items"],
            "date": row["sale_datetime"],
            "total": row["total_amount"],
            "payment_method": row["payment_method"] or "N/A",
            "receipt_number": format_receipt_number(row["id"]),
        })


    conn.close()
    return rows


def get_returns_history(search_text=""):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_search = search_text.strip().lower().replace("#", "")

    base_query = """
        SELECT
            r.id,
            r.sale_id,
            r.return_datetime,
            r.total_amount,
            r.processed_by_username,
            COALESCE(SUM(ri.quantity), 0) AS total_items
        FROM returns r
        LEFT JOIN return_items ri ON ri.return_id = r.id
    """

    if normalized_search:
        if normalized_search.isdigit():
            numeric_value = int(normalized_search)
            cursor.execute(base_query + """
                WHERE r.id = ?
                   OR r.sale_id = ?
                GROUP BY
                    r.id,
                    r.sale_id,
                    r.return_datetime,
                    r.total_amount,
                    r.processed_by_username
                ORDER BY r.id DESC
            """, (numeric_value, numeric_value))
        else:
            cursor.execute(base_query + """
                WHERE LOWER(COALESCE(r.processed_by_username, '')) LIKE ?
                GROUP BY
                    r.id,
                    r.sale_id,
                    r.return_datetime,
                    r.total_amount,
                    r.processed_by_username
                ORDER BY r.id DESC
            """, (f"%{normalized_search}%",))
    else:
        cursor.execute(base_query + """
            GROUP BY
                r.id,
                r.sale_id,
                r.return_datetime,
                r.total_amount,
                r.processed_by_username
            ORDER BY r.id DESC
        """)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "return_receipt_number": format_receipt_number(row["id"]),
            "source_sale_id": row["sale_id"],
            "source_receipt_number": format_receipt_number(row["sale_id"]),
            "date": row["return_datetime"] or "",
            "refund_amount": float(row["total_amount"] or 0),
            "total_items": int(row["total_items"] or 0),
            "processed_by": row["processed_by_username"] or "",
        })

    conn.close()
    return rows

def get_sale_receipt_data(sale_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            sale_datetime,
            total_amount,
            payment_method
        FROM sales
        WHERE id = ?
    """, (sale_id,))
    sale = cursor.fetchone()

    if not sale:
        conn.close()
        return None

    cursor.execute("""
        SELECT
            si.product_name,
            si.quantity,
            si.unit_price,
            si.subtotal
        FROM sale_items si
        WHERE si.sale_id = ?
        ORDER BY si.id ASC
    """, (sale_id,))

    items = cursor.fetchall()

    conn.close()

    return {
        "sale_id": sale["id"],
        "receipt_number": format_receipt_number(sale["id"]),
        "date": sale["sale_datetime"],
        "total": sale["total_amount"],
        "payment_method": sale["payment_method"] or "N/A",
        "items": [
            {
                "name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "subtotal": item["subtotal"],
            }
            for item in items
        ]
    }


def get_return_report_data(return_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.id,
            r.sale_id,
            r.return_datetime,
            r.total_amount,
            r.processed_by_username,
            r.processed_by_role,
            s.payment_method,
            s.sale_datetime
        FROM returns r
        JOIN sales s ON s.id = r.sale_id
        WHERE r.id = ?
    """, (return_id,))
    returned_sale = cursor.fetchone()

    if not returned_sale:
        conn.close()
        return None

    cursor.execute("""
        SELECT
            product_name,
            quantity,
            unit_price,
            subtotal
        FROM return_items
        WHERE return_id = ?
        ORDER BY id ASC
    """, (return_id,))
    items = cursor.fetchall()

    conn.close()

    return {
        "return_id": returned_sale["id"],
        "return_receipt_number": format_receipt_number(returned_sale["id"]),
        "source_sale_id": returned_sale["sale_id"],
        "source_receipt_number": format_receipt_number(returned_sale["sale_id"]),
        "return_date": returned_sale["return_datetime"],
        "source_sale_date": returned_sale["sale_datetime"],
        "refund_total": float(returned_sale["total_amount"] or 0),
        "processed_by": returned_sale["processed_by_username"] or "",
        "processed_role": returned_sale["processed_by_role"] or "",
        "payment_method": returned_sale["payment_method"] or "N/A",
        "total_items": sum(int(item["quantity"]) for item in items),
        "items": [
            {
                "name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "subtotal": item["subtotal"],
            }
            for item in items
        ]
    }



def get_expiring_soon():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.name, b.batch_number, b.expiry_date
        FROM batches b
        JOIN products p ON b.product_id = p.id
        WHERE date(b.expiry_date) >= date('now')
          AND date(b.expiry_date) <= date('now', '+30 days')
        ORDER BY date(b.expiry_date) ASC
    """)


    rows = []
    for row in cursor.fetchall():
        rows.append((row["name"], row["batch_number"], row["expiry_date"]))

    conn.close()
    return rows
