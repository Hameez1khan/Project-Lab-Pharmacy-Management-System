import base64
import hashlib
import hmac
import sqlite3
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from datetime import datetime, timedelta

import os
import sys

if getattr(sys, "frozen", False):
    data_dir = Path(os.environ["LOCALAPPDATA"]) / "KhalisDawa"
    data_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH = data_dir / "pharmacy.db"
else:
    DB_PATH = Path(__file__).resolve().parent / "pharmacy.db"
RETURN_WINDOW_DAYS = 3
DB_PATH_ENV = "KHALIS_DAWA_DB_PATH"
DB_BUSY_TIMEOUT_MS = 5000
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_VERSION = "v1"
PASSWORD_ITERATIONS = 600_000


from database import inventory_audit


def get_database_path():
    """Return the configured database without changing the production default."""
    override = os.environ.get(DB_PATH_ENV)
    return Path(override).expanduser().resolve() if override else DB_PATH


def get_connection(reason="Inventory change"):
    conn = sqlite3.connect(get_database_path(), timeout=DB_BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {DB_BUSY_TIMEOUT_MS}")
    inventory_audit.bind(conn, reason)
    return conn


def hash_password(password, *, iterations=PASSWORD_ITERATIONS):
    password = str(password or "").strip()
    if not password:
        raise ValueError("Password is required.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join((
        PASSWORD_SCHEME,
        PASSWORD_VERSION,
        str(iterations),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def is_password_hash(value):
    return str(value or "").startswith(f"{PASSWORD_SCHEME}${PASSWORD_VERSION}$")


def verify_password(password, stored_value):
    candidate = str(password or "").strip()
    stored = str(stored_value or "")
    if not is_password_hash(stored):
        return hmac.compare_digest(candidate, stored.strip())
    try:
        scheme, version, iterations, salt_text, digest_text = stored.split("$", 4)
        if scheme != PASSWORD_SCHEME or version != PASSWORD_VERSION:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", candidate.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def normalize_customer_ssn(ssn):
    return "".join(char for char in (ssn or "").strip() if char.isdigit())


def is_valid_customer_ssn(ssn):
    return len(normalize_customer_ssn(ssn)) == 9


def format_receipt_number(record_id, transaction_date=None, prefix="KD"):
    """Return a stable business identifier while preserving legacy callers.

    Existing relationships continue to use integer primary keys.  Screens that
    have a transaction date receive a readable KD-YYYYMMDD-00001 identifier;
    older call sites without a date retain the legacy number.
    """
    if transaction_date:
        compact_date = str(transaction_date).strip()[:10].replace("-", "")
        if len(compact_date) == 8 and compact_date.isdigit():
            return f"{prefix}-{compact_date}-{int(record_id):05d}"
    return f"#{int(record_id):05d}"


def parse_receipt_search(value):
    """Accept a database id, legacy #00001, or KD-YYYYMMDD-00001."""
    normalized = str(value or "").strip().replace("#", "")
    if not normalized:
        return None
    tail = normalized.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def get_dashboard_sales_trend(days=30):
    """Return zero-filled daily net sales ending today using real sale/refund data."""
    try:
        days = int(days)
    except (TypeError, ValueError) as error:
        raise ValueError("Days must be a whole number.") from error
    if not 1 <= days <= 366:
        raise ValueError("Days must be between 1 and 366.")

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)
    conn = get_connection()
    try:
        rows = conn.execute("""
            WITH flow(day, amount) AS (
                SELECT date(sale_datetime), total_amount FROM sales
                UNION ALL
                SELECT date(return_datetime), -total_amount FROM returns
            )
            SELECT day, ROUND(SUM(amount), 2) AS net_sales
            FROM flow
            WHERE day BETWEEN ? AND ?
            GROUP BY day
        """, (start_date.isoformat(), end_date.isoformat())).fetchall()
        amounts = {row["day"]: float(row["net_sales"] or 0) for row in rows}
    finally:
        conn.close()

    return [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "net_sales": amounts.get(
                (start_date + timedelta(days=offset)).isoformat(), 0.0
            ),
        }
        for offset in range(days)
    ]



def refresh_expiring_soon_discounts():
    conn = get_connection("Automatic expiry discount review")
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

    missing = expected_prescription_columns - set(prescription_columns)
    additions = {
        "sale_id": "INTEGER REFERENCES sales(id)",
        "created_at": "TEXT",
    }
    unknown = missing - additions.keys()
    if unknown:
        conn.close()
        raise RuntimeError(
            "Prescriptions are missing required fields: "
            + ", ".join(sorted(unknown))
            + ". Existing records were preserved. Review the database before continuing."
        )

    for column, definition in additions.items():
        if column in missing:
            cursor.execute(
                f"ALTER TABLE prescriptions ADD COLUMN {column} {definition}"
            )





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
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    )
    """)

    supplier_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(suppliers)").fetchall()
    }
    if "lead_time_days" not in supplier_columns:
        cursor.execute(
            "ALTER TABLE suppliers ADD COLUMN lead_time_days INTEGER NOT NULL DEFAULT 7"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
        supplier_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        expected_date TEXT,
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK(status IN ('draft','pending','ordered','partially_received',
                             'fully_received','cancelled')),
        notes TEXT,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        ordered_quantity INTEGER NOT NULL CHECK(ordered_quantity > 0),
        received_quantity INTEGER NOT NULL DEFAULT 0
            CHECK(received_quantity >= 0 AND received_quantity <= ordered_quantity),
        unit_cost REAL NOT NULL CHECK(unit_cost > 0),
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
        UNIQUE(purchase_order_id, product_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        reference_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
        received_date TEXT NOT NULL,
        notes TEXT,
        received_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
    )
    """)

    receipt_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(purchase_receipts)").fetchall()
    }
    if "purchase_order_id" not in receipt_columns:
        cursor.execute(
            "ALTER TABLE purchase_receipts ADD COLUMN purchase_order_id INTEGER "
            "REFERENCES purchase_orders(id) ON DELETE RESTRICT"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_receipt_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        batch_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        unit_cost REAL NOT NULL CHECK(unit_cost > 0),
        total_cost REAL NOT NULL CHECK(total_cost > 0),
        FOREIGN KEY (receipt_id) REFERENCES purchase_receipts(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE RESTRICT
    )
    """)

    receipt_item_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(purchase_receipt_items)").fetchall()
    }
    if "purchase_order_item_id" not in receipt_item_columns:
        cursor.execute(
            "ALTER TABLE purchase_receipt_items ADD COLUMN purchase_order_item_id INTEGER "
            "REFERENCES purchase_order_items(id) ON DELETE RESTRICT"
        )

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_status
        ON purchase_orders(supplier_id, status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_receipts_order
        ON purchase_receipts(purchase_order_id)
    """)

    # Keep common list, search, dashboard, and FEFO queries responsive as the
    # operational history grows. These indexes are safe to create repeatedly.
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
        "CREATE INDEX IF NOT EXISTS idx_batches_product_expiry ON batches(product_id, expiry_date)",
        "CREATE INDEX IF NOT EXISTS idx_batches_expiry_quantity ON batches(expiry_date, quantity)",
        "CREATE INDEX IF NOT EXISTS idx_sales_datetime ON sales(sale_datetime)",
        "CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id)",
        "CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_sale_allocations_item ON sale_batch_allocations(sale_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_created ON prescriptions(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_sale ON prescriptions(sale_id)",
        "CREATE INDEX IF NOT EXISTS idx_returns_datetime ON returns(return_datetime)",
        "CREATE INDEX IF NOT EXISTS idx_returns_sale ON returns(sale_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(username)",
    ):
        cursor.execute(statement)

    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', ?, 'admin')
    """, (hash_password("1234"),))



    from database.workbook import setup as setup_workbook
    inventory_audit.install(conn)
    setup_workbook(conn)
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

    if not user:
        conn.close()
        return None

    if not verify_password(password, user["password"]):
        conn.close()
        return None

    if not is_password_hash(user["password"]):
        conn.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hash_password(password), user["id"]),
        )
        conn.commit()

    conn.close()

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
    """, (username, hash_password(password)))

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


