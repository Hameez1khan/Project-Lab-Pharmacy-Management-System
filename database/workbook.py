from contextlib import closing
from datetime import datetime
import json
import math
import secrets
import sqlite3

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from database.db import get_connection
from database.inventory_audit import bind, operator

LEGACY_TABLES = ("inventory_events", "users", "products", "batches", "sales",
                 "sale_items", "sale_batch_allocations", "returns", "return_items",
                 "return_batch_allocations", "prescriptions", "audit_logs")
V3_TABLES = ("inventory_events", "users", "suppliers", "products", "batches",
          "purchase_receipts", "purchase_receipt_items", "sales", "sale_items",
          "sale_batch_allocations", "returns", "return_items",
          "return_batch_allocations", "prescriptions", "audit_logs")
TABLES = ("inventory_events", "users", "suppliers", "products", "batches",
          "purchase_orders", "purchase_order_items", "purchase_receipts",
          "purchase_receipt_items", "sales", "sale_items", "sale_batch_allocations",
          "returns", "return_items", "return_batch_allocations", "prescriptions",
          "audit_logs")
KEYS = {"audit_logs": "transfer_key"}
UNIQUE = {"users": ("username",), "suppliers": ("name",),
          "products": ("name", "barcode"), "batches": ("batch_number",),
          "purchase_orders": ("order_number",),
          "purchase_receipts": ("reference_number",)}
LINKS = {
    "batches": {"product_id": "products"},
    "purchase_orders": {"supplier_id": "suppliers"},
    "purchase_order_items": {"purchase_order_id": "purchase_orders",
        "product_id": "products"},
    "purchase_receipts": {"supplier_id": "suppliers",
        "purchase_order_id": "purchase_orders"},
    "purchase_receipt_items": {"receipt_id": "purchase_receipts",
        "product_id": "products", "batch_id": "batches",
        "purchase_order_item_id": "purchase_order_items"},
    "sales": {"cashier_id": "users"},
    "sale_items": {"sale_id": "sales", "product_id": "products"},
    "sale_batch_allocations": {"sale_item_id": "sale_items", "batch_id": "batches"},
    "returns": {"sale_id": "sales"},
    "return_items": {"return_id": "returns", "sale_item_id": "sale_items",
                     "product_id": "products"},
    "return_batch_allocations": {"return_item_id": "return_items",
        "sale_batch_allocation_id": "sale_batch_allocations", "batch_id": "batches"},
    "prescriptions": {"sale_id": "sales", "product_id": "products"},
}
VERSION_V1 = "Pharmacy workbook v1"
VERSION_V2 = "Pharmacy workbook v2"
VERSION_V3 = "Pharmacy workbook v3"
VERSION_V4 = "Pharmacy workbook v4"
TECH_PREFIX = "_data_"
HEADER_FILL = PatternFill("solid", fgColor="2563EB")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def setup(c):
    c.execute("""CREATE TABLE IF NOT EXISTS transfer_origin(
        id INTEGER PRIMARY KEY CHECK(id=1), token TEXT NOT NULL)""")
    c.execute("INSERT OR IGNORE INTO transfer_origin VALUES(1,lower(hex(randomblob(16))))")
    if "transfer_key" not in [r[1] for r in c.execute("PRAGMA table_info(audit_logs)")]:
        c.execute("ALTER TABLE audit_logs ADD COLUMN transfer_key TEXT")
    c.execute("UPDATE audit_logs SET transfer_key=lower(hex(randomblob(16))) WHERE transfer_key IS NULL")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS audit_transfer_key ON audit_logs(transfer_key)")
    c.execute("""CREATE TRIGGER IF NOT EXISTS audit_assign_key AFTER INSERT ON audit_logs
        WHEN NEW.transfer_key IS NULL BEGIN
        UPDATE audit_logs SET transfer_key=lower(hex(randomblob(16))) WHERE id=NEW.id;
        END""")


def columns(c, table):
    omit = {"users": {"password"}, "audit_logs": {"id"}}.get(table, set())
    return {r[1]: r[2].upper() for r in c.execute(f"PRAGMA table_info({table})")
            if r[1] not in omit}


def put(ws, values):
    ws.append(list(values))


def encode(value):
    """Preserve text exactly through Excel, including empty strings."""
    return "''" + value if isinstance(value, str) else value


def _display_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    return text


