from contextvars import ContextVar
import json

operator = ContextVar("operator", default=("System", ""))
fields = {
    "products": "id name dosage_form barcode selling_price min_stock_level category manufacturer prescription_required",
    "batches": "id product_id batch_number expiry_date quantity purchase_unit_cost total_purchase_cost discount_percent discount_applied_date",
}


def install(c):
    c.execute("""CREATE TABLE IF NOT EXISTS inventory_events (
        id TEXT PRIMARY KEY, entity TEXT NOT NULL, record_id INTEGER NOT NULL,
        action TEXT NOT NULL, old_state TEXT, new_state TEXT,
        actor TEXT NOT NULL DEFAULT 'System', role TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT 'Database change',
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now','localtime'))
    )""")
    for table, names in fields.items():
        def snapshot(prefix):
            pairs = ", ".join(f"'{n}', {prefix}.{n}" for n in names.split())
            return f"json_object({pairs})"

        for action in ("INSERT", "UPDATE", "DELETE"):
            old = "NULL" if action == "INSERT" else snapshot("OLD")
            new = "NULL" if action == "DELETE" else snapshot("NEW")
            key = "OLD.id" if action == "DELETE" else "NEW.id"
            guard = f"WHEN {old} IS NOT {new}" if action == "UPDATE" else ""
            c.execute(f"""CREATE TRIGGER IF NOT EXISTS inv_v1_{table}_{action}
                AFTER {action} ON {table} {guard} BEGIN
                INSERT INTO inventory_events(id,entity,record_id,action,old_state,new_state)
                VALUES(lower(hex(randomblob(16))),'{table}',{key},'{action}',{old},{new});
                END""")


def bind(c, reason):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='inventory_events'").fetchone():
        return
    actor, role = operator.get()
    c.create_function("inv_actor", 0, lambda: actor)
    c.create_function("inv_role", 0, lambda: role)
    c.create_function("inv_reason", 0, lambda: reason)
    c.execute("""CREATE TEMP TRIGGER inv_stamp AFTER INSERT ON main.inventory_events
        BEGIN UPDATE inventory_events SET actor=inv_actor(), role=inv_role(),
        reason=inv_reason() WHERE id=NEW.id; END""")


def history(c, search):
    rows = []
    for r in c.execute("SELECT * FROM inventory_events"):
        old = json.loads(r["old_state"] or "{}")
        new = json.loads(r["new_state"] or "{}")
        item = new or old
        name = item.get("batch_number") or item.get("name") or str(r["record_id"])
        summary = f"{r['action'].title()} {name}: {r['reason']}"
        if old.get("quantity") != new.get("quantity"):
            summary += f" ({old.get('quantity', '-')} -> {new.get('quantity', '-')} units)"
        if search.casefold() not in " ".join((summary, r["actor"], r["role"])).casefold():
            continue
        details = json.dumps({"before": old or None, "after": new or None},
                             indent=2, ensure_ascii=False)
        rows.append(dict(id=r["id"], username=r["actor"], role=r["role"],
                         description=summary, created_at=r["created_at"], details=details))
    return rows