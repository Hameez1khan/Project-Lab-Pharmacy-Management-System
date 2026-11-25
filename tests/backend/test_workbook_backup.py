from pathlib import Path
from contextlib import closing

from openpyxl import load_workbook

from database.backup import create_database_backup, restore_database, validate_database_file
from database.db import get_connection
from database.inventory_audit import operator
from database.workbook import TABLES, TECH_PREFIX, VERSION_V1, export_book, import_book
from tests.backend.base import DatabaseTestCase


class WorkbookAndBackupTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.operator_token = operator.set(("admin", "admin"))

    def tearDown(self):
        operator.reset(self.operator_token)
        super().tearDown()

    def test_v2_export_has_business_sheets_hidden_data_and_no_password(self):
        self.add_product()
        path = Path(self.temp_dir.name) / "export.xlsx"
        export_book(path)
        book = load_workbook(path, data_only=False)
        self.assertIn("Overview", book.sheetnames)
        self.assertIn("Inventory", book.sheetnames)
        self.assertEqual(book["Manifest"]["A1"].value, "Pharmacy workbook v2")
        self.assertEqual(book[TECH_PREFIX + "users"].sheet_state, "hidden")
        self.assertNotIn("password", [c.value for c in book[TECH_PREFIX + "users"][1]])
        self.assertEqual(book["Products"]["A2"].value, 1)
        book.close()

    def test_v2_duplicate_import_skips_and_conflict_rolls_back(self):
        self.add_product()
        path = Path(self.temp_dir.name) / "export.xlsx"
        export_book(path)
        added, skipped = import_book(path)
        self.assertEqual(added, 0)
        self.assertGreater(skipped, 0)

        book = load_workbook(path)
        sheet = book[TECH_PREFIX + "products"]
        headers = [cell.value for cell in sheet[1]]
        sheet.cell(2, headers.index("name") + 1, "Conflicting name")
        conflict = Path(self.temp_dir.name) / "conflict.xlsx"
        book.save(conflict)
        book.close()
        with self.assertRaisesRegex(ValueError, "different data"):
            import_book(conflict)
        with closing(get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM products").fetchone()[0], 1)

    def test_v1_workbook_remains_importable(self):
        self.add_product()
        v2 = Path(self.temp_dir.name) / "v2.xlsx"
        export_book(v2)
        book = load_workbook(v2)
        manifest = book["Manifest"]
        manifest.sheet_state = "visible"
        manifest["A1"] = VERSION_V1
        technical_rows = {
            table: list(book[TECH_PREFIX + table].values) for table in TABLES
        }
        for name in list(book.sheetnames):
            if name != "Manifest":
                book.remove(book[name])
        for table in TABLES:
            target = book.create_sheet(table)
            for row in technical_rows[table]:
                target.append(row)
        v1 = Path(self.temp_dir.name) / "v1.xlsx"
        book.save(v1)
        book.close()
        added, skipped = import_book(v1)
        self.assertEqual(added, 0)
        self.assertGreater(skipped, 0)

    def test_exact_backup_and_restore_with_safety_copy(self):
        self.add_product("Before backup")
        backup = Path(self.temp_dir.name) / "backup.db"
        create_database_backup(backup)
        self.assertEqual(validate_database_file(backup)["integrity"], "ok")
        self.add_product("After backup")
        safety = restore_database(backup, Path(self.temp_dir.name) / "safety")
        self.assertTrue(safety.exists())
        with closing(get_connection()) as conn:
            names = [row[0] for row in conn.execute("SELECT name FROM products ORDER BY id")]
        self.assertEqual(names, ["Before backup"])
