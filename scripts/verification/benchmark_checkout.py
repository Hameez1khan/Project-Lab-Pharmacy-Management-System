"""Measure checkout database time with a temporary pharmacy database."""

from contextlib import closing
import os
from pathlib import Path
import statistics
import sys
import tempfile
from time import perf_counter


CHECKOUTS = 100
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["KHALIS_DAWA_DB_PATH"] = str(Path(temp_dir) / "benchmark.db")

        from database.db import create_sale, get_connection, initialize_database

        initialize_database()
        with closing(get_connection("Performance benchmark setup")) as conn, conn:
            product_id = conn.execute(
                """INSERT INTO products
                   (name, dosage_form, barcode, selling_price, min_stock_level,
                    category, manufacturer, prescription_required)
                   VALUES ('Benchmark Medicine', 'Tablet', '9999999999999',
                           100, 5, 'General', 'Benchmark', 0)"""
            ).lastrowid
            conn.execute(
                """INSERT INTO batches
                   (product_id, batch_number, expiry_date, quantity,
                    purchase_unit_cost, total_purchase_cost, discount_percent)
                   VALUES (?, 'PERF-001', '2099-12-31', ?, 50, ?, 0)""",
                (product_id, CHECKOUTS, CHECKOUTS * 50),
            )

        durations = []
        for _ in range(CHECKOUTS):
            started = perf_counter()
            create_sale([{"product_id": product_id, "quantity": 1}], "Cash")
            durations.append((perf_counter() - started) * 1000)

        ordered = sorted(durations)
        percentile_95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
        print(f"Checkouts: {CHECKOUTS}")
        print(f"Average: {statistics.mean(durations):.2f} ms")
        print(f"Median: {statistics.median(durations):.2f} ms")
        print(f"95th percentile: {percentile_95:.2f} ms")
        print(f"Slowest: {max(durations):.2f} ms")


if __name__ == "__main__":
    main()