def change_user_password(username, current_password, new_password,
                         acting_username=None, acting_role=None):
    """Validate and update a password without exposing its stored representation."""
    username = (username or "").strip()
    new_password = str(new_password or "").strip()
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters long."

    conn = get_connection("Password changed")
    try:
        user = conn.execute(
            "SELECT id, password FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not user:
            return False, "Selected user account not found."
        if not verify_password(current_password, user["password"]):
            return False, "Current password is incorrect."

        conn.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hash_password(new_password), user["id"]),
        )
        add_audit_log(
            acting_username or username,
            f"Updated password for {username}",
            role=acting_role,
            conn=conn,
            cursor=conn.cursor(),
        )
        conn.commit()
        return True, f"Password updated successfully for {username}."
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()




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


def get_audit_log_rows(search_text="", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    normalized = f"%{search_text.strip().lower()}%"

    query = """
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
    """
    params = [normalized, normalized, normalized]
    if limit is not None:
        query += " LIMIT ?"
        params.append(max(0, int(limit)) + max(0, int(offset)))
    cursor.execute(query, params)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "username": row["username"],
            "role": row["role"] or "",
            "description": row["description"],
            "created_at": row["created_at"] or "",
        })

    history_limit = None if limit is None else max(0, int(limit)) + max(0, int(offset))
    rows.extend(inventory_audit.history(conn, search_text.strip(), history_limit, 0))
    conn.close()
    rows = sorted(rows, key=lambda row: row["created_at"], reverse=True)
    if limit is not None:
        start = max(0, int(offset))
        return rows[start:start + max(0, int(limit))]
    return rows


def get_audit_log_count(search_text=""):
    conn = get_connection()
    normalized = f"%{search_text.strip().lower()}%"
    total = conn.execute("""
        SELECT COUNT(*) AS total FROM audit_logs
        WHERE LOWER(username) LIKE ? OR LOWER(COALESCE(role, '')) LIKE ? OR LOWER(description) LIKE ?
    """, (normalized, normalized, normalized)).fetchone()["total"]
    total += inventory_audit.history_count(conn, search_text.strip())
    conn.close()
    return int(total)


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
    conn = get_connection("Stock loaded")
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


def add_batch_record(product_name, batch_number, quantity, expiry_date, purchase_unit_cost):
    from decimal import Decimal, InvalidOperation

    try:
        cost = Decimal(str(purchase_unit_cost))
        if not cost.is_finite() or not 0 < cost <= 999_999_999:
            raise ValueError
        if cost != cost.quantize(Decimal("0.01")):
            raise ValueError
    except (InvalidOperation, TypeError, ValueError):
        return False, "Enter a positive purchase cost with at most two decimal places."

    conn = get_connection("Batch received")
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

    unit_cost = float(cost)
    total_cost = float(cost * int(quantity))

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


