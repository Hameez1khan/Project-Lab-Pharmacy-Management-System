from contextlib import closing
from datetime import datetime

from database.db import (
    delete_supplier,
    get_connection,
    get_purchase_history,
    receive_purchase,
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

    def test_receiving_creates_history_and_updates_existing_batch_cost(self):
        product = self.add_product("Paracetamol", 100)
        today = datetime.now().date().isoformat()
        first = receive_purchase(
            self.supplier_id, "INV-1001", today, [self.line(product)],
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
