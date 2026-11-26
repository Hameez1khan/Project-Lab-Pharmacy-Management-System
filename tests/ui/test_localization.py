import ast
import os
import pathlib
import string
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

import i18n
from login_window import LoginWindow
from pages.dashboard import NetSalesChart


ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND_FILES = [
    ROOT / "login_window.py",
    ROOT / "main_window.py",
    ROOT / "i18n.py",
    *sorted((ROOT / "pages").glob("*.py")),
]
BACKEND_MESSAGE_FILES = [
    ROOT / "database" / name
    for name in ("backup.py", "db.py", "reporting.py", "workbook.py")
]

VISIBLE_TEXT_CALLS = {
    "QCheckBox", "QGroupBox", "QLabel", "QPushButton",
    "setPlaceholderText", "setText", "setTitle", "setToolTip", "setWindowTitle",
}
INTENTIONAL_VISIBLE_LITERALS = {
    "Khalis Dawa", "+", "-", "0", "0.00", "YYYY-MM-DD", "■",
}
AUDITED_DYNAMIC_ARGUMENTS = {
    "message", "text", "label", "title", "header", "column", "h", "key", "caption",
    "expiry_status", "str(error)", "str(e)", "self.role_style['mode_text']",
    "row_data['description']", "row_data['role'].title()",
    "row_data['payment_method']", "receipt_data['payment_method']",
    "report_data['payment_method']", "row['operation']", "row['phase']",
    "row['metric_kind']", "message or 'Export complete.'",
    "value", "row['status'].replace('_', ' ').title()", "row['movement']",
    "order['status'].replace('_', ' ').title()",
    "order.get('notes')",
}


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _literal_values(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        return _literal_values(node.body) | _literal_values(node.orelse)
    return set()


def _format_fields(value):
    return {
        field_name.split(".", 1)[0].split("[", 1)[0]
        for _, field_name, _, _ in string.Formatter().parse(value)
        if field_name is not None
    }


def _translations_for(key):
    translations = i18n._strings.get(key)
    if translations is None:
        translations = i18n._folded_strings.get(key.casefold(), {})
    return translations


def _translated_collection_values(tree):
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, (ast.Tuple, ast.List)):
            translated_names = {
                call.args[0].id
                for statement in node.body for call in ast.walk(statement)
                if isinstance(call, ast.Call) and call.args
                and _call_name(call.func) in {"T", "TF"}
                and isinstance(call.args[0], ast.Name)
            }
            indexes = [
                index for index, target in enumerate(node.target.elts)
                if isinstance(target, ast.Name) and target.id in translated_names
            ]
            if isinstance(node.iter, (ast.Tuple, ast.List)):
                for row in node.iter.elts:
                    if not isinstance(row, (ast.Tuple, ast.List)):
                        continue
                    for index in indexes:
                        if index < len(row.elts):
                            values |= _literal_values(row.elts[index])
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for generator in node.generators:
                if not isinstance(generator.target, ast.Name):
                    continue
                translated_names = {
                    call.args[0].id for call in ast.walk(node.elt)
                    if isinstance(call, ast.Call) and call.args
                    and _call_name(call.func) in {"T", "TF"}
                    and isinstance(call.args[0], ast.Name)
                }
                if generator.target.id not in translated_names:
                    continue
                if isinstance(generator.iter, (ast.Tuple, ast.List, ast.Set)):
                    for item in generator.iter.elts:
                        values |= _literal_values(item)
        if (isinstance(node, ast.Call) and _call_name(node.func) == "make_table"
                and node.args and isinstance(node.args[0], (ast.Tuple, ast.List))):
            for item in node.args[0].elts:
                values |= _literal_values(item)
    return values


