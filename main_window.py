import sys
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pages.dashboard import DashboardPage
from pages.batch_management import BatchManagementPage
from pages.pos import POSPage
from pages.settings import SettingsPage
from pages.sales_history import SalesHistoryPage
from pages.returned_items import ReturnedItemsPage
from pages.product import ProductPage
from pages.prescriptions import PrescriptionsPage
from pages.audit_logs import AuditLogsPage
from ui_theme import (
    BORDER,
    CANVAS,
    SURFACE,
    SURFACE_SOFT,
    TEXT,
    TEXT_MUTED,
    page_title_style,
)

class MainWindow(QWidget):
    def __init__(self, user):
        super().__init__()

        self.current_user = user
        self.current_role = (user.get("role") or "admin").lower()

        self.role_styles = {
            "admin": {
                "accent": "#16a34a",
                "active_bg": "#ecfdf5",
                "active_border": "#86efac",
                "mode_text": "Administrator Mode",
            },
            "pharmacist": {
                "accent": "#dc2626",
                "active_bg": "#fef2f2",
                "active_border": "#fca5a5",
                "mode_text": "Pharmacist Mode",
            },
        }


        self.role_style = self.role_styles.get(self.current_role, self.role_styles["admin"])

        self.setWindowTitle("Khalis Dawa")
        self.showMaximized()

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar_buttons = {}
        sidebar = self.create_sidebar()

        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self.create_top_header())

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.batch_management_page = BatchManagementPage(current_user=self.current_user)
        self.pos_page = POSPage(current_user=self.current_user)
        self.product_page = ProductPage(role=self.current_role, current_user=self.current_user)

        self.prescriptions_page = PrescriptionsPage(role=self.current_role)
        self.sales_history_page = SalesHistoryPage(current_user=self.current_user)
        self.audit_logs_page = AuditLogsPage()
        self.returned_items_page = ReturnedItemsPage(current_user=self.current_user)
        self.settings_page = SettingsPage(current_user=self.current_user)


        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.batch_management_page)
        self.stack.addWidget(self.pos_page)
        self.stack.addWidget(self.product_page)
        self.stack.addWidget(self.prescriptions_page)
        self.stack.addWidget(self.sales_history_page)
        self.stack.addWidget(self.audit_logs_page)
        self.stack.addWidget(self.returned_items_page)
        self.stack.addWidget(self.settings_page)


        content_layout.addWidget(self.stack)
        content.setLayout(content_layout)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content)

        self.setLayout(root_layout)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CANVAS};
                color: {TEXT};
            }}

            QWidget#content {{
                background-color: {CANVAS};
            }}
        """)

        self.show_dashboard()

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(230)
        sidebar.setObjectName("sidebar")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        logo_label = QLabel()
        logo_label.setFixedSize(44, 44)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setText("+")
        logo_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.role_style['accent']};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 24px;
                font-weight: 800;
                padding-left: 2px;
                padding-bottom: 1px;
            }}
        """)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)

        app_name = QLabel("Khalis Dawa")
        app_name.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 18px;
                font-weight: 800;
                background: transparent;
            }
        """)

        mode = QLabel(self.role_style["mode_text"])
        mode.setStyleSheet(f"""
            QLabel {{
                color: {self.role_style['accent']};
                font-size: 12px;
                font-weight: 700;
                background: transparent;
            }}
        """)

        brand_row.addWidget(logo_label)
        brand_text.addWidget(app_name)
        brand_text.addWidget(mode)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()

        layout.addLayout(brand_row)
        layout.addSpacing(18)

        menu_items = [
            ("Dashboard", "", self.show_dashboard, True),
            ("Batch Management", "", self.show_batch_management, True),
            ("Point of Sale", "", self.show_pos, True),
            ("Product", "", self.show_product, True),
            ("Prescriptions", "", self.show_prescriptions, True),
            ("Sales History", "", self.show_sales_history, True),
            ("Returned Items", "", self.show_returned_items, True),
            ("Audit Logs", "", self.show_audit_logs, True),
        ]


        if self.current_role == "admin":
            menu_items.append(("Settings", "", self.show_settings, True))

        for text, icon, handler, enabled in menu_items:
            button = self.create_sidebar_button(text, icon, enabled)
            if handler:
                button.clicked.connect(handler)
            layout.addWidget(button)
            self.sidebar_buttons[text] = button

        layout.addStretch()

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(separator)
        layout.addSpacing(12)

        logout_btn = self.create_sidebar_button("Logout", "", True, danger=True)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        self.sidebar_buttons["Logout"] = logout_btn

        sidebar.setLayout(layout)
        sidebar.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {SURFACE};
                border-right: 1px solid {BORDER};
            }}
        """)

        return sidebar

    def create_sidebar_button(self, text, icon="", enabled=True, danger=False):
        button_text = f"{icon}   {text}" if icon else text

        button = QPushButton(button_text)
        button.setFixedHeight(40)
        button.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )
        button.setEnabled(enabled)
        button.setProperty("danger", danger)
        button.setStyleSheet(self.sidebar_button_style(active=False, danger=danger))
        return button

    def sidebar_button_style(self, active=False, danger=False):
        if active:
            return f"""
                QPushButton {{
                    background-color: {self.role_style['active_bg']};
                    color: {self.role_style['accent']};
                    border: 1px solid {self.role_style['active_border']};
                    border-radius: 10px;
                    padding: 10px 12px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 700;
                }}
            """

        if danger:
            return """
                QPushButton {
                    background-color: transparent;
                    color: #dc2626;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 12px;
                    text-align: center;
                    font-size: 13px;
                    font-weight: 700;
                }

                QPushButton:hover {
                    background-color: #dc2626;
                    color: white;
                }

                QPushButton:pressed {
                    background-color: #b91c1c;
                    color: white;
                }

                QPushButton:disabled {
                    background-color: transparent;
                    color: #dc2626;
                }
            """

        return """
            QPushButton {
                background-color: transparent;
                color: #475569;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #eef4fb;
            }

            QPushButton:disabled {
                background-color: transparent;
                color: #475569;
            }
        """

    def create_top_header(self):
        header = QWidget()
        header.setFixedHeight(72)
        header.setObjectName("topHeader")

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 24, 0)
        layout.setSpacing(14)

        date_label = QLabel(datetime.now().strftime("%A, %B %d, %Y"))
        date_label.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 15px;
                font-weight: 700;
                background: transparent;
            }
        """)

        user_chip = QLabel(self.current_user.get("username", "").strip() or "User")
        user_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_chip.setStyleSheet(f"""
            QLabel {{
                background-color: {SURFACE_SOFT};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 999px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
            }}
        """)

        role_mode_label = QLabel(self.role_style["mode_text"])
        role_mode_label.setStyleSheet(f"""
            QLabel {{
                color: {self.role_style['accent']};
                font-size: 12px;
                font-weight: 700;
                background: transparent;
            }}
        """)

        layout.addWidget(date_label)
        layout.addStretch()
        layout.addWidget(user_chip)
        layout.addWidget(role_mode_label)

        header.setLayout(layout)
        header.setStyleSheet(f"""
            QWidget#topHeader {{
                background-color: {SURFACE};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        return header

    def set_active_button(self, active_name):
        for name, button in self.sidebar_buttons.items():
            danger = bool(button.property("danger"))
            button.setStyleSheet(
                self.sidebar_button_style(active=name == active_name, danger=danger)
            )

    def show_dashboard(self):
        self.set_active_button("Dashboard")
        self.dashboard_page.refresh_data()
        self.stack.setCurrentWidget(self.dashboard_page)

    def show_batch_management(self):
        self.set_active_button("Batch Management")
        self.batch_management_page.reload_filters()
        self.batch_management_page.refresh_table()
        self.stack.setCurrentWidget(self.batch_management_page)

    def show_pos(self):
        self.set_active_button("Point of Sale")
        self.pos_page.refresh_filters()
        self.pos_page.refresh_products()
        self.stack.setCurrentWidget(self.pos_page)

    def show_product(self):
        self.set_active_button("Product")
        self.product_page.reload_filters()
        self.product_page.refresh_table()
        self.stack.setCurrentWidget(self.product_page)


    def show_sales_history(self):
        self.set_active_button("Sales History")
        self.sales_history_page.refresh_table()
        self.stack.setCurrentWidget(self.sales_history_page)

    def show_returned_items(self):
        self.set_active_button("Returned Items")
        self.returned_items_page.refresh_table()
        self.stack.setCurrentWidget(self.returned_items_page)

    def show_audit_logs(self):
        self.set_active_button("Audit Logs")
        self.audit_logs_page.refresh_table()
        self.stack.setCurrentWidget(self.audit_logs_page)

    def show_settings(self):
        self.set_active_button("Settings")
        self.stack.setCurrentWidget(self.settings_page)

    def show_prescriptions(self):
        self.set_active_button("Prescriptions")
        self.prescriptions_page.refresh_table()
        self.stack.setCurrentWidget(self.prescriptions_page)


    def logout(self):
        confirm = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        from login_window import LoginWindow

        self.login_window = LoginWindow()
        self.login_window.showMaximized()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    user = {"username": "admin", "role": "admin"}
    window = MainWindow(user)
    window.show()
    sys.exit(app.exec())
