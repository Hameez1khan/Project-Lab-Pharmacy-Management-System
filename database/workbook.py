from contextlib import closing
import json
import math
import secrets
import sqlite3

from openpyxl import Workbook, load_workbook
from database.db import get_connection
from database.inventory_audit import bind, operator

TABLES = ("inventory_events", "users", "products", "batches", "sales", "sale_items",
          "sale_batch_allocations", "returns", "return_items",
          "return_batch_allocations", "prescriptions", "audit_logs")
KEYS = {"audit_logs": "transfer_key"}
UNIQUE = {"users": ("username",), "products": ("name", "barcode"),
          "batches": ("batch_number",)}
LINKS = {
    "batches": {"product_id": "products"},
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


def columns(c, t):
    omit = {"users": {"password"}, "audit_logs": {"id"}}.get(t, set())
    return {r[1]: r[2].upper() for r in c.execute(f"PRAGMA table_info({t})")
            if r[1] not in omit}


def put(ws, values):
    ws.append(list(values))
    for cell in ws[ws.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def export_book(path):
    if operator.get()[1].lower() != "admin":
        raise PermissionError("Administrator access required.")
    book = Workbook()
    meta = book.active
    meta.title = "Manifest"
    with closing(get_connection()) as c:
        c.execute("BEGIN")
        token = c.execute("SELECT token FROM transfer_origin WHERE id=1").fetchone()[0]
        put(meta, ("Pharmacy workbook v1", token))
        for t in TABLES:
            cols = columns(c, t)
            ws = book.create_sheet(t)
            put(ws, cols)
            ws.freeze_panes = "A2"
            for row in c.execute(f"SELECT {','.join(cols)} FROM {t}"):
                put(ws, [None if v is None else "''" + v if isinstance(v, str)
                         and (not v or v.startswith("'")) else str(v) for v in row])
            seq = c.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (t,)).fetchone()
            put(meta, (t, ws.max_row - 1, int(seq[0]) if seq else 0))
    book.save(path)

def decode(cell, kind):
    v = cell.value
    if cell.data_type == "f":
        raise ValueError("Formulas are not allowed in a data workbook.")
    if v is None:
        return None
    if kind == "INTEGER":
        if isinstance(v, bool) or isinstance(v, float) and not v.is_integer():
            raise ValueError("Expected a whole number.")
        return int(v)
    if kind == "REAL":
        v = float(v)
        if not math.isfinite(v):
            raise ValueError("Expected a finite amount.")
        return v
    if not isinstance(v, str):
        raise ValueError("Use text for dates, codes and names.")
    return v[2:] if v.startswith("''") else v


def read_rows(c, book):
    if set(book.sheetnames) != {"Manifest", *TABLES}:
        raise ValueError("Missing or unexpected worksheet.")
    meta = list(book["Manifest"].values)
    if not meta or meta[0][0] != "Pharmacy workbook v1" or not meta[0][1]:
        raise ValueError("Not a pharmacy data workbook.")
    counts = {t: (int(n), int(seq)) for t, n, seq in meta[1:]}
    if set(counts) != set(TABLES):
        raise ValueError("Invalid manifest.")
    data = {}
    for t in TABLES:
        kinds = columns(c, t)
        rows = iter(book[t].rows)
        header = [cell.value for cell in next(rows, ())]
        if len(header) != len(kinds) or set(header) != set(kinds):
            raise ValueError(f"{t}: unexpected columns.")
        key = KEYS.get(t, "id")
        data[t] = {}
        for n, row in enumerate(rows, 2):
            try:
                d = {k: decode(cell, kinds[k]) for k, cell in zip(header, row)}
                i = d[key]
                if i is None or i in data[t] or isinstance(i, int) and i < 1:
                    raise ValueError("Missing, invalid or repeated record ID.")
                if "quantity" in d and (d["quantity"] is None or d["quantity"] < 0):
                    raise ValueError("Invalid quantity.")
                if t == "users" and d["role"] not in ("admin", "pharmacist", "doctor"):
                    raise ValueError("Unexpected account role.")
                if t == "inventory_events":
                    for field in ("old_state", "new_state"):
                        if d[field] is not None and not isinstance(json.loads(d[field]), dict):
                            raise ValueError("Invalid audit snapshot.")
                data[t][i] = d
            except (ValueError, TypeError, OverflowError) as e:
                raise ValueError(f"{t}, Excel row {n}: {e}") from e
        if len(data[t]) != counts[t][0]:
            raise ValueError(f"{t}: row count differs from the manifest.")
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
                if any(c.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
                       for t in ("sales", "returns")) and (data["sales"] or data["returns"]):
                    raise ValueError("Separate sales histories cannot safely be matched by receipt number.")
                if not any(c.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
                           for t in ("products", "batches", "sales", "returns")):
                    c.execute("UPDATE transfer_origin SET token=? WHERE id=1", (origin,))

            for t in TABLES:
                if t == "inventory_events":
                    c.execute("DROP TRIGGER IF EXISTS temp.inv_stamp")
                key = KEYS.get(t, "id")
                for i, d in data[t].items():
                    for field, parent in LINKS.get(t, {}).items():
                        ref = d[field]
                        if ref is None or ref in data[parent]:
                            continue
                        historical = parent in ("products", "batches") and t != "batches"
                        if not historical or c.execute(
                            f"SELECT 1 FROM {parent} WHERE id=?", (ref,)
                        ).fetchone():
                            raise ValueError(f"{t} #{i}: unresolved or ambiguous {field}={ref}.")

                    cols = ",".join(d)
                    existing = c.execute(
                        f"SELECT {cols} FROM {t} WHERE {key}=?", (i,)
                    ).fetchone()
                    if existing:
                        if dict(existing) != d:
                            raise ValueError(f"{t} #{i}: same identifier, different data. Nothing imported.")
                        skipped += 1
                        continue

                    for k in UNIQUE.get(t, ()):
                        if d[k] and c.execute(
                            f"SELECT 1 FROM {t} WHERE {k}=? COLLATE NOCASE", (d[k],)
                        ).fetchone():
                            raise ValueError(f"{t} #{i}: {k} already belongs to another record.")

                    values = list(d.values())
                    if t == "users":
                        cols += ",password"
                        values.append(secrets.token_urlsafe(48))
                    try:
                        marks = ",".join("?" for _ in values)
                        c.execute(f"INSERT INTO {t}({cols}) VALUES({marks})", values)
                    except sqlite3.IntegrityError as e:
                        raise ValueError(f"{t} #{i}: {e}") from e
                    added += 1

                if t == "inventory_events":
                    bind(c, "Excel merge")
                seq = counts[t][1]
                if seq > 0 and t not in ("inventory_events", "audit_logs"):
                    if not c.execute(
                        "UPDATE sqlite_sequence SET seq=max(seq,?) WHERE name=?", (seq, t)
                    ).rowcount:
                        c.execute("INSERT INTO sqlite_sequence(name,seq) VALUES(?,?)", (t, seq))
    return added, skipped