def _business_sheet(book, title, headers, rows, currency_columns=(), date_columns=()):
    ws = book.create_sheet(title)
    ws.sheet_view.showGridLines = False
    put(ws, headers)
    for row in rows:
        put(ws, row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 24
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for column in currency_columns:
        for cell in ws[column][1:]:
            cell.number_format = '#,##0.00 "Ft"'
    for column in date_columns:
        for cell in ws[column][1:]:
            if isinstance(cell.value, datetime):
                cell.number_format = "yyyy-mm-dd hh:mm"
    sample_end = min(ws.max_row, 501)
    for index in range(1, ws.max_column + 1):
        column = ws.iter_rows(
            min_row=1, max_row=sample_end, min_col=index, max_col=index
        )
        width = max(
            (
                len(str(row[0].value)) if row[0].value is not None else 0
                for row in column
            ),
            default=0,
        )
        ws.column_dimensions[get_column_letter(index)].width = min(max(width + 3, 11), 42)
    return ws


def _add_visible_sheets(book, c):
    overview = book.active
    overview.title = "Overview"
    overview.sheet_view.showGridLines = False
    overview.append(["Khalis Dawa - Pharmacy Data Export"])
    overview["A1"].font = Font(size=18, bold=True, color="1E3A8A")
    overview.append(["Generated", datetime.now()])
    overview["B2"].number_format = "yyyy-mm-dd hh:mm"
    overview.append([])
    overview.append(["Section", "Records"])
    for cell in overview[4]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for label, table in (("Products", "products"), ("Batches", "batches"),
                         ("Suppliers", "suppliers"), ("Purchase orders", "purchase_orders"),
                         ("Purchases", "purchase_receipts"),
                         ("Sales", "sales"), ("Returns", "returns"),
                         ("Prescriptions", "prescriptions")):
        overview.append([label, c.execute(f"SELECT count(*) FROM {table}").fetchone()[0]])
    overview.column_dimensions["A"].width = 32
    overview.column_dimensions["B"].width = 22

    products = c.execute("""SELECT name,dosage_form,barcode,purchase_cost,selling_price,min_stock_level,
        category,manufacturer,prescription_required FROM products ORDER BY lower(name)""")
    _business_sheet(book, "Products", (
        "No.", "Product", "Form", "Barcode", "Purchase cost", "Selling price",
        "Minimum stock", "Category", "Manufacturer", "Prescription",
    ),
        ((n, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], "Yes" if r[8] else "No")
         for n, r in enumerate(products, 1)), currency_columns=("E", "F"))

    inventory = c.execute("""SELECT p.name,b.batch_number,b.expiry_date,b.quantity,
        b.purchase_unit_cost,b.total_purchase_cost,b.discount_percent
        FROM batches b JOIN products p ON p.id=b.product_id
        ORDER BY lower(p.name),date(b.expiry_date),b.batch_number""")
    today = datetime.now().date()
    inventory_rows = []
    for n, r in enumerate(inventory, 1):
        expiry = _display_datetime(r[2])
        status = "Check date"
        if isinstance(expiry, datetime):
            status = "Expired" if expiry.date() < today else "Available"
        inventory_rows.append((n, r[0], r[1], expiry, r[3], r[4], r[5], r[6], status))
    _business_sheet(book, "Inventory", ("No.", "Product", "Batch", "Expiry", "Quantity",
        "Unit cost", "Stock cost", "Discount %", "Status"), inventory_rows,
        currency_columns=("F", "G"), date_columns=("D",))

    suppliers = c.execute("""SELECT name,contact_person,phone,email,address,lead_time_days,created_at
        FROM suppliers ORDER BY lower(name)""")
    _business_sheet(book, "Suppliers", ("No.", "Supplier", "Contact", "Phone", "Email",
        "Address", "Lead time (days)", "Created"),
        ((n, r[0], r[1], r[2], r[3], r[4], r[5], _display_datetime(r[6]))
         for n, r in enumerate(suppliers, 1)), date_columns=("H",))

    orders = c.execute("""SELECT o.id,o.order_number,s.name,o.order_date,o.expected_date,
        o.status,sum(i.ordered_quantity),sum(i.received_quantity),
        sum(i.ordered_quantity*i.unit_cost),o.created_by,o.notes
        FROM purchase_orders o JOIN suppliers s ON s.id=o.supplier_id
        JOIN purchase_order_items i ON i.purchase_order_id=o.id
        GROUP BY o.id ORDER BY o.order_date,o.id""")
    _business_sheet(book, "Purchase Orders", ("No.", "Order", "Supplier", "Order date",
        "Expected", "Status", "Ordered units", "Received units", "Total cost",
        "Created by", "Notes"),
        ((n, r[1], r[2], _display_datetime(r[3]), _display_datetime(r[4]), r[5],
          r[6], r[7], r[8], r[9], r[10]) for n, r in enumerate(orders, 1)),
        currency_columns=("I",), date_columns=("D", "E"))

    order_items = c.execute("""SELECT o.order_number,p.name,i.ordered_quantity,
        i.received_quantity,i.ordered_quantity-i.received_quantity,i.unit_cost,
        i.ordered_quantity*i.unit_cost
        FROM purchase_order_items i JOIN purchase_orders o ON o.id=i.purchase_order_id
        JOIN products p ON p.id=i.product_id ORDER BY o.id,i.id""")
    _business_sheet(book, "Order Items", ("No.", "Order", "Product", "Ordered",
        "Received", "Outstanding", "Unit cost", "Line total"),
        ((n, *r) for n, r in enumerate(order_items, 1)),
        currency_columns=("G", "H"))

    purchases = c.execute("""SELECT r.id,r.reference_number,r.received_date,s.name,
        count(i.id),coalesce(sum(i.quantity),0),coalesce(sum(i.total_cost),0),
        r.received_by,r.notes
        FROM purchase_receipts r JOIN suppliers s ON s.id=r.supplier_id
        LEFT JOIN purchase_receipt_items i ON i.receipt_id=r.id
        GROUP BY r.id ORDER BY r.received_date,r.id""")
    _business_sheet(book, "Purchases", ("No.", "Receipt", "Reference", "Received",
        "Supplier", "Line items", "Units", "Total cost", "Received by", "Notes"),
        ((n, f"P-{r[0]:05d}", r[1], _display_datetime(r[2]), r[3], r[4], r[5],
          r[6], r[7], r[8]) for n, r in enumerate(purchases, 1)),
        currency_columns=("H",), date_columns=("D",))

    purchase_items = c.execute("""SELECT r.id,r.reference_number,p.name,i.batch_number,
        i.expiry_date,i.quantity,i.unit_cost,i.total_cost
        FROM purchase_receipt_items i
        JOIN purchase_receipts r ON r.id=i.receipt_id
        JOIN products p ON p.id=i.product_id ORDER BY r.id,i.id""")
    _business_sheet(book, "Purchase Items", ("No.", "Receipt", "Reference", "Product",
        "Batch", "Expiry", "Quantity", "Unit cost", "Total cost"),
        ((n, f"P-{r[0]:05d}", r[1], r[2], r[3], _display_datetime(r[4]),
          r[5], r[6], r[7]) for n, r in enumerate(purchase_items, 1)),
        currency_columns=("H", "I"), date_columns=("F",))

    sales = c.execute("""SELECT s.id,s.sale_datetime,s.payment_method,count(i.id),s.total_amount
        FROM sales s LEFT JOIN sale_items i ON i.sale_id=s.id GROUP BY s.id ORDER BY s.id""")
    _business_sheet(book, "Sales", ("No.", "Receipt", "Date", "Payment", "Line items", "Total"),
        ((n, f"#{r[0]:05d}", _display_datetime(r[1]), r[2] or "Unknown", r[3], r[4])
         for n, r in enumerate(sales, 1)), currency_columns=("F",), date_columns=("C",))

    items = c.execute("""SELECT i.sale_id,i.product_name,i.quantity,i.unit_price,i.subtotal,
        group_concat(a.batch_number || ' x' || a.quantity, ', ')
        FROM sale_items i LEFT JOIN sale_batch_allocations a ON a.sale_item_id=i.id
        GROUP BY i.id ORDER BY i.sale_id,i.id""")
    _business_sheet(book, "Sale Items", ("No.", "Receipt", "Product", "Quantity",
        "Unit price", "Subtotal", "Batches"),
        ((n, f"#{r[0]:05d}", r[1], r[2], r[3], r[4], r[5] or "")
         for n, r in enumerate(items, 1)), currency_columns=("E", "F"))

    returns = c.execute("""SELECT id,sale_id,return_datetime,processed_by_username,
        processed_by_role,total_amount FROM returns ORDER BY id""")
    _business_sheet(book, "Returns", ("No.", "Return", "Source receipt", "Date",
        "Processed by", "Role", "Refund"),
        ((n, f"#{r[0]:05d}", f"#{r[1]:05d}", _display_datetime(r[2]), r[3], r[4], r[5])
         for n, r in enumerate(returns, 1)), currency_columns=("G",), date_columns=("D",))

    prescriptions = c.execute("""SELECT customer_ssn,customer_name,medicine_name,amount,
        created_at,sale_id FROM prescriptions ORDER BY id""")
    _business_sheet(book, "Prescriptions", ("No.", "Customer SSN", "Customer", "Medicine",
        "Quantity", "Date", "Receipt"),
        ((n, r[0], r[1], r[2], r[3], _display_datetime(r[4]),
          f"#{r[5]:05d}" if r[5] else "") for n, r in enumerate(prescriptions, 1)),
        date_columns=("F",))

    audits = c.execute("""
        SELECT username,role,description,created_at FROM (
            SELECT id,username,role,description,created_at
            FROM audit_logs ORDER BY id DESC LIMIT 5000
        ) ORDER BY created_at,id
    """)
    _business_sheet(book, "Audit History", ("No.", "User", "Role", "Action", "Date"),
        ((n, r[0], r[1], r[2], _display_datetime(r[3])) for n, r in enumerate(audits, 1)),
        date_columns=("E",))

    changes = []
    for n, row in enumerate(c.execute("""
            SELECT actor,role,entity,record_id,action,old_state,new_state,reason,created_at
            FROM (
                SELECT id,actor,role,entity,record_id,action,old_state,new_state,reason,created_at
                FROM inventory_events ORDER BY created_at DESC,id DESC LIMIT 5000
            ) ORDER BY created_at,id
        """), 1):
        before = json.loads(row[5] or "{}")
        after = json.loads(row[6] or "{}")
        state = after or before
        record = state.get("name") or state.get("batch_number") or row[3]
        quantity_change = ""
        if before.get("quantity") != after.get("quantity"):
            quantity_change = f"{before.get('quantity', '-')} to {after.get('quantity', '-')}"
        changes.append((n, row[0], row[1], row[2].title(), record,
                        row[4].title(), quantity_change, row[7], _display_datetime(row[8])))
    _business_sheet(book, "Inventory Changes", ("No.", "User", "Role", "Record type",
        "Record", "Action", "Quantity change", "Reason", "Date"), changes,
        date_columns=("I",))


