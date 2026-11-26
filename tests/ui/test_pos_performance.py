import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

from database.db import get_connection, initialize_database
from database.performance import get_performance_statistics
from pages.pos import POSPage, build_receipt_summary


class POSPerformanceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = os.environ.get("KHALIS_DAWA_DB_PATH")
        os.environ["KHALIS_DAWA_DB_PATH"] = str(Path(self.temp_dir.name) / "pos.db")
        initialize_database()
        with closing(get_connection("POS performance test")) as connection, connection:
            product_id = connection.execute("""
                INSERT INTO products
                    (name, dosage_form, barcode, selling_price, min_stock_level,
                     category, manufacturer, prescription_required)
                VALUES ('Measured Medicine','Tablet','998877',250,2,
                        'General','Test',0)
            """).lastrowid
            connection.execute("""
                INSERT INTO batches
                    (product_id,batch_number,expiry_date,quantity,purchase_unit_cost,
                     total_purchase_cost,discount_percent)
                VALUES (?, 'PERF-1', '2099-12-31', 10, 100, 1000, 0)
            """, (product_id,))
        self.product_id = product_id

    def tearDown(self):
        if self.previous_path is None:
            os.environ.pop("KHALIS_DAWA_DB_PATH", None)
        else:
            os.environ["KHALIS_DAWA_DB_PATH"] = self.previous_path
        self.temp_dir.cleanup()

    def test_successful_checkout_records_required_phases(self):
        page = POSPage({"id": 1, "username": "admin", "role": "admin"})
        page.cart = {
            self.product_id: {
                "product_id": self.product_id,
                "name": "Measured Medicine",
                "price": 250.0,
                "original_price": 250.0,
                "has_discount": False,
                "discount_percent": 0,
                "prescription_required": False,
                "quantity": 2,
            }
        }
        with (
            patch("pages.pos.run_centered_modal",
                  return_value=QDialog.DialogCode.Accepted),
            patch("pages.pos.QMessageBox.information"),
            patch("pages.pos.QMessageBox.warning"),
            patch("pages.pos.QMessageBox.critical"),
        ):
            page.checkout()

        statistics = get_performance_statistics(30)
        phases = {row["phase"] for row in statistics["phases"]
                  if row["operation"] == "checkout"}
        self.assertTrue({
            "cart_availability", "fefo_allocation", "payment_selection",
            "transaction", "inventory_deduction", "receipt_summary",
            "total_system_checkout",
        }.issubset(phases))
        self.assertEqual(statistics["successful"], 1)
        self.assertEqual(page.cart, {})
        with closing(get_connection()) as connection:
            stock = connection.execute(
                "SELECT quantity FROM batches WHERE product_id=?", (self.product_id,)
            ).fetchone()[0]
        self.assertEqual(stock, 8)
        page.close()

    def test_receipt_summary_contains_real_sale_values(self):
        summary = build_receipt_summary([{
            "product_name": "Measured Medicine", "quantity": 2,
            "price": 250.0, "subtotal": 500.0,
        }], 500.0, "Card")
        self.assertEqual(summary["items"][0]["name"], "Measured Medicine")
        self.assertEqual(summary["items"][0]["subtotal"], 500.0)
        self.assertEqual(summary["total"], 500.0)
        self.assertEqual(summary["payment_method"], "Card")


if __name__ == "__main__":
    unittest.main()