def get_purchase_products():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name FROM products ORDER BY LOWER(name)"
    ).fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def get_suppliers(search_text=""):
    conn = get_connection()
    pattern = f"%{search_text.strip().lower()}%"
    rows = conn.execute("""
        SELECT id, name, contact_person, phone, email, address, lead_time_days, created_at
        FROM suppliers
        WHERE LOWER(name) LIKE ?
           OR LOWER(COALESCE(contact_person, '')) LIKE ?
           OR LOWER(COALESCE(phone, '')) LIKE ?
           OR LOWER(COALESCE(email, '')) LIKE ?
        ORDER BY LOWER(name)
    """, (pattern, pattern, pattern, pattern)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_supplier(name, contact_person="", phone="", email="", address="",
                  supplier_id=None, acting_username=None, acting_role=None,
                  lead_time_days=7):
    _require_purchase_admin(acting_role)
    name = str(name or "").strip()
    contact_person = str(contact_person or "").strip()
    phone = str(phone or "").strip()
    email = str(email or "").strip()
    address = str(address or "").strip()
    try:
        lead_time_days = int(lead_time_days)
    except (TypeError, ValueError):
        return False, "Supplier lead time must be a whole number of days."
    if not name:
        return False, "Supplier name is required."
    if len(name) > 120 or any(len(value) > 250 for value in (contact_person, phone, email, address)):
        return False, "Supplier details are too long."
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        return False, "Enter a valid email address."
    if not 0 <= lead_time_days <= 365:
        return False, "Supplier lead time must be between 0 and 365 days."

    conn = get_connection("Supplier record updated")
    cursor = conn.cursor()
    try:
        if supplier_id is None:
            cursor.execute("""
                INSERT INTO suppliers(name, contact_person, phone, email, address,
                                      lead_time_days, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, contact_person, phone, email, address,
                  lead_time_days, datetime.now().strftime("%Y-%m-%d %H:%M")))
            description = f"Added supplier {name}"
        else:
            if not cursor.execute("SELECT 1 FROM suppliers WHERE id=?", (supplier_id,)).fetchone():
                return False, "Supplier was not found."
            cursor.execute("""
                UPDATE suppliers
                SET name=?, contact_person=?, phone=?, email=?, address=?, lead_time_days=?
                WHERE id=?
            """, (name, contact_person, phone, email, address, lead_time_days,
                  int(supplier_id)))
            description = f"Updated supplier {name}"
        add_audit_log(acting_username or "System", description, acting_role,
                      conn=conn, cursor=cursor)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "A supplier with this name already exists."
    finally:
        conn.close()
    return True, "Supplier saved successfully."


def delete_supplier(supplier_id, acting_username=None, acting_role=None):
    _require_purchase_admin(acting_role)
    conn = get_connection("Supplier removed")
    cursor = conn.cursor()
    supplier = cursor.execute(
        "SELECT name FROM suppliers WHERE id=?", (int(supplier_id),)
    ).fetchone()
    if not supplier:
        conn.close()
        return False, "Supplier was not found."
    if cursor.execute(
        "SELECT 1 FROM purchase_receipts WHERE supplier_id=? LIMIT 1", (int(supplier_id),)
    ).fetchone():
        conn.close()
        return False, "Suppliers with purchase history cannot be deleted."
    if cursor.execute(
        "SELECT 1 FROM purchase_orders WHERE supplier_id=? LIMIT 1", (int(supplier_id),)
    ).fetchone():
        conn.close()
        return False, "Suppliers with purchase orders cannot be deleted."
    cursor.execute("DELETE FROM suppliers WHERE id=?", (int(supplier_id),))
    add_audit_log(acting_username or "System", f"Deleted supplier {supplier['name']}",
                  acting_role, conn=conn, cursor=cursor)
    conn.commit()
    conn.close()
    return True, "Supplier deleted successfully."


def receive_purchase(supplier_id, reference_number, received_date, items, notes="",
                     acting_username=None, acting_role=None, purchase_order_id=None):
    _require_purchase_admin(acting_role)
    reference_number = str(reference_number or "").strip()
    received_date = str(received_date or "").strip()
    notes = str(notes or "").strip()
    if not reference_number or len(reference_number) > 80:
        raise ValueError("Enter a purchase reference number.")
    try:
        received_day = datetime.strptime(received_date, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Enter a valid received date.") from error
    if received_day > datetime.now().date():
        raise ValueError("The received date cannot be in the future.")
    if not items:
        raise ValueError("Add at least one received item.")
    try:
        supplier_id = int(supplier_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Choose a valid supplier.") from error

    normalized = []
    for item in items:
        try:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
            unit_cost = Decimal(str(item.get("unit_cost")))
            expiry = datetime.strptime(str(item.get("expiry_date", "")).strip(), "%Y-%m-%d").date()
        except (TypeError, ValueError, InvalidOperation) as error:
            raise ValueError("Check the product, quantity, cost, and expiry date on every line.") from error
        batch_number = str(item.get("batch_number") or "").strip()
        if not batch_number or len(batch_number) > 80:
            raise ValueError("Every received item needs a batch number.")
        if quantity <= 0 or quantity > 1_000_000:
            raise ValueError("Received quantities must be positive whole numbers.")
        if (not unit_cost.is_finite() or unit_cost <= 0 or unit_cost > Decimal("999999999")
                or unit_cost != unit_cost.quantize(Decimal("0.01"))):
            raise ValueError("Purchase costs must be positive with at most two decimal places.")
        if expiry <= received_day:
            raise ValueError("Batch expiry must be after the received date.")
        normalized.append({
            "product_id": product_id,
            "batch_number": batch_number,
            "expiry_date": expiry.isoformat(),
            "quantity": quantity,
            "unit_cost": float(unit_cost),
            "purchase_order_item_id": item.get("purchase_order_item_id"),
        })

    conn = get_connection(f"Purchase receipt {reference_number}")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        supplier = cursor.execute(
            "SELECT name FROM suppliers WHERE id=?", (supplier_id,)
        ).fetchone()
        if not supplier:
            raise ValueError("Choose a valid supplier.")
        order = None
        if purchase_order_id is not None:
            order = cursor.execute(
                "SELECT id, supplier_id, order_number, status FROM purchase_orders WHERE id=?",
                (int(purchase_order_id),),
            ).fetchone()
            if not order:
                raise ValueError("Purchase order was not found.")
            if int(order["supplier_id"]) != supplier_id:
                raise ValueError("The receipt supplier does not match the purchase order.")
            if order["status"] not in ("ordered", "partially_received"):
                raise ValueError("Only ordered or partially received orders can be received.")
        if cursor.execute(
            "SELECT 1 FROM purchase_receipts WHERE reference_number=? COLLATE NOCASE",
            (reference_number,),
        ).fetchone():
            raise ValueError("This purchase reference already exists.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("""
            INSERT INTO purchase_receipts
                (supplier_id, reference_number, received_date, notes, received_by,
                 created_at, purchase_order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (supplier_id, reference_number, received_date, notes,
              (acting_username or "System").strip(), now, purchase_order_id))
        receipt_id = cursor.lastrowid

        for item in normalized:
            order_item = None
            if order:
                try:
                    order_item_id = int(item["purchase_order_item_id"])
                except (TypeError, ValueError) as error:
                    raise ValueError("Every received line must belong to the purchase order.") from error
                order_item = cursor.execute("""
                    SELECT id, product_id, ordered_quantity, received_quantity, unit_cost
                    FROM purchase_order_items
                    WHERE id=? AND purchase_order_id=?
                """, (order_item_id, order["id"])).fetchone()
                if not order_item or int(order_item["product_id"]) != item["product_id"]:
                    raise ValueError("A received line does not match the purchase order.")
                outstanding = int(order_item["ordered_quantity"]) - int(order_item["received_quantity"])
                if item["quantity"] > outstanding:
                    raise ValueError("Received quantity exceeds the outstanding order quantity.")
            product = cursor.execute(
                "SELECT name FROM products WHERE id=?", (item["product_id"],)
            ).fetchone()
            if not product:
                raise ValueError("A selected product no longer exists.")
            existing = cursor.execute("""
                SELECT id, product_id, expiry_date, quantity, purchase_unit_cost
                FROM batches WHERE batch_number=? COLLATE NOCASE
            """, (item["batch_number"],)).fetchone()
            line_total = round(item["unit_cost"] * item["quantity"], 2)
            if existing:
                if (existing["product_id"] != item["product_id"]
                        or existing["expiry_date"] != item["expiry_date"]):
                    raise ValueError(
                        "Batch number conflicts with existing product or expiry details."
                    )
                new_quantity = existing["quantity"] + item["quantity"]
                stock_cost = existing["quantity"] * existing["purchase_unit_cost"] + line_total
                weighted_cost = round(stock_cost / new_quantity, 2)
                cursor.execute("""
                    UPDATE batches
                    SET quantity=?, purchase_unit_cost=?, total_purchase_cost=?
                    WHERE id=?
                """, (new_quantity, weighted_cost, round(stock_cost, 2), existing["id"]))
                batch_id = existing["id"]
            else:
                cursor.execute("""
                    INSERT INTO batches
                        (product_id, batch_number, expiry_date, quantity,
                         purchase_unit_cost, total_purchase_cost)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (item["product_id"], item["batch_number"], item["expiry_date"],
                      item["quantity"], item["unit_cost"], line_total))
                batch_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO purchase_receipt_items
                    (receipt_id, product_id, batch_id, batch_number, expiry_date,
                     quantity, unit_cost, total_cost, purchase_order_item_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (receipt_id, item["product_id"], batch_id, item["batch_number"],
                  item["expiry_date"], item["quantity"], item["unit_cost"], line_total,
                  order_item["id"] if order_item else None))
            if order_item:
                cursor.execute("""
                    UPDATE purchase_order_items
                    SET received_quantity=received_quantity+?
                    WHERE id=? AND received_quantity+? <= ordered_quantity
                """, (item["quantity"], order_item["id"], item["quantity"]))
                if cursor.rowcount != 1:
                    raise ValueError("Purchase order quantities changed. Refresh and try again.")

        if order:
            remaining = cursor.execute("""
                SELECT COALESCE(SUM(ordered_quantity-received_quantity), 0)
                FROM purchase_order_items WHERE purchase_order_id=?
            """, (order["id"],)).fetchone()[0]
            received = cursor.execute("""
                SELECT COALESCE(SUM(received_quantity), 0)
                FROM purchase_order_items WHERE purchase_order_id=?
            """, (order["id"],)).fetchone()[0]
            new_status = "fully_received" if int(remaining) == 0 else "partially_received"
            if int(received) == 0:
                new_status = "ordered"
            cursor.execute(
                "UPDATE purchase_orders SET status=?, updated_at=? WHERE id=?",
                (new_status, now, order["id"]),
            )

        total_quantity = sum(item["quantity"] for item in normalized)
        add_audit_log(
            acting_username or "System",
            f"Received purchase {reference_number} from {supplier['name']} ({total_quantity} units)",
            acting_role, conn=conn, cursor=cursor,
        )
        conn.commit()
        return receipt_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_purchase_history(search_text=""):
    conn = get_connection()
    pattern = f"%{search_text.strip().lower()}%"
    rows = conn.execute("""
        SELECT r.id, r.reference_number, r.received_date, s.name AS supplier,
               COUNT(i.id) AS line_count, COALESCE(SUM(i.quantity), 0) AS quantity,
               COALESCE(SUM(i.total_cost), 0) AS total_cost, r.received_by, r.notes
        FROM purchase_receipts r
        JOIN suppliers s ON s.id=r.supplier_id
        LEFT JOIN purchase_receipt_items i ON i.receipt_id=r.id
        WHERE LOWER(r.reference_number) LIKE ? OR LOWER(s.name) LIKE ?
        GROUP BY r.id
        ORDER BY r.received_date DESC, r.id DESC
    """, (pattern, pattern)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_purchase_receipt_items(receipt_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name AS product, i.batch_number, i.expiry_date, i.quantity,
               i.unit_cost, i.total_cost
        FROM purchase_receipt_items i
        JOIN products p ON p.id=i.product_id
        WHERE i.receipt_id=? ORDER BY i.id
    """, (int(receipt_id),)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_purchase_receipt(receipt_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT r.id, r.reference_number, r.received_date, r.received_by, r.notes,
               s.name AS supplier
        FROM purchase_receipts r
        JOIN suppliers s ON s.id=r.supplier_id
        WHERE r.id=?
    """, (int(receipt_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


PURCHASE_ORDER_STATUSES = (
    "draft", "pending", "ordered", "partially_received", "fully_received", "cancelled"
)


def _require_purchase_admin(acting_role):
    if str(acting_role or "").strip().lower() != "admin":
        raise PermissionError("Administrator access required.")


def _normalize_purchase_order_items(items):
    if not items:
        raise ValueError("Add at least one purchase order item.")
    normalized = []
    products = set()
    for item in items:
        try:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
            unit_cost = Decimal(str(item.get("unit_cost")))
        except (TypeError, ValueError, InvalidOperation) as error:
            raise ValueError("Check the product, quantity, and cost on every order line.") from error
        if product_id in products:
            raise ValueError("Each product can appear only once on a purchase order.")
        if not 1 <= quantity <= 1_000_000:
            raise ValueError("Ordered quantities must be positive whole numbers.")
        if (not unit_cost.is_finite() or not Decimal("0") < unit_cost <= Decimal("999999999")
                or unit_cost != unit_cost.quantize(Decimal("0.01"))):
            raise ValueError("Purchase costs must be positive with at most two decimal places.")
        products.add(product_id)
        normalized.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_cost": float(unit_cost),
        })
    return normalized


def save_purchase_order(supplier_id, order_date, expected_date, items, notes="",
                        status="draft", purchase_order_id=None,
                        acting_username=None, acting_role=None):
    """Create or edit a pre-delivery order without changing inventory."""
    _require_purchase_admin(acting_role)
    try:
        supplier_id = int(supplier_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Choose a valid supplier.") from error
    try:
        order_day = datetime.strptime(str(order_date), "%Y-%m-%d").date()
        expected_day = datetime.strptime(str(expected_date), "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Enter valid order and expected delivery dates.") from error
    if expected_day < order_day:
        raise ValueError("Expected delivery cannot be before the order date.")
    if status not in ("draft", "pending"):
        raise ValueError("New purchase orders must be draft or pending.")
    normalized = _normalize_purchase_order_items(items)
    notes = str(notes or "").strip()
    if len(notes) > 2000:
        raise ValueError("Purchase order notes are too long.")

    conn = get_connection("Purchase order saved")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        supplier = cursor.execute(
            "SELECT name FROM suppliers WHERE id=?", (supplier_id,)
        ).fetchone()
        if not supplier:
            raise ValueError("Choose a valid supplier.")
        product_ids = {row["id"] for row in cursor.execute(
            f"SELECT id FROM products WHERE id IN ({','.join('?' for _ in normalized)})",
            tuple(item["product_id"] for item in normalized),
        ).fetchall()}
        if product_ids != {item["product_id"] for item in normalized}:
            raise ValueError("A selected product no longer exists.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if purchase_order_id is None:
            next_id = int(cursor.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM purchase_orders"
            ).fetchone()[0])
            order_number = f"PO-{order_day.strftime('%Y%m%d')}-{next_id:04d}"
            cursor.execute("""
                INSERT INTO purchase_orders
                    (order_number, supplier_id, order_date, expected_date, status,
                     notes, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_number, supplier_id, order_day.isoformat(), expected_day.isoformat(),
                  status, notes, (acting_username or "System").strip(), now, now))
            purchase_order_id = cursor.lastrowid
            action = "Created"
        else:
            purchase_order_id = int(purchase_order_id)
            existing = cursor.execute(
                "SELECT order_number, status FROM purchase_orders WHERE id=?",
                (purchase_order_id,),
            ).fetchone()
            if not existing:
                raise ValueError("Purchase order was not found.")
            if existing["status"] not in ("draft", "pending"):
                raise ValueError("Only draft or pending purchase orders can be edited.")
            order_number = existing["order_number"]
            cursor.execute("""
                UPDATE purchase_orders
                SET supplier_id=?, order_date=?, expected_date=?, status=?, notes=?, updated_at=?
                WHERE id=?
            """, (supplier_id, order_day.isoformat(), expected_day.isoformat(), status,
                  notes, now, purchase_order_id))
            cursor.execute(
                "DELETE FROM purchase_order_items WHERE purchase_order_id=?",
                (purchase_order_id,),
            )
            action = "Updated"
        cursor.executemany("""
            INSERT INTO purchase_order_items
                (purchase_order_id, product_id, ordered_quantity, received_quantity, unit_cost)
            VALUES (?, ?, ?, 0, ?)
        """, [
            (purchase_order_id, item["product_id"], item["quantity"], item["unit_cost"])
            for item in normalized
        ])
        add_audit_log(
            acting_username or "System",
            f"{action} purchase order {order_number} for {supplier['name']}",
            acting_role, conn=conn, cursor=cursor,
        )
        conn.commit()
        return purchase_order_id, order_number
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def change_purchase_order_status(purchase_order_id, new_status,
                                 acting_username=None, acting_role=None):
    _require_purchase_admin(acting_role)
    transitions = {
        "draft": {"pending", "cancelled"},
        "pending": {"draft", "ordered", "cancelled"},
        "ordered": {"cancelled"},
        "partially_received": set(),
        "fully_received": set(),
        "cancelled": set(),
    }
    if new_status not in PURCHASE_ORDER_STATUSES:
        raise ValueError("Invalid purchase order status.")
    conn = get_connection("Purchase order status changed")
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute(
            "SELECT order_number, status FROM purchase_orders WHERE id=?",
            (int(purchase_order_id),),
        ).fetchone()
        if not order:
            raise ValueError("Purchase order was not found.")
        if new_status == "cancelled":
            received = conn.execute("""
                SELECT COALESCE(SUM(received_quantity), 0) FROM purchase_order_items
                WHERE purchase_order_id=?
            """, (int(purchase_order_id),)).fetchone()[0]
            if int(received):
                raise ValueError("A purchase order with received stock cannot be cancelled.")
        if new_status not in transitions[order["status"]]:
            raise ValueError("This purchase order status change is not allowed.")
        conn.execute(
            "UPDATE purchase_orders SET status=?, updated_at=? WHERE id=?",
            (new_status, datetime.now().strftime("%Y-%m-%d %H:%M"), int(purchase_order_id)),
        )
        add_audit_log(
            acting_username or "System",
            f"Changed purchase order {order['order_number']} from {order['status']} to {new_status}",
            acting_role, conn=conn, cursor=conn.cursor(),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_purchase_orders(search_text="", status="all", supplier_id=None):
    pattern = f"%{str(search_text or '').strip().lower()}%"
    clauses = ["(LOWER(o.order_number) LIKE ? OR LOWER(s.name) LIKE ?)"]
    parameters = [pattern, pattern]
    if status and status != "all":
        clauses.append("o.status=?")
        parameters.append(status)
    if supplier_id is not None:
        clauses.append("o.supplier_id=?")
        parameters.append(int(supplier_id))
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT o.id, o.order_number, o.supplier_id, s.name AS supplier,
               o.order_date, o.expected_date, o.status, o.created_by,
               COUNT(i.id) AS line_count,
               COALESCE(SUM(i.ordered_quantity), 0) AS ordered_quantity,
               COALESCE(SUM(i.received_quantity), 0) AS received_quantity,
               COALESCE(SUM((i.ordered_quantity-i.received_quantity)), 0) AS outstanding_quantity,
               COALESCE(SUM(i.ordered_quantity*i.unit_cost), 0) AS total_cost
        FROM purchase_orders o
        JOIN suppliers s ON s.id=o.supplier_id
        LEFT JOIN purchase_order_items i ON i.purchase_order_id=o.id
        WHERE {' AND '.join(clauses)}
        GROUP BY o.id
        ORDER BY o.order_date DESC, o.id DESC
    """, parameters).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_purchase_order(purchase_order_id):
    conn = get_connection()
    order = conn.execute("""
        SELECT o.*, s.name AS supplier, s.lead_time_days
        FROM purchase_orders o JOIN suppliers s ON s.id=o.supplier_id
        WHERE o.id=?
    """, (int(purchase_order_id),)).fetchone()
    items = conn.execute("""
        SELECT i.id, i.product_id, p.name AS product, i.ordered_quantity,
               i.received_quantity, i.ordered_quantity-i.received_quantity AS outstanding_quantity,
               i.unit_cost, i.ordered_quantity*i.unit_cost AS total_cost
        FROM purchase_order_items i JOIN products p ON p.id=i.product_id
        WHERE i.purchase_order_id=? ORDER BY i.id
    """, (int(purchase_order_id),)).fetchall()
    receipts = conn.execute("""
        SELECT id, reference_number, received_date, received_by
        FROM purchase_receipts WHERE purchase_order_id=? ORDER BY id
    """, (int(purchase_order_id),)).fetchall()
    conn.close()
    return ((dict(order), [dict(row) for row in items], [dict(row) for row in receipts])
            if order else (None, [], []))


def get_reorder_suggestions(period_days=30, safety_days=7, supplier_id=None):
    try:
        period_days, safety_days = int(period_days), int(safety_days)
    except (TypeError, ValueError) as error:
        raise ValueError("Sales period and safety stock must be whole numbers of days.") from error
    if period_days not in (7, 30, 60, 90):
        raise ValueError("Sales period must be 7, 30, 60, or 90 days.")
    if not 0 <= safety_days <= 365:
        raise ValueError("Safety stock days must be between 0 and 365.")
    start = (datetime.now().date() - timedelta(days=period_days - 1)).isoformat()
    conn = get_connection()
    selected_supplier_id = int(supplier_id) if supplier_id is not None else None
    parameters = [start, start, selected_supplier_id, selected_supplier_id]
    rows = conn.execute(f"""
        WITH sold AS (
            SELECT si.product_id, COALESCE(SUM(si.quantity), 0) AS quantity
            FROM sale_items si JOIN sales s ON s.id=si.sale_id
            WHERE date(s.sale_datetime) >= date(?) GROUP BY si.product_id
        ), returned AS (
            SELECT ri.product_id, COALESCE(SUM(ri.quantity), 0) AS quantity
            FROM return_items ri JOIN returns r ON r.id=ri.return_id
            WHERE date(r.return_datetime) >= date(?) GROUP BY ri.product_id
        ), stock AS (
            SELECT product_id, COALESCE(SUM(quantity), 0) AS quantity
            FROM batches WHERE quantity>0 AND date(expiry_date)>=date('now') GROUP BY product_id
        ), outstanding AS (
            SELECT i.product_id, COALESCE(SUM(i.ordered_quantity-i.received_quantity), 0) AS quantity
            FROM purchase_order_items i JOIN purchase_orders o ON o.id=i.purchase_order_id
            WHERE o.status IN ('pending','ordered','partially_received') GROUP BY i.product_id
        ), preferred AS (
            SELECT product_id, supplier_id AS preferred_supplier_id FROM (
                SELECT i.product_id, r.supplier_id,
                       ROW_NUMBER() OVER (PARTITION BY i.product_id ORDER BY r.received_date DESC, r.id DESC) AS rn
                FROM purchase_receipt_items i JOIN purchase_receipts r ON r.id=i.receipt_id
            ) WHERE rn=1
        ), costs AS (
            SELECT product_id, purchase_unit_cost FROM (
                SELECT product_id, purchase_unit_cost,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY id DESC) AS rn
                FROM batches
            ) WHERE rn=1
        ), supplier_costs AS (
            SELECT product_id, supplier_id, unit_cost FROM (
                SELECT i.product_id, r.supplier_id, i.unit_cost,
                       ROW_NUMBER() OVER (
                           PARTITION BY i.product_id, r.supplier_id
                           ORDER BY r.received_date DESC, r.id DESC, i.id DESC
                       ) AS rn
                FROM purchase_receipt_items i
                JOIN purchase_receipts r ON r.id=i.receipt_id
            ) WHERE rn=1
        )
        SELECT p.id AS product_id, p.name AS product, p.min_stock_level,
               MAX(0, COALESCE(sold.quantity,0)-COALESCE(returned.quantity,0)) AS units_sold,
               COALESCE(stock.quantity,0) AS usable_stock,
               COALESCE(outstanding.quantity,0) AS outstanding_order,
               sup.id AS preferred_supplier_id,
               sup.name AS supplier, COALESCE(sup.lead_time_days,7) AS lead_time_days,
               CASE WHEN ? IS NOT NULL
                    THEN COALESCE(supplier_costs.unit_cost,p.selling_price)
                    ELSE COALESCE(supplier_costs.unit_cost,costs.purchase_unit_cost,p.selling_price)
               END AS unit_cost
        FROM products p
        LEFT JOIN sold ON sold.product_id=p.id
        LEFT JOIN returned ON returned.product_id=p.id
        LEFT JOIN stock ON stock.product_id=p.id
        LEFT JOIN outstanding ON outstanding.product_id=p.id
        LEFT JOIN preferred ON preferred.product_id=p.id
        LEFT JOIN suppliers sup ON sup.id=COALESCE(?, preferred.preferred_supplier_id)
        LEFT JOIN supplier_costs
               ON supplier_costs.product_id=p.id AND supplier_costs.supplier_id=sup.id
        LEFT JOIN costs ON costs.product_id=p.id
        ORDER BY LOWER(p.name)
    """, parameters).fetchall()
    conn.close()
    suggestions = []
    for row in rows:
        sold = int(row["units_sold"] or 0)
        daily = sold / period_days
        lead = int(row["lead_time_days"] or 7)
        reorder_point = max(int(row["min_stock_level"] or 0),
                            int((Decimal(str(daily * (lead + safety_days)))).to_integral_value(rounding="ROUND_CEILING")))
        target = max(reorder_point, int((Decimal(str(daily * (lead + safety_days + period_days)))).to_integral_value(rounding="ROUND_CEILING")))
        available = int(row["usable_stock"] or 0)
        outstanding = int(row["outstanding_order"] or 0)
        suggested = max(0, target - available - outstanding)
        if sold == 0:
            movement = "No sales history"
        elif daily >= 1:
            movement = "Fast-moving"
        else:
            movement = "Slow-moving"
        suggestions.append({
            **dict(row), "period_days": period_days, "safety_days": safety_days,
            "average_daily_sales": round(daily, 2), "reorder_point": reorder_point,
            "target_stock": target, "suggested_quantity": suggested,
            "movement": movement,
            "explanation": (
                f"{sold} sold / {period_days} days; target {target}; "
                f"usable {available}; outstanding {outstanding}."
            ),
        })
    return suggestions


def create_order_from_recommendations(supplier_id, recommendations, order_date,
                                      expected_date, acting_username=None,
                                      acting_role=None):
    _require_purchase_admin(acting_role)
    items = []
    for recommendation in recommendations:
        quantity = int(recommendation.get("quantity") or 0)
        if quantity > 0:
            items.append({
                "product_id": recommendation.get("product_id"),
                "quantity": quantity,
                "unit_cost": recommendation.get("unit_cost"),
            })
    if not items:
        raise ValueError("Select at least one recommendation with a positive quantity.")
    return save_purchase_order(
        supplier_id, order_date, expected_date, items,
        notes="Created from replenishment recommendations", status="draft",
        acting_username=acting_username, acting_role=acting_role,
    )


def update_batch_record(batch_id, quantity, expiry_date, price, min_stock_level,
    reason="Batch details edited"):
    conn = get_connection(reason)
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
    conn = get_connection("Batch deleted")
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

def get_product_rows(search_text="", category="All Categories", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    search_value = f"%{search_text.strip().lower()}%"

    query = """
        SELECT
            p.id,
            p.name,
            p.dosage_form,
            p.barcode,
            p.selling_price,
            b.purchase_unit_cost,
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
          AND (? IN ('', 'All Categories') OR p.category = ?)
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
    """
    params = [search_value, category, category]
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend((max(0, int(limit)), max(0, int(offset))))
    cursor.execute(query, params)

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


def get_product_row_count(search_text="", category="All Categories"):
    conn = get_connection()
    search_value = f"%{search_text.strip().lower()}%"
    total = conn.execute("""
        SELECT COUNT(*) AS total FROM products p
        WHERE LOWER(p.name) LIKE ? AND (? IN ('', 'All Categories') OR p.category = ?)
    """, (search_value, category, category)).fetchone()["total"]
    conn.close()
    return int(total)


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
    conn = get_connection("Product and its batches deleted")
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
          AND (? IN ('', 'All Categories') OR p.category = ?)
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


def get_prescription_rows(search_text="", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    if search_text.strip():
        search_value = f"%{search_text.strip().lower()}%"
        query = """
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
        """
        params = [search_value, search_value, search_value]
    else:
        query = """
            SELECT
                id,
                customer_ssn,
                customer_name,
                medicine_name,
                amount,
                created_at
            FROM prescriptions
            ORDER BY id DESC
        """
        params = []
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend((max(0, int(limit)), max(0, int(offset))))
    cursor.execute(query, params)

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


def get_prescription_row_count(search_text=""):
    conn = get_connection()
    search_value = f"%{search_text.strip().lower()}%"
    total = conn.execute("""
        SELECT COUNT(*) AS total FROM prescriptions
        WHERE LOWER(customer_ssn) LIKE ? OR LOWER(customer_name) LIKE ? OR LOWER(medicine_name) LIKE ?
    """, (search_value, search_value, search_value)).fetchone()["total"]
    conn.close()
    return int(total)




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
        "receipt_number": format_receipt_number(sale["id"], sale["sale_datetime"]),
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
    conn = get_connection(f"Return against sale #{sale_id}")
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
    conn = get_connection(f"Reversed return #{return_id}")
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


def get_batch_rows(search_text="", category="All Categories", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    search_value = f"%{search_text.strip().lower()}%"

    query = """
        SELECT
            b.id AS batch_id,
            p.id AS product_id,
            p.name,
            p.category,
            p.selling_price,
            b.purchase_unit_cost,
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
          AND (? IN ('', 'All Categories') OR p.category = ?)
        ORDER BY LOWER(p.name), date(b.expiry_date), b.batch_number
    """
    params = [search_value, category, category]
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend((max(0, int(limit)), max(0, int(offset))))
    cursor.execute(query, params)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "batch_id": row["batch_id"],
            "product_id": row["product_id"],
            "name": row["name"],
            "category": row["category"] or "General",
            "price": row["selling_price"],
            "purchase_unit_cost": row["purchase_unit_cost"],
            "min_stock_level": row["min_stock_level"],
            "batch_number": row["batch_number"],
            "stock": row["quantity"],
            "expiry_date": row["expiry_date"],
            "expired": bool(row["expired"]),
        })

    conn.close()
    return rows


def get_batch_row_count(search_text="", category="All Categories"):
    conn = get_connection()
    search_value = f"%{search_text.strip().lower()}%"
    total = conn.execute("""
        SELECT COUNT(*) AS total FROM batches b JOIN products p ON p.id=b.product_id
        WHERE LOWER(p.name) LIKE ? AND (? IN ('', 'All Categories') OR p.category = ?)
    """, (search_value, category, category)).fetchone()["total"]
    conn.close()
    return int(total)


def get_fefo_allocations(product_id, requested_quantity, conn=None):
    owns_connection = conn is None
    conn = conn or get_connection()
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
    if owns_connection:
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


def preview_sale_allocations(cart_items, conn=None):
    owns_connection = conn is None
    conn = conn or get_connection()
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
            if owns_connection:
                conn.close()
            raise ValueError("Product not found.")

        allocations = get_fefo_allocations(
            item["product_id"], item["quantity"], conn=conn
        )
        if not allocations:
            if owns_connection:
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

    if owns_connection:
        conn.close()
    return plan, total_amount


def create_sale(
    cart_items,
    payment_method,
    cashier_id=1,
    acting_username=None,
    acting_role=None,
    customer_ssn=None,
    customer_name=None,
    performance_callback=None,
):
    conn = get_connection("POS checkout")

    try:
        # Reserve the database for this writer before checking stock.
        conn.execute("BEGIN IMMEDIATE")

        result = _create_sale_locked(
            conn,
            cart_items,
            payment_method,
            cashier_id,
            acting_username,
            acting_role,
            customer_ssn,
            customer_name,
            performance_callback,
        )

        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_sale_locked(
    conn,
    cart_items,
    payment_method,
    cashier_id=1,
    acting_username=None,
    acting_role=None,
    customer_ssn=None,
    customer_name=None,
    performance_callback=None,
    ):
    plan, total_amount = preview_sale_allocations(cart_items, conn=conn)

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

    inventory_deduction_ms = 0.0
    for item in plan:
        cursor.execute("""
            SELECT prescription_required
            FROM products
            WHERE id = ?
        """, (item["product_id"],))
        prescription_row = cursor.fetchone()

        if prescription_row and prescription_row["prescription_required"]:
            if not normalized_ssn or not normalized_name:
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

        inventory_started = time.perf_counter()
        for allocation in item["allocations"]:
            cursor.execute("""
                UPDATE batches
                SET quantity = quantity - ?
                WHERE id = ? AND quantity >= ?
            """, (
                allocation["quantity"],
                allocation["batch_id"],
                allocation["quantity"],
            ))
            if cursor.rowcount != 1:
                raise ValueError(
                    f"Stock changed while checking out {item['product_name']}. "
                    "Please review the cart and try again."
                )

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
        inventory_deduction_ms += (time.perf_counter() - inventory_started) * 1000

    if performance_callback is not None:
        performance_callback("inventory_deduction", inventory_deduction_ms)
    return plan, total_amount


def delete_sale_record(sale_id, acting_username=None, acting_role=None):
    conn = get_connection(f"Reversed sale #{sale_id}")
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
            sale_datetime,
            payment_method
        FROM sales
        ORDER BY id DESC
        LIMIT 5
    """)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "receipt_number": format_receipt_number(row["id"], row["sale_datetime"]),
            "total_amount": float(row["total_amount"] or 0),
            "sale_datetime": row["sale_datetime"],
            "payment_method": row["payment_method"] or "Cash",
        })

    conn.close()
    return rows