def export_book(path):
    if operator.get()[1].lower() != "admin":
        raise PermissionError("Administrator access required.")
    book = Workbook()
    with closing(get_connection()) as c:
        c.execute("BEGIN")
        token = c.execute("SELECT token FROM transfer_origin WHERE id=1").fetchone()[0]
        _add_visible_sheets(book, c)
        meta = book.create_sheet("Manifest")
        put(meta, (VERSION_V4, token))
        for table in TABLES:
            cols = columns(c, table)
            ws = book.create_sheet(TECH_PREFIX + table)
            put(ws, cols)
            ws.freeze_panes = "A2"
            for row in c.execute(f"SELECT {','.join(cols)} FROM {table}"):
                put(ws, (encode(value) for value in row))
            seq = c.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (table,)).fetchone()
            put(meta, (table, ws.max_row - 1, int(seq[0]) if seq else 0))
            ws.sheet_state = "hidden"
        meta.sheet_state = "hidden"
    book.save(path)


def decode(cell, kind):
    value = cell.value
    if cell.data_type == "f":
        raise ValueError("Formulas are not allowed in a data workbook.")
    if value is None:
        return None
    if kind == "INTEGER":
        if isinstance(value, bool) or isinstance(value, float) and not value.is_integer():
            raise ValueError("Expected a whole number.")
        return int(value)
    if kind == "REAL":
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Expected a finite amount.")
        return value
    if not isinstance(value, str):
        raise ValueError("Use text for dates, codes and names.")
    return value[2:] if value.startswith("''") else value


