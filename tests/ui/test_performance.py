import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from pages.performance import PerformancePage


EMPTY_STATS = {
    "days": 30,
    "attempts": 0,
    "successful": 0,
    "failed": 0,
    "cancelled": 0,
    "success_rate": 0.0,
    "checkout": {"avg": 0.0, "min": 0.0, "max": 0.0,
                 "median": 0.0, "p95": 0.0},
    "phases": [],
}


class PerformancePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_page_renders_empty_statistics(self):
        with patch("pages.performance.get_performance_statistics",
                   return_value=EMPTY_STATS):
            page = PerformancePage({"role": "admin"})
            page.resize(1100, 700)
            page.show()
            self.app.processEvents()
            self.assertFalse(page.grab().isNull())
            self.assertEqual(page.table.rowCount(), 0)
            page.close()

    def test_page_renders_phase_statistics(self):
        data = dict(EMPTY_STATS)
        data["attempts"] = 3
        data["successful"] = 2
        data["failed"] = 1
        data["success_rate"] = 66.666
        data["checkout"] = {"avg": 25.0, "min": 10.0, "max": 50.0,
                            "median": 15.0, "p95": 50.0}
        data["phases"] = [{
            "operation": "checkout", "phase": "transaction",
            "metric_kind": "processing", "count": 3, "success": 2,
            "failed": 1, "cancelled": 0, "avg": 12.0, "min": 8.0,
            "max": 20.0, "median": 8.0, "p95": 20.0,
        }]
        with patch("pages.performance.get_performance_statistics", return_value=data):
            page = PerformancePage({"role": "admin"})
            self.assertEqual(page.table.rowCount(), 1)
            self.assertEqual(page.table.item(0, 3).text(), "3")
            page.close()


if __name__ == "__main__":
    unittest.main()
