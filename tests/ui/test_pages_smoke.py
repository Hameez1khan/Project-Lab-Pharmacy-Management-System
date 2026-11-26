import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtWidgets import QApplication

import i18n
import pages.audit_logs as audit_logs
import pages.batch_management as batch_management
import pages.pos as pos
import pages.prescriptions as prescriptions
import pages.purchasing as purchasing
import pages.product as product
import pages.reports as reports
import pages.returned_items as returned_items
import pages.sales_history as sales_history
import pages.settings as settings
from pages.dashboard import DashboardPage


class PageSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        i18n._language = "ar"
        QLocale.setDefault(QLocale("ar_EG"))
        self.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def tearDown(self):
        i18n._language = "en"
        QLocale.setDefault(QLocale("en_GB"))
        self.app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def assert_renders(self, widget):
        widget.resize(900, 650)
        widget.show()
        self.app.processEvents()
        self.assertFalse(widget.grab().isNull())
        widget.close()

    def test_all_pages_render_without_database_access(self):
        user = {"id": 1, "username": "test-admin", "role": "admin"}
        with (
            patch.object(product, "get_categories", return_value=[]),
            patch.object(product, "get_product_rows", return_value=[]),
            patch.object(batch_management, "get_categories", return_value=[]),
            patch.object(batch_management, "get_batch_rows", return_value=[]),
            patch.object(pos, "get_categories", return_value=[]),
            patch.object(pos, "get_products_for_pos", return_value=[]),
            patch.object(prescriptions, "get_prescription_rows", return_value=[]),
            patch.object(purchasing, "get_purchase_products", return_value=[]),
            patch.object(purchasing, "get_suppliers", return_value=[]),
            patch.object(purchasing, "get_purchase_history", return_value=[]),
            patch.object(sales_history, "get_sales_history", return_value=[]),
            patch.object(returned_items, "get_returns_history", return_value=[]),
            patch.object(audit_logs, "get_audit_log_rows", return_value=[]),
            patch.object(settings, "get_password_manageable_users", return_value=[]),
        ):
            widgets = [
                DashboardPage(),
                product.ProductPage(current_user=user),
                batch_management.BatchManagementPage(current_user=user),
                pos.POSPage(current_user=user),
                prescriptions.PrescriptionsPage(),
                purchasing.PurchasingPage(current_user=user),
                sales_history.SalesHistoryPage(current_user=user),
                returned_items.ReturnedItemsPage(current_user=user),
                audit_logs.AuditLogsPage(),
                reports.ReportsPage(user),
                settings.SettingsPage(current_user=user),
            ]
            for widget in widgets:
                self.assert_renders(widget)


if __name__ == "__main__":
    unittest.main()