def read_rows(c, book):
    if "Manifest" not in book.sheetnames:
        raise ValueError("Missing workbook manifest.")
    meta = list(book["Manifest"].values)
    if not meta or meta[0][0] not in (VERSION_V1, VERSION_V2, VERSION_V3, VERSION_V4) or not meta[0][1]:
        raise ValueError("Not a pharmacy data workbook.")
    version = meta[0][0]
    if version == VERSION_V4:
        workbook_tables = TABLES
    elif version == VERSION_V3:
        workbook_tables = V3_TABLES
    else:
        workbook_tables = LEGACY_TABLES
    prefix = "" if version == VERSION_V1 else TECH_PREFIX
    required = {prefix + table for table in workbook_tables}
    if not required.issubset(book.sheetnames):
        raise ValueError("The workbook is missing required data worksheets.")
    if version == VERSION_V1 and set(book.sheetnames) != {"Manifest", *workbook_tables}:
        raise ValueError("Missing or unexpected worksheet.")
    counts = {table: (int(count), int(seq)) for table, count, seq in meta[1:]}
    if set(counts) != set(workbook_tables):
        raise ValueError("Invalid manifest.")
    data = {}
    for table in workbook_tables:
        available_kinds = columns(c, table)
        rows = iter(book[prefix + table].rows)
        header = [cell.value for cell in next(rows, ())]
        if (not header or len(header) != len(set(header))
                or not set(header).issubset(available_kinds)
                or version == VERSION_V4 and set(header) != set(available_kinds)):
            raise ValueError(f"{table}: unexpected columns.")
        kinds = {name: available_kinds[name] for name in header}
        key = KEYS.get(table, "id")
        data[table] = {}
        for number, row in enumerate(rows, 2):
            try:
                values = {name: decode(cell, kinds[name]) for name, cell in zip(header, row)}
                identifier = values[key]
                if (identifier is None or identifier in data[table]
                        or isinstance(identifier, int) and identifier < 1):
                    raise ValueError("Missing, invalid or repeated record ID.")
                if "quantity" in values and (values["quantity"] is None or values["quantity"] < 0):
                    raise ValueError("Invalid quantity.")
                if table == "users" and values["role"] not in ("admin", "pharmacist", "doctor"):
                    raise ValueError("Unexpected account role.")
                if table == "inventory_events":
                    for field in ("old_state", "new_state"):
                        if values[field] is not None and not isinstance(json.loads(values[field]), dict):
                            raise ValueError("Invalid audit snapshot.")
                data[table][identifier] = values
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError(f"{table}, Excel row {number}: {error}") from error
        if len(data[table]) != counts[table][0]:
            raise ValueError(f"{table}: row count differs from the manifest.")
    return meta[0][1], counts, data