def get_sales_history(search_text="", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    search_text = search_text.strip()

    if search_text:
        numeric_receipt = parse_receipt_search(search_text)
        if numeric_receipt is None:
            conn.close()
            return []

        query = """
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
        """
        params = [numeric_receipt]

    else:
        query = """
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
        """
        params = []

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend((max(0, int(limit)), max(0, int(offset))))
    cursor.execute(query, params)


    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "items": row["total_items"],
            "date": row["sale_datetime"],
            "total": row["total_amount"],
            "payment_method": row["payment_method"] or "N/A",
            "receipt_number": format_receipt_number(row["id"], row["sale_datetime"]),
        })


    conn.close()
    return rows


def get_sales_history_count(search_text=""):
    conn = get_connection()
    if search_text.strip():
        receipt_id = parse_receipt_search(search_text)
        total = 0 if receipt_id is None else conn.execute(
            "SELECT COUNT(*) AS total FROM sales WHERE id=?", (receipt_id,)
        ).fetchone()["total"]
    else:
        total = conn.execute("SELECT COUNT(*) AS total FROM sales").fetchone()["total"]
    conn.close()
    return int(total)


def get_returns_history(search_text="", limit=None, offset=0):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_search = search_text.strip().lower().replace("#", "")
    numeric_search = parse_receipt_search(search_text)

    base_query = """
        SELECT
            r.id,
            r.sale_id,
            r.return_datetime,
            s.sale_datetime,
            r.total_amount,
            r.processed_by_username,
            COALESCE(SUM(ri.quantity), 0) AS total_items
        FROM returns r
        JOIN sales s ON s.id = r.sale_id
        LEFT JOIN return_items ri ON ri.return_id = r.id
    """

    if normalized_search:
        if numeric_search is not None:
            numeric_value = numeric_search
            query = base_query + """
                WHERE r.id = ?
                   OR r.sale_id = ?
                GROUP BY
                    r.id,
                    r.sale_id,
                    r.return_datetime,
                    s.sale_datetime,
                    r.total_amount,
                    r.processed_by_username
                ORDER BY r.id DESC
            """
            params = [numeric_value, numeric_value]
        else:
            query = base_query + """
                WHERE LOWER(COALESCE(r.processed_by_username, '')) LIKE ?
                GROUP BY
                    r.id,
                    r.sale_id,
                    r.return_datetime,
                    s.sale_datetime,
                    r.total_amount,
                    r.processed_by_username
                ORDER BY r.id DESC
            """
            params = [f"%{normalized_search}%"]
    else:
        query = base_query + """
            GROUP BY
                r.id,
                r.sale_id,
                r.return_datetime,
                s.sale_datetime,
                r.total_amount,
                r.processed_by_username
            ORDER BY r.id DESC
        """
        params = []

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend((max(0, int(limit)), max(0, int(offset))))
    cursor.execute(query, params)

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row["id"],
            "return_receipt_number": format_receipt_number(
                row["id"], row["return_datetime"], prefix="RT"
            ),
            "source_sale_id": row["sale_id"],
            "source_receipt_number": format_receipt_number(
                row["sale_id"], row["sale_datetime"]
            ),
            "date": row["return_datetime"] or "",
            "refund_amount": float(row["total_amount"] or 0),
            "total_items": int(row["total_items"] or 0),
            "processed_by": row["processed_by_username"] or "",
        })

    conn.close()
    return rows


def get_returns_history_count(search_text=""):
    conn = get_connection()
    normalized = search_text.strip().lower().replace("#", "")
    numeric = parse_receipt_search(search_text)
    if not normalized:
        total = conn.execute("SELECT COUNT(*) AS total FROM returns").fetchone()["total"]
    elif numeric is not None:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM returns WHERE id=? OR sale_id=?", (numeric, numeric)
        ).fetchone()["total"]
    else:
        total = conn.execute("""
            SELECT COUNT(*) AS total FROM returns
            WHERE LOWER(COALESCE(processed_by_username,'')) LIKE ?
        """, (f"%{normalized}%",)).fetchone()["total"]
    conn.close()
    return int(total)

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
        "receipt_number": format_receipt_number(sale["id"], sale["sale_datetime"]),
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
        "return_receipt_number": format_receipt_number(
            returned_sale["id"], returned_sale["return_datetime"], prefix="RT"
        ),
        "source_sale_id": returned_sale["sale_id"],
        "source_receipt_number": format_receipt_number(
            returned_sale["sale_id"], returned_sale["sale_datetime"]
        ),
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
