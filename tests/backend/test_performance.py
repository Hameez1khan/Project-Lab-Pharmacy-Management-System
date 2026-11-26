import sqlite3
import time
from contextlib import closing
from unittest.mock import patch

from database.db import create_sale, get_connection, preview_sale_allocations
from database.performance import (
    CheckoutPerformance, get_performance_statistics,
    initialize_performance_database, record_metric,
)
from tests.backend.base import DatabaseTestCase


class PerformanceMetricsTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        initialize_performance_database()

    def test_statistics_include_count_and_distribution(self):
        for duration in (10, 20, 30, 40, 100):
            record_metric("checkout", "total_system_checkout", duration)
        record_metric(
            "checkout", "total_system_checkout", 15,
            outcome="failed", error_category="ValueError",
        )

        result = get_performance_statistics(30)
        total = next(row for row in result["phases"]
                     if row["phase"] == "total_system_checkout")

        self.assertEqual(result["attempts"], 6)
        self.assertEqual(result["successful"], 5)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(total["count"], 6)
        self.assertEqual(total["min"], 10)
        self.assertEqual(total["max"], 100)
        self.assertEqual(total["median"], 25)
        self.assertEqual(total["p95"], 100)

    def test_checkout_session_separates_processing_and_interaction(self):
        session = CheckoutPerformance(2, 5)
        with session.measure("fefo_allocation"):
            pass
        with session.measure("payment_selection", "interaction"):
            pass
        session.finish("cancelled")

        result = get_performance_statistics(30)
        phases = {(row["phase"], row["metric_kind"]): row
                  for row in result["phases"]}
        self.assertIn(("processing_total", "processing"), phases)
        self.assertIn(("interaction_total", "interaction"), phases)
        self.assertEqual(result["cancelled"], 1)

    def test_checkout_metrics_are_flushed_in_one_write(self):
        session = CheckoutPerformance(1, 1)
        for index in range(50):
            session.record_phase(f"phase_{index}", index / 10)
        started = time.perf_counter()
        session.finish("success")
        self.assertLess(time.perf_counter() - started, 0.5)
        result = get_performance_statistics(30)
        self.assertEqual(result["attempts"], 1)
        self.assertGreaterEqual(len(result["phases"]), 53)

    def test_inventory_deduction_callback_measures_guarded_updates(self):
        product_id = self.add_product("Measured Deduction", price=100)
        self.add_batch(product_id, "MEASURED", 5, "2099-01-01")
        captured = {}
        create_sale(
            [{"product_id": product_id, "quantity": 2}], "Cash",
            performance_callback=lambda phase, duration: captured.update(
                {phase: duration}
            ),
        )
        self.assertIn("inventory_deduction", captured)
        self.assertGreaterEqual(captured["inventory_deduction"], 0)

    def test_schema_does_not_store_customer_or_search_values(self):
        with closing(get_connection()) as connection:
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(performance_metrics)"
                ).fetchall()
            }
        self.assertFalse(
            columns & {"customer_name", "customer_ssn", "barcode", "search_text"}
        )

    def test_metrics_failure_never_breaks_pos(self):
        with patch("database.performance._connect", side_effect=sqlite3.OperationalError):
            self.assertFalse(record_metric("search", "product_lookup", 1.0))

    def test_representative_fefo_checkout_stays_within_regression_limit(self):
        product_id = self.add_product("Timed Medicine", price=125.0)
        first_batch = self.add_batch(product_id, "EARLY", 2, "2098-01-01")
        second_batch = self.add_batch(product_id, "LATER", 5, "2099-01-01")
        cart = [{"product_id": product_id, "quantity": 4}]

        started = time.perf_counter()
        plan, total = preview_sale_allocations(cart)
        create_sale(cart, "Cash", cashier_id=1)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2.0, "A small local FEFO checkout regressed above 2 seconds")
        self.assertEqual(total, 500.0)
        self.assertEqual([part["batch_id"] for part in plan[0]["allocations"]],
                         [first_batch, second_batch])
        with closing(get_connection()) as connection:
            quantities = [row[0] for row in connection.execute(
                "SELECT quantity FROM batches WHERE product_id=? ORDER BY expiry_date",
                (product_id,),
            ).fetchall()]
        self.assertEqual(quantities, [0, 3])


if __name__ == "__main__":
    import unittest
    unittest.main()