def import_book(path):
    if operator.get()[1].lower() != "admin":
        raise PermissionError("Administrator access required.")
    added = skipped = 0
    with closing(load_workbook(path, read_only=True, data_only=False)) as book, \
            closing(get_connection("Excel merge")) as c:
        with c:
            c.execute("BEGIN IMMEDIATE")
            origin, counts, data = read_rows(c, book)
            local = c.execute("SELECT token FROM transfer_origin WHERE id=1").fetchone()[0]
            if origin != local:
                if any(c.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                       for table in ("sales", "returns")) and (data["sales"] or data["returns"]):
                    raise ValueError("Separate sales histories cannot safely be matched by receipt number.")
                if not any(c.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                           for table in ("products", "batches", "sales", "returns")):
                    c.execute("UPDATE transfer_origin SET token=? WHERE id=1", (origin,))

            for table in data:
                if table == "inventory_events":
                    c.execute("DROP TRIGGER IF EXISTS temp.inv_stamp")
                key = KEYS.get(table, "id")
                for identifier, values in data[table].items():
                    for field, parent in LINKS.get(table, {}).items():
                        if field not in values:
                            continue
                        reference = values[field]
                        if reference is None or reference in data[parent]:
                            continue
                        historical = parent in ("products", "batches") and table != "batches"
                        if not historical or c.execute(
                            f"SELECT 1 FROM {parent} WHERE id=?", (reference,)
                        ).fetchone():
                            raise ValueError(
                                f"{table} #{identifier}: unresolved or ambiguous {field}={reference}."
                            )

                    names = ",".join(values)
                    existing = c.execute(
                        f"SELECT {names} FROM {table} WHERE {key}=?", (identifier,)
                    ).fetchone()
                    if existing:
                        if dict(existing) != values:
                            raise ValueError(
                                f"{table} #{identifier}: same identifier, different data. Nothing imported."
                            )
                        skipped += 1
                        continue

                    for unique_name in UNIQUE.get(table, ()):
                        if values[unique_name] and c.execute(
                            f"SELECT 1 FROM {table} WHERE {unique_name}=? COLLATE NOCASE",
                            (values[unique_name],)
                        ).fetchone():
                            raise ValueError(
                                f"{table} #{identifier}: {unique_name} already belongs to another record."
                            )

                    insert_values = list(values.values())
                    if table == "users":
                        from database.db import hash_password
                        names += ",password"
                        insert_values.append(hash_password(secrets.token_urlsafe(32)))
                    try:
                        marks = ",".join("?" for _ in insert_values)
                        c.execute(f"INSERT INTO {table}({names}) VALUES({marks})", insert_values)
                    except sqlite3.IntegrityError as error:
                        raise ValueError(f"{table} #{identifier}: {error}") from error
                    added += 1

                if table == "inventory_events":
                    bind(c, "Excel merge")
                sequence = counts[table][1]
                if sequence > 0 and table not in ("inventory_events", "audit_logs"):
                    if not c.execute(
                        "UPDATE sqlite_sequence SET seq=max(seq,?) WHERE name=?", (sequence, table)
                    ).rowcount:
                        c.execute("INSERT INTO sqlite_sequence(name,seq) VALUES(?,?)", (table, sequence))
    return added, skipped
