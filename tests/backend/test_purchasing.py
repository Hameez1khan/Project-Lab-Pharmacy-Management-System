from contextlib import closing
from datetime import datetime

from database.db import (
    change_purchase_order_status,
    create_order_from_recommendations,
    delete_supplier,
    get_connection,
    get_purchase_order,
    get_purchase_orders,
    get_purchase_history,
    get_purchase_receipt,
    get_reorder_suggestions,
    receive_purchase,
    save_purchase_order,
    save_supplier,
)
from tests.backend.base import DatabaseTestCase


class PurchasingTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        success, message = save_supplier(
            "MediSupply Kft.", "Anna Kovacs", "+36 1 555 0101",
            "orders@medisupply.test", "Budapest", acting_username="admin",
            acting_role="admin",
        )
        self.assertTrue(success, message)
        with closing(get_connection()) as conn:
            self.supplier_id = conn.execute("SELECT id FROM suppliers").fetchone()[0]

    def line(self, product_id, batch="LOT-001", quantity=10, cost="40.00"):
        return {
            "product_id": product_id,
            "batch_number": batch,
            "expiry_date": "2099-12-31",
            "quantity": quantity,
            "unit_cost": cost,
        }

    def order(self, product_id, quantity=10, cost="40.00", status="draft"):
        today = datetime.now().date()
        return save_purchase_order(
            self.supplier_id, today.isoformat(),
            today.replace(year=today.year + 1).isoformat(),
            [{"product_id": product_id, "quantity": quantity, "unit_cost": cost}],
            status=status, acting_username="admin", acting_role="admin",
        )

    def test_receiving_creates_history_and_updates_existing_batch_cost(self):
        product = self.add_product("Paracetamol", 100)
        today = datetime.now().date().isoformat()
        first = receive_purchase(
            self.supplier_id, "INV-1001", today, [self.line(product)],
            notes="Keep refrigerated after opening.",
            acting_username="admin", acting_role="admin",
        )
        second = receive_purchase(
            self.supplier_id, "INV-1002", today,
            [self.line(product, quantity=10, cost="60.00")],
            acting_username="admin", acting_role="admin",
        )
        self.assertNotEqual(first, second)
        with closing(get_connection()) as conn:
            batch = conn.execute("""SELECT quantity,purchase_unit_cost,total_purchase_cost
                FROM batches WHERE batch_number='LOT-001'""").fetchone()
            item_count = conn.execute(
                "SELECT count(*) FROM purchase_receipt_items"
            ).fetchone()[0]
        self.assertEqual((batch[0], batch[1], batch[2]), (20, 50.0, 1000.0))
        self.assertEqual(item_count, 2)
        self.assertEqual(len(get_purchase_history()), 2)
        receipt = get_purchase_receipt(first)
        self.assertEqual(receipt["supplier"], "MediSupply Kft.")
        self.assertEqual(receipt["notes"], "Keep refrigerated after opening.")

        success, message = delete_supplier(self.supplier_id, "admin", "admin")
        self.assertFalse(success)
        self.assertIn("history", message)

    def test_conflicting_batch_rolls_back_complete_receipt(self):
        first_product = self.add_product("First", 100)
        second_product = self.add_product("Second", 120)
        today = datetime.now().date().isoformat()
        receive_purchase(
            self.supplier_id, "INV-2001", today, [self.line(first_product)],
            acting_username="admin", acting_role="admin",
        )
        with self.assertRaisesRegex(ValueError, "conflicts"):
            receive_purchase(
                self.supplier_id, "INV-2002", today, [self.line(second_product)],
                acting_username="admin", acting_role="admin",
            )
        with closing(get_connection()) as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM purchase_receipts").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("SELECT quantity FROM batches WHERE batch_number='LOT-001'").fetchone()[0],
                10,
            )

    def test_receiving_requires_a_selected_supplier(self):
        product = self.add_product("Selection Test", 100)
        with self.assertRaisesRegex(ValueError, "valid supplier"):
            receive_purchase(
                None, "INV-3001", datetime.now().date().isoformat(),
                [self.line(product)], acting_username="admin", acting_role="admin",
            )

    def test_purchase_order_lifecycle_and_edit_restrictions(self):
        product = self.add_product("Lifecycle", 100)
        order_id, number = self.order(product)
        order, items, _ = get_purchase_order(order_id)
        self.assertEqual(order["status"], "draft")
        self.assertEqual(items[0]["outstanding_quantity"], 10)
        self.assertTrue(number.startswith("PO-"))

        change_purchase_order_status(order_id, "pending", "admin", "admin")
        change_purchase_order_status(order_id, "ordered", "admin", "admin")
        with self.assertRaisesRegex(ValueError, "status change"):
            change_purchase_order_status(order_id, "draft", "admin", "admin")
        with self.assertRaisesRegex(ValueError, "draft or pending"):
            self.order(product, status="ordered")
        with self.assertRaisesRegex(ValueError, "draft or pending"):
            save_purchase_order(
                self.supplier_id, order["order_date"], order["expected_date"],
                [{"product_id": product, "quantity": 5, "unit_cost": 40}],
                purchase_order_id=order_id, acting_username="admin", acting_role="admin",
            )

    def test_purchase_order_writes_require_administrator_role(self):
        product = self.add_product("Permission Check", 100)
        today = datetime.now().date()
        with self.assertRaisesRegex(PermissionError, "Administrator"):
            save_purchase_order(
                self.supplier_id, today.isoformat(),
                today.replace(year=today.year + 1).isoformat(),
                [{"product_id": product, "quantity": 2, "unit_cost": 40}],
                acting_username="pharma", acting_role="pharmacist",
            )

    def test_supplier_and_receipt_writes_require_administrator_role(self):
        product = self.add_product("Restricted Receipt", 100)
        with self.assertRaisesRegex(PermissionError, "Administrator"):
            save_supplier("Blocked Supplier", acting_username="pharma",
                          acting_role="pharmacist")
        with self.assertRaisesRegex(PermissionError, "Administrator"):
            delete_supplier(self.supplier_id, "pharma", "pharmacist")
        with self.assertRaisesRegex(PermissionError, "Administrator"):
            receive_purchase(
                self.supplier_id, "BLOCKED-1", datetime.now().date().isoformat(),
                [self.line(product)], acting_username="pharma",
                acting_role="pharmacist",
            )
        with closing(get_connection()) as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM purchase_receipts").fetchone()[0], 0
            )

    def test_pending_order_can_return_to_draft_and_unreceived_order_can_cancel(self):
        product = self.add_product("Cancellation", 100)
        order_id, _ = self.order(product, status="pending")
        change_purchase_order_status(order_id, "draft", "admin", "admin")
        change_purchase_order_status(order_id, "cancelled", "admin", "admin")
        order, _, _ = get_purchase_order(order_id)
        self.assertEqual(order["status"], "cancelled")
        with self.assertRaisesRegex(ValueError, "status change"):
            change_purchase_order_status(order_id, "pending", "admin", "admin")

    def test_partial_and_full_receipt_updates_inventory_only_on_receipt(self):
        product = self.add_product("Partial Receipt", 100)
        order_id, _ = self.order(product, quantity=10, status="pending")
        change_purchase_order_status(order_id, "ordered", "admin", "admin")
        order, items, _ = get_purchase_order(order_id)
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM batches").fetchone()[0], 0)
        today = datetime.now().date().isoformat()
        first_line = self.line(product, "PO-BATCH", 4)
        first_line["purchase_order_item_id"] = items[0]["id"]
        receive_purchase(
            self.supplier_id, "PO-INV-1", today, [first_line], purchase_order_id=order_id,
            acting_username="admin", acting_role="admin",
        )
        order, items, _ = get_purchase_order(order_id)
        self.assertEqual(order["status"], "partially_received")
        self.assertEqual((items[0]["received_quantity"], items[0]["outstanding_quantity"]), (4, 6))
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute(
                "SELECT quantity FROM batches WHERE batch_number='PO-BATCH'"
            ).fetchone()[0], 4)

        second_line = self.line(product, "PO-BATCH", 6)
        second_line["purchase_order_item_id"] = items[0]["id"]
        receive_purchase(
            self.supplier_id, "PO-INV-2", today, [second_line], purchase_order_id=order_id,
            acting_username="admin", acting_role="admin",
        )
        order, items, receipts = get_purchase_order(order_id)
        self.assertEqual(order["status"], "fully_received")
        self.assertEqual(items[0]["outstanding_quantity"], 0)
        self.assertEqual(len(receipts), 2)
        with self.assertRaisesRegex(ValueError, "ordered or partially"):
            receive_purchase(
                self.supplier_id, "PO-INV-3", today, [second_line],
                purchase_order_id=order_id,
                acting_username="admin", acting_role="admin",
            )

    def test_receipt_rejects_excess_duplicate_reference_and_preserves_stock(self):
        product = self.add_product("Receipt Limits", 100)
        order_id, _ = self.order(product, quantity=5, status="pending")
        change_purchase_order_status(order_id, "ordered", "admin", "admin")
        _, items, _ = get_purchase_order(order_id)
        line = self.line(product, "LIMIT-BATCH", 6)
        line["purchase_order_item_id"] = items[0]["id"]
        today = datetime.now().date().isoformat()
        with self.assertRaisesRegex(ValueError, "exceeds"):
            receive_purchase(
                self.supplier_id, "LIMIT-1", today, [line], purchase_order_id=order_id,
                acting_username="admin", acting_role="admin",
            )
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM batches").fetchone()[0], 0)
        line["quantity"] = 2
        receive_purchase(
            self.supplier_id, "LIMIT-1", today, [line], purchase_order_id=order_id,
            acting_username="admin", acting_role="admin",
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            receive_purchase(
                self.supplier_id, "LIMIT-1", today, [line], purchase_order_id=order_id,
                acting_username="admin", acting_role="admin",
            )
        with self.assertRaisesRegex(ValueError, "received stock"):
            change_purchase_order_status(order_id, "cancelled", "admin", "admin")

    def test_order_search_status_and_supplier_history(self):
        product = self.add_product("History Product", 100)
        order_id, number = self.order(product, status="pending")
        self.assertEqual(get_purchase_orders(number)[0]["id"], order_id)
        self.assertEqual(get_purchase_orders(status="pending")[0]["supplier"], "MediSupply Kft.")
        self.assertEqual(get_purchase_orders(supplier_id=self.supplier_id)[0]["id"], order_id)

    def test_reorder_period_stock_outstanding_and_movement_calculation(self):
        fast = self.add_product("Fast Reorder", 100, minimum=5)
        slow = self.add_product("Slow Reorder", 80, minimum=3)
        no_history = self.add_product("No History", 60, minimum=8)
        self.add_batch(fast, "FAST-USABLE", 5, "2099-12-31", 40)
        self.add_batch(fast, "FAST-EXPIRED", 100, "2020-01-01", 40)
        with closing(get_connection("Test sales")) as conn, conn:
            sale = conn.execute(
                "INSERT INTO sales(sale_datetime,total_amount,cashier_id,payment_method) VALUES(datetime('now'),0,1,'Cash')"
            ).lastrowid
            conn.execute("INSERT INTO sale_items(sale_id,product_id,product_name,quantity,unit_price,subtotal) VALUES(?,?,?,?,?,?)",
                         (sale, fast, "Fast Reorder", 30, 100, 3000))
            conn.execute("INSERT INTO sale_items(sale_id,product_id,product_name,quantity,unit_price,subtotal) VALUES(?,?,?,?,?,?)",
                         (sale, slow, "Slow Reorder", 1, 80, 80))
        order_id, _ = self.order(fast, quantity=4, status="pending")
        rows = {row["product"]: row for row in get_reorder_suggestions(30, 7)}
        self.assertEqual(rows["Fast Reorder"]["movement"], "Fast-moving")
        self.assertEqual(rows["Slow Reorder"]["movement"], "Slow-moving")
        self.assertEqual(rows["No History"]["movement"], "No sales history")
        self.assertEqual(rows["Fast Reorder"]["usable_stock"], 5)
        self.assertEqual(rows["Fast Reorder"]["outstanding_order"], 4)
        self.assertEqual(rows["No History"]["suggested_quantity"], 8)
        self.assertGreater(rows["Fast Reorder"]["suggested_quantity"], 0)
        before_cancel = rows["Fast Reorder"]["suggested_quantity"]
        change_purchase_order_status(order_id, "cancelled", "admin", "admin")
        recalculated = {
            row["product"]: row for row in get_reorder_suggestions(30, 7)
        }
        self.assertEqual(recalculated["Fast Reorder"]["outstanding_order"], 0)
        self.assertEqual(recalculated["Fast Reorder"]["suggested_quantity"], before_cancel + 4)
        for period in (7, 30, 60, 90):
            self.assertTrue(get_reorder_suggestions(period, 7))

    def test_selected_supplier_applies_to_every_reorder_suggestion(self):
        product = self.add_product("No Supplier History", 100)
        success, message = save_supplier(
            "Fast Delivery Kft.", lead_time_days=2,
            acting_username="admin", acting_role="admin",
        )
        self.assertTrue(success, message)
        with closing(get_connection()) as conn:
            supplier_id = conn.execute(
                "SELECT id FROM suppliers WHERE name='Fast Delivery Kft.'"
            ).fetchone()[0]
        today = datetime.now().date().isoformat()
        receive_purchase(
            supplier_id, "COST-SELECTED", today,
            [self.line(product, "COST-B", 1, "65.00")],
            acting_username="admin", acting_role="admin",
        )
        receive_purchase(
            self.supplier_id, "COST-ORIGINAL", today,
            [self.line(product, "COST-A", 1, "40.00")],
            acting_username="admin", acting_role="admin",
        )
        row = next(
            item for item in get_reorder_suggestions(30, 7, supplier_id)
            if item["product_id"] == product
        )
        self.assertEqual(row["preferred_supplier_id"], supplier_id)
        self.assertEqual(row["supplier"], "Fast Delivery Kft.")
        self.assertEqual(row["lead_time_days"], 2)
        self.assertEqual(row["unit_cost"], 65.0)

    def test_manual_recommendation_quantity_converts_to_draft_order(self):
        product = self.add_product("Manual Recommendation", 100)
        today = datetime.now().date()
        order_id, number = create_order_from_recommendations(
            self.supplier_id,
            [{"product_id": product, "quantity": 17, "unit_cost": 55}],
            today.isoformat(), today.replace(year=today.year + 1).isoformat(),
            "admin", "admin",
        )
        order, items, _ = get_purchase_order(order_id)
        self.assertEqual(order["status"], "draft")
        self.assertEqual(items[0]["ordered_quantity"], 17)
        self.assertTrue(number.startswith("PO-"))
