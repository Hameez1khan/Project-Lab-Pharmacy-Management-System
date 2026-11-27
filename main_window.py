import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from i18n import LANGUAGES, T, format_current_date, is_rtl, language_name, set_language
from pages.audit_logs import AuditLogsPage
from pages.batch_management import BatchManagementPage
from pages.dashboard import DashboardPage
from pages.performance import PerformancePage
from pages.pos import POSPage
from pages.prescriptions import PrescriptionsPage
from pages.product import ProductPage
from pages.purchasing import PurchasingPage
from pages.reports import ReportsPage
from pages.returned_items import ReturnedItemsPage
from pages.sales_history import SalesHistoryPage
from pages.settings import SettingsPage
from ui_theme import (
    BORDER,
    CANVAS,
    DANGER,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SIDEBAR,
    SURFACE,
    SURFACE_SOFT,
    TEXT,
    TEXT_MUTED,
    TEXT_SUBTLE,
)


class MainWindow(QWidget):
    """Application shell shared by the administrator and pharmacist workspaces."""

    def __init__(self, user):
        super().__init__()
        from database.inventory_audit import operator

        operator.set((user["username"], user["role"]))
        self.current_user = user
        self.current_role = (user.get("role") or "admin").lower()
        self.sidebar_buttons = {}

        self.setWindowTitle("Khalis Dawa")
        self.setMinimumSize(1120, 720)
        self.setObjectName("mainWindow")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.create_sidebar())

        content = QWidget()
        content.setObjectName("workspace")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.create_top_header())

        self.stack = QStackedWidget()
        self._create_pages()
        content_layout.addWidget(self.stack, 1)
        root.addWidget(content, 1)

        self.setStyleSheet(f"""
            QWidget#mainWindow, QWidget#workspace {{ background:{CANVAS}; }}
        """)
        self.show_dashboard()

    def _create_pages(self):
        self._page_cache = {}
        self.dashboard_page = DashboardPage(current_user=self.current_user)
        self.dashboard_page.navigate_requested.connect(self.navigate_to)
        self._page_cache["dashboard"] = self.dashboard_page
        self.stack.addWidget(self.dashboard_page)

    def _page(self, key, factory):
        page = self._page_cache.get(key)
        if page is None:
            page = factory()
            self._page_cache[key] = page
            self.stack.addWidget(page)
        return page

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(246)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{ background:{SIDEBAR}; border:none; border-right:1px solid {BORDER}; }}
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(5)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("+")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(
            f"background:{PRIMARY}; color:white; border-radius:8px; font-size:22px; font-weight:800;"
        )
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("Khalis Dawa")
        name.setStyleSheet(f"color:{TEXT}; font-size:16px; font-weight:800;")
        role = QLabel(T("Administrator Mode" if self.current_role == "admin" else "Pharmacist Mode"))
        role.setStyleSheet(f"color:{PRIMARY}; font-size:10px; font-weight:700;")
        brand_text.addWidget(name)
        brand_text.addWidget(role)
        brand.addWidget(mark)
        brand.addLayout(brand_text)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(18)

        core = [
            ("Dashboard", QStyle.StandardPixmap.SP_ComputerIcon, self.show_dashboard),
            ("Point of Sale", QStyle.StandardPixmap.SP_DialogApplyButton, self.show_pos),
            ("Prescriptions", QStyle.StandardPixmap.SP_FileIcon, self.show_prescriptions),
            ("Sales History", QStyle.StandardPixmap.SP_FileDialogDetailedView, self.show_sales_history),
            ("Returned Items", QStyle.StandardPixmap.SP_ArrowBack, self.show_returned_items),
        ]
        inventory = [
            ("Products", QStyle.StandardPixmap.SP_DirIcon, self.show_product),
            ("Batch Management", QStyle.StandardPixmap.SP_FileDialogContentsView, self.show_batch_management),
        ]
        if self.current_role == "admin":
            inventory.append(("Purchasing", QStyle.StandardPixmap.SP_DriveHDIcon, self.show_purchasing))
        insights = [
            ("Reports", QStyle.StandardPixmap.SP_FileDialogInfoView, self.show_reports),
            ("Audit Logs", QStyle.StandardPixmap.SP_MessageBoxInformation, self.show_audit_logs),
        ]
        if self.current_role == "admin":
            insights.extend([
                ("POS Performance", QStyle.StandardPixmap.SP_BrowserReload, self.show_performance),
                ("Settings", QStyle.StandardPixmap.SP_FileDialogDetailedView, self.show_settings),
            ])

        for section, items in ((T("WORKSPACE"), core), (T("INVENTORY"), inventory), (T("INSIGHTS"), insights)):
            section_label = QLabel(section)
            section_label.setStyleSheet(
                f"color:#8a9790; font-size:9px; font-weight:800; padding:10px 10px 4px 10px;"
            )
            layout.addWidget(section_label)
            for text, icon, handler in items:
                button = self.create_sidebar_button(text, icon)
                button.clicked.connect(handler)
                layout.addWidget(button)
                self.sidebar_buttons[text] = button

        layout.addStretch()
        help_card = QFrame()
        help_card.setStyleSheet(
            f"QFrame {{ background:{PRIMARY_SOFT}; border:1px solid #cfe2d9; border-radius:8px; }}"
        )
        help_layout = QVBoxLayout(help_card)
        help_layout.setContentsMargins(12, 10, 12, 10)
        help_layout.setSpacing(2)
        help_title = QLabel(T("A little help?"))
        help_title.setStyleSheet(f"color:{PRIMARY_DARK}; font-size:11px; font-weight:700;")
        help_text = QLabel(T("Use search and filters to find records quickly."))
        help_text.setWordWrap(True)
        help_text.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        help_layout.addWidget(help_title)
        help_layout.addWidget(help_text)
        layout.addWidget(help_card)
        layout.addSpacing(8)

        logout = self.create_sidebar_button("Logout", QStyle.StandardPixmap.SP_DialogCloseButton, danger=True)
        logout.clicked.connect(self.logout)
        layout.addWidget(logout)
        self.sidebar_buttons["Logout"] = logout
        return sidebar

    def create_sidebar_button(self, text, standard_icon, danger=False):
        button = QPushButton(T(text))
        button.setFixedHeight(40)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIcon(self.style().standardIcon(standard_icon))
        button.setIconSize(QSize(16, 16))
        button.setProperty("danger", danger)
        button.setStyleSheet(self.sidebar_button_style(False, danger))
        return button

    def sidebar_button_style(self, active=False, danger=False):
        alignment = "right" if is_rtl() else "left"
        if active:
            return f"""
                QPushButton {{ background:{PRIMARY_SOFT}; color:{PRIMARY_DARK}; border:none;
                    border-left:3px solid {PRIMARY}; border-radius:6px; padding:0 11px;
                    text-align:{alignment}; font-size:12px; font-weight:700; }}
                QPushButton:hover {{ background:#dfefe7; }}
            """
        if danger:
            return f"""
                QPushButton {{ background:transparent; color:{DANGER}; border:none; border-radius:6px;
                    padding:0 11px; text-align:{alignment}; font-size:12px; font-weight:600; }}
                QPushButton:hover {{ background:#fff0f0; }}
            """
        return f"""
            QPushButton {{ background:transparent; color:{TEXT_SUBTLE}; border:none; border-radius:6px;
                padding:0 11px; text-align:{alignment}; font-size:12px; font-weight:600; }}
            QPushButton:hover {{ background:#eef3f0; color:{PRIMARY_DARK}; }}
        """

    def create_top_header(self):
        header = QFrame()
        header.setObjectName("topHeader")
        header.setFixedHeight(66)
        header.setStyleSheet(
            f"QFrame#topHeader {{ background:{SURFACE}; border:none; border-bottom:1px solid {BORDER}; }}"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        context = QVBoxLayout()
        context.setSpacing(0)
        self.header_page_label = QLabel(T("Dashboard"))
        self.header_page_label.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:700;")
        date_label = QLabel(format_current_date())
        date_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        context.addWidget(self.header_page_label)
        context.addWidget(date_label)
        layout.addLayout(context)
        layout.addStretch()

        language_combo = QComboBox()
        language_combo.addItems(list(LANGUAGES))
        language_combo.setCurrentText(language_name())
        language_combo.setFixedSize(132, 36)
        language_combo.setToolTip(T("Language"))
        language_combo.currentTextChanged.connect(self.change_language)
        layout.addWidget(language_combo)

        identity = QFrame()
        identity.setStyleSheet(
            f"QFrame {{ background:{SURFACE_SOFT}; border:1px solid {BORDER}; border-radius:8px; }}"
        )
        identity_layout = QHBoxLayout(identity)
        identity_layout.setContentsMargins(9, 5, 11, 5)
        identity_layout.setSpacing(8)
        avatar = QLabel((self.current_user.get("username") or "U")[:1].upper())
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background:{PRIMARY}; color:white; border-radius:14px; font-size:11px; font-weight:800;"
        )
        labels = QVBoxLayout()
        labels.setSpacing(0)
        username = QLabel(self.current_user.get("username", "").strip() or T("User"))
        username.setStyleSheet(f"color:{TEXT}; font-size:11px; font-weight:700;")
        role = QLabel(T("Admin" if self.current_role == "admin" else "Pharmacist"))
        role.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px;")
        labels.addWidget(username)
        labels.addWidget(role)
        identity_layout.addWidget(avatar)
        identity_layout.addLayout(labels)
        layout.addWidget(identity)
        return header

    def change_language(self, name):
        if name == language_name():
            return
        set_language(QApplication.instance(), name)
        replacement = MainWindow(self.current_user)
        replacement.showMaximized()
        self.replacement_window = replacement
        self.close()

    def set_active_button(self, active_name):
        translated_pages = {
            "Dashboard": T("Dashboard"),
            "Point of Sale": T("Point of Sale"),
            "Prescriptions": T("Prescriptions"),
            "Sales History": T("Sales History"),
            "Returned Items": T("Returned Items"),
            "Products": T("Products"),
            "Batch Management": T("Batch Management"),
            "Purchasing": T("Purchasing"),
            "Reports": T("Reports"),
            "Audit Logs": T("Audit Logs"),
            "POS Performance": T("POS Performance"),
            "Settings": T("Settings"),
        }
        self.header_page_label.setText(translated_pages.get(active_name, active_name))
        for name, button in self.sidebar_buttons.items():
            danger = bool(button.property("danger"))
            button.setStyleSheet(self.sidebar_button_style(name == active_name, danger))

    def _show(self, name, page, refresh=None):
        self.set_active_button(name)
        if refresh:
            refresh()
        self.stack.setCurrentWidget(page)

    def navigate_to(self, destination):
        handlers = {
            "pos": self.show_pos,
            "batches": self.show_batch_management,
            "reports": self.show_reports,
            "prescriptions": self.show_prescriptions,
            "sales": self.show_sales_history,
        }
        handler = handlers.get(destination)
        if handler:
            handler()

    def show_dashboard(self):
        self._show("Dashboard", self.dashboard_page, self.dashboard_page.refresh_data)

    def show_batch_management(self):
        page = self._page("batches", lambda: BatchManagementPage(current_user=self.current_user))
        page.reload_filters()
        self._show("Batch Management", page, page.refresh_table)

    def show_purchasing(self):
        if self.current_role == "admin":
            page = self._page("purchasing", lambda: PurchasingPage(current_user=self.current_user))
            self._show("Purchasing", page, page.refresh)

    def show_performance(self):
        if self.current_role == "admin":
            page = self._page("performance", lambda: PerformancePage(current_user=self.current_user))
            self._show("POS Performance", page, page.refresh)

    def show_pos(self):
        page = self._page("pos", lambda: POSPage(current_user=self.current_user))
        page.refresh_filters()
        self._show("Point of Sale", page, page.refresh_products)

    def show_product(self):
        page = self._page("products", lambda: ProductPage(role=self.current_role, current_user=self.current_user))
        page.reload_filters()
        self._show("Products", page, page.refresh_table)

    def show_prescriptions(self):
        page = self._page("prescriptions", lambda: PrescriptionsPage(role=self.current_role))
        self._show("Prescriptions", page, page.refresh_table)

    def show_sales_history(self):
        page = self._page("sales", lambda: SalesHistoryPage(current_user=self.current_user))
        self._show("Sales History", page, page.refresh_table)

    def show_returned_items(self):
        page = self._page("returns", lambda: ReturnedItemsPage(current_user=self.current_user))
        self._show("Returned Items", page, page.refresh_table)

    def show_reports(self):
        page = self._page("reports", lambda: ReportsPage(current_user=self.current_user))
        self._show("Reports", page, page.refresh)

    def show_audit_logs(self):
        page = self._page("audit", AuditLogsPage)
        self._show("Audit Logs", page, page.refresh_table)

    def show_settings(self):
        page = self._page("settings", lambda: SettingsPage(current_user=self.current_user))
        self._show("Settings", page)

    def logout(self):
        answer = QMessageBox.question(
            self,
            T("Confirm logout"),
            T("Are you sure you want to log out?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        from login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.showMaximized()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow({"username": "admin", "role": "admin"})
    window.showMaximized()
    sys.exit(app.exec())
