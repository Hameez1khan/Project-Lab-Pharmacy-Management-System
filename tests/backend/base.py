import os
from contextlib import closing
from pathlib import Path
import tempfile
import unittest

from database.db import initialize_database, get_connection


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.previous_path = os.environ.get("KHALIS_DAWA_DB_PATH")
        os.environ["KHALIS_DAWA_DB_PATH"] = str(self.db_path)
        initialize_database()

    def tearDown(self):
        if self.previous_path is None:
            os.environ.pop("KHALIS_DAWA_DB_PATH", None)
        else:
            os.environ["KHALIS_DAWA_DB_PATH"] = self.previous_path
        self.temp_dir.cleanup()

    def add_product(self, name="Medicine", price=100.0, minimum=5):
        with closing(get_connection("Test setup")) as conn, conn:
            cursor = conn.execute("""INSERT INTO products
                (name,dosage_form,barcode,selling_price,min_stock_level,category,
                 manufacturer,prescription_required)
                VALUES(?,?,?,?,?,'General','Test',0)""",
                (name, "Tablet", f"code-{name}", price, minimum))
            return cursor.lastrowid

    def add_batch(self, product_id, number, quantity, expiry="2099-12-31", cost=50.0):
        with closing(get_connection("Test setup")) as conn, conn:
            cursor = conn.execute("""INSERT INTO batches
                (product_id,batch_number,expiry_date,quantity,purchase_unit_cost,
                 total_purchase_cost,discount_percent)
                VALUES(?,?,?,?,?,?,0)""",
                (product_id, number, expiry, quantity, cost, cost * quantity))
            return cursor.lastrowid
