from datetime import datetime
from contextlib import closing

from database.db import (
    authenticate_user,
    change_user_password,
    create_sale,
    get_connection,
    get_dashboard_sales_trend,
    get_batch_row_count,
    get_batch_rows,
    get_product_row_count,
    get_product_rows,
    get_products_for_pos,
    is_password_hash,
    process_sale_return,
    register_pharmacist,
)
from database.reporting import report_data
from tests.backend.base import DatabaseTestCase


class DatabaseBehaviorTests(DatabaseTestCase):
    def test_empty_category_value_means_all_categories(self):
        product = self.add_product("Visible Medicine")
        self.add_batch(product, "VISIBLE-001", 12)

        self.assertEqual(get_product_row_count("", ""), 1)
        self.assertEqual(len(get_product_rows("", "", 25, 0)), 1)
        self.assertEqual(get_batch_row_count("", ""), 1)
        self.assertEqual(len(get_batch_rows("", "", 25, 0)), 1)
        self.assertEqual(len(get_products_for_pos("", "")), 1)

    def test_connection_enforces_foreign_keys(self):
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_legacy_password_upgrades_and_password_changes_are_hashed(self):
        with closing(get_connection()) as conn, conn:
            conn.execute("UPDATE users SET password='1234' WHERE username='admin'")
        self.assertIsNotNone(authenticate_user("admin", "1234"))
        with closing(get_connection()) as conn:
            stored = conn.execute(
                "SELECT password FROM users WHERE username='admin'"
            ).fetchone()[0]
        self.assertTrue(is_password_hash(stored))

        success, _ = register_pharmacist("pharma", "secret")
        self.assertTrue(success)
        self.assertIsNotNone(authenticate_user("pharma", "secret"))
        success, _ = change_user_password("pharma", "secret", "changed")
        self.assertTrue(success)
        self.assertIsNone(authenticate_user("pharma", "secret"))
        self.assertIsNotNone(authenticate_user("pharma", "changed"))

    def test_fefo_sale_partially_consumes_two_batches(self):
        product = self.add_product()
        first = self.add_batch(product, "EARLY", 2, "2099-01-01")
        second = self.add_batch(product, "LATE", 5, "2099-06-01")
        plan, total = create_sale([{"product_id": product, "quantity": 4}], "Cash")
        self.assertEqual(total, 400)
        self.assertEqual([a["quantity"] for a in plan[0]["allocations"]], [2, 2])
        with closing(get_connection()) as conn:
            quantities = dict(conn.execute("SELECT id,quantity FROM batches"))
            allocations = list(conn.execute(
                "SELECT batch_number,quantity FROM sale_batch_allocations ORDER BY id"
            ))
        self.assertEqual(quantities, {first: 0, second: 3})
        self.assertEqual([(r[0], r[1]) for r in allocations], [("EARLY", 2), ("LATE", 2)])

    def test_insufficient_stock_rolls_back_every_sale_record(self):
        product = self.add_product()
        self.add_batch(product, "ONLY", 1)
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            create_sale([{"product_id": product, "quantity": 2}], "Cash")
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM sales").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT quantity FROM batches").fetchone()[0], 1)

    def test_return_restores_original_batch_and_creates_audit_snapshot(self):
        product = self.add_product()
        batch = self.add_batch(product, "RETURN", 5)
        create_sale(
            [{"product_id": product, "quantity": 2}], "Card",
            acting_username="admin", acting_role="admin"
        )
        with closing(get_connection()) as conn:
            sale_id = conn.execute("SELECT id FROM sales").fetchone()[0]
            item_id = conn.execute("SELECT id FROM sale_items").fetchone()[0]
        success, _ = process_sale_return(
            sale_id, [{"sale_item_id": item_id, "quantity": 1}], "admin", "admin"
        )
        self.assertTrue(success)
        with closing(get_connection()) as conn:
            self.assertEqual(
                conn.execute("SELECT quantity FROM batches WHERE id=?", (batch,)).fetchone()[0], 4
            )
            snapshots = conn.execute(
                "SELECT old_state,new_state FROM inventory_events WHERE entity='batches'"
            ).fetchall()
        self.assertGreaterEqual(len(snapshots), 3)
        self.assertTrue(any(row[0] and row[1] for row in snapshots))

    def test_reporting_subtracts_returns_and_calculates_demand_reorder(self):
        fast = self.add_product("Fast", 100, minimum=2)
        slow = self.add_product("Slow", 50, minimum=8)
        self.add_batch(fast, "FAST", 20)
        self.add_batch(slow, "SLOW", 1)
        create_sale([{"product_id": fast, "quantity": 6}], "Cash")
        with closing(get_connection()) as conn:
            sale_id = conn.execute("SELECT id FROM sales").fetchone()[0]
            item_id = conn.execute("SELECT id FROM sale_items").fetchone()[0]
        process_sale_return(sale_id, [{"sale_item_id": item_id, "quantity": 2}])
        today = datetime.now().date().isoformat()
        reports = report_data(today, today)
        product_cols, product_rows = reports["Products"]
        fast_row = dict(zip(product_cols, next(r for r in product_rows if r[0] == "Fast")))
        self.assertEqual(fast_row["Net units"], 4)
        self.assertEqual(fast_row["Net (Ft)"], 400)
        reorder_cols, reorder_rows = reports["Low stock now"]
        slow_row = dict(zip(reorder_cols, next(r for r in reorder_rows if r[0] == "Slow")))
        self.assertEqual(slow_row["Suggested order (units)"], 7)
        fast_cols, fast_rows = reports["Fast movers"]
        self.assertEqual(dict(zip(fast_cols, fast_rows[0]))["Product"], "Fast")
        slow_cols, slow_rows = reports["Slow movers"]
        self.assertEqual(dict(zip(slow_cols, slow_rows[0]))["Product"], "Slow")

    def test_dashboard_trend_is_zero_filled_and_uses_refunds(self):
        product = self.add_product(price=100)
        self.add_batch(product, "TREND", 10)
        create_sale([{"product_id": product, "quantity": 3}], "Cash")
        with closing(get_connection()) as conn:
            sale_id = conn.execute("SELECT id FROM sales").fetchone()[0]
            item_id = conn.execute("SELECT id FROM sale_items").fetchone()[0]
        process_sale_return(sale_id, [{"sale_item_id": item_id, "quantity": 1}])
        trend = get_dashboard_sales_trend(7)
        self.assertEqual(len(trend), 7)
        self.assertEqual(trend[-1]["net_sales"], 200)
        self.assertTrue(all(point["net_sales"] == 0 for point in trend[:-1]))
