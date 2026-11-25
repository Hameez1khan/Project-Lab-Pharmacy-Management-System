import ast
import os
import pathlib
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


class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._language = "en"
        QLocale.setDefault(QLocale("en_GB"))

    def test_every_literal_translation_key_has_hungarian_and_arabic(self):
        missing = []
        for path in FRONTEND_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if not isinstance(node.func, ast.Name) or node.func.id not in {"T", "TF"}:
                    continue
                key_node = node.args[0]
                if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                    continue
                translations = i18n._strings.get(key_node.value.casefold(), {})
                if not translations.get("hu") or not translations.get("ar"):
                    missing.append(f"{path.name}:{node.lineno}: {key_node.value}")
        self.assertEqual([], missing, "\n".join(missing))

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
            ("2026-11-01", 1200),
            ("2026-11-02", 1800),
            ("2026-11-03", 900),
        ])
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