class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._language = "en"
        QLocale.setDefault(QLocale("en_GB"))

    def test_catalog_is_well_formed_complete_and_has_no_duplicate_keys(self):
        rows = []
        malformed = []
        for line_number, line in enumerate(i18n._catalog.strip().splitlines(), 1):
            if not line.strip():
                continue
            parts = i18n._split_catalog_line(line)
            if len(parts) != 3:
                malformed.append(f"line {line_number}: {line}")
                continue
            rows.append((line_number, *parts))

        counts = {}
        for line_number, key, hungarian, arabic in rows:
            counts.setdefault(key, []).append(line_number)
            self.assertTrue(hungarian.strip(), f"Missing Hungarian translation: {key}")
            self.assertTrue(arabic.strip(), f"Missing Arabic translation: {key}")

        duplicates = {
            key: lines for key, lines in counts.items() if len(lines) > 1
        }
        self.assertEqual([], malformed, "\n".join(malformed))
        self.assertEqual({}, duplicates, str(duplicates))
        self.assertEqual(len(rows), len(i18n._strings))

    def test_translation_placeholders_match_english_source(self):
        mismatches = []
        for key, translations in i18n._strings.items():
            expected = _format_fields(key)
            for language, translated in translations.items():
                actual = _format_fields(translated)
                if actual != expected:
                    mismatches.append(
                        f"{key!r} [{language}]: expected {expected}, found {actual}"
                    )
        self.assertEqual([], mismatches, "\n".join(mismatches))

    def test_every_literal_and_conditional_translation_key_is_covered(self):
        missing = []
        for path in FRONTEND_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if _call_name(node.func) not in {"T", "TF"}:
                    continue
                for key in _literal_values(node.args[0]):
                    translations = _translations_for(key)
                    if not translations.get("hu") or not translations.get("ar"):
                        missing.append(f"{path.name}:{node.lineno}: {key}")
            for key in _translated_collection_values(tree):
                translations = _translations_for(key)
                if not translations.get("hu") or not translations.get("ar"):
                    missing.append(f"{path.name}:dynamic collection: {key}")
        self.assertEqual([], missing, "\n".join(missing))

    def test_backend_messages_have_catalog_entries(self):
        missing = []
        for path in BACKEND_MESSAGE_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                values = []
                if (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                        and node.exc.args):
                    values.extend(_literal_values(node.exc.args[0]))
                if isinstance(node, ast.Return) and isinstance(node.value, (ast.Tuple, ast.List)):
                    for item in node.value.elts:
                        values.extend(_literal_values(item))
                for key in values:
                    translations = _translations_for(key)
                    if not translations.get("hu") or not translations.get("ar"):
                        missing.append(f"{path.name}:{node.lineno}: {key}")
        self.assertEqual([], missing, "\n".join(missing))

    def test_dynamic_translation_calls_are_explicitly_audited(self):
        unaudited = []
        for path in FRONTEND_FILES:
            if path.name == "i18n.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if _call_name(node.func) not in {"T", "TF"}:
                    continue
                if _literal_values(node.args[0]):
                    continue
                expression = ast.unparse(node.args[0])
                if expression not in AUDITED_DYNAMIC_ARGUMENTS:
                    unaudited.append(f"{path.name}:{node.lineno}: {expression}")
        self.assertEqual([], unaudited, "\n".join(unaudited))

    def test_visible_text_literals_are_translated_or_intentional(self):
        hardcoded = []
        for path in FRONTEND_FILES:
            if path.name == "i18n.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if _call_name(node.func) not in VISIBLE_TEXT_CALLS:
                    continue
                argument = node.args[0]
                if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                    continue
                value = argument.value.strip()
                if value and value not in INTENTIONAL_VISIBLE_LITERALS:
                    hardcoded.append(f"{path.name}:{node.lineno}: {value}")
        self.assertEqual([], hardcoded, "\n".join(hardcoded))

    def test_lookup_preserves_exact_case_and_has_safe_fallbacks(self):
        i18n._language = "hu"
        self.assertEqual("Felhasználónév", i18n.T("Username"))
        self.assertEqual("FELHASZNÁLÓNÉV", i18n.T("USERNAME"))
        self.assertEqual("Készpénz", i18n.T("cash"))
        self.assertEqual("Ismeretlen felirat", i18n.T("Ismeretlen felirat"))
        self.assertEqual("Egységár (Ft)", i18n.T("Unit Price (Ft)"))

        i18n._language = "en"
        self.assertEqual("Username", i18n.T("Username"))
        self.assertEqual("Hello Ada", i18n.TF("Hello {name}", name="Ada"))

    def test_dynamic_audit_descriptions_translate_without_changing_record_names(self):
        i18n._language = "hu"
        purchase = i18n.translate_audit_description(
            "Received purchase INV-42 from MediSupply (12 units)"
        )
        self.assertIn("INV-42", purchase)
        self.assertIn("MediSupply", purchase)
        self.assertNotIn("Received purchase", purchase)
        i18n._language = "ar"
        sold = i18n.translate_audit_description("Sold Amoxicillin x3")
        self.assertIn("Amoxicillin", sold)
        self.assertNotIn("Sold", sold)

    def test_login_is_translated_but_brand_is_unchanged(self):
        for code, expected in (("hu", "Bejelentkezés"), ("ar", "تسجيل الدخول")):
            i18n._language = code
            QLocale.setDefault(QLocale("hu_HU" if code == "hu" else "ar_EG"))
            window = LoginWindow()
            labels = [label.text() for label in window.findChildren(QLabel)]
            buttons = [button.text() for button in window.findChildren(QPushButton)]
            self.assertIn("Khalis Dawa", labels)
            self.assertIn(expected, labels)
            self.assertNotIn("Proceed", buttons)
            window.close()

    def test_locale_date_changes_language(self):
        i18n._language = "hu"
        QLocale.setDefault(QLocale("hu_HU"))
        hungarian = i18n.format_date("2026-11-26", long=True)
        i18n._language = "ar"
        QLocale.setDefault(QLocale("ar_EG"))
        arabic = i18n.format_date("2026-11-26", long=True)
        self.assertNotEqual(hungarian, arabic)
        self.assertNotIn("Thursday", hungarian + arabic)

    def test_chart_renders_real_points_and_empty_state(self):
        chart = NetSalesChart()
        chart.resize(900, 260)
        chart.set_points([
            {"date": "2026-11-01", "net_sales": 1200},
            {"date": "2026-11-02", "net_sales": 1800},
            {"date": "2026-11-03", "net_sales": 900},
        ])
        self.assertEqual(("2026-11-01", 1200), chart.points[0])
        image = chart.grab().toImage()
        colors = {
            image.pixelColor(x, y).name()
            for x in range(0, image.width(), 20)
            for y in range(0, image.height(), 20)
        }
        self.assertGreater(len(colors), 3)
        chart.set_points([])
        self.assertFalse(chart.grab().isNull())
        chart.close()


if __name__ == "__main__":
    unittest.main()
