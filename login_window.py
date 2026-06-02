from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from database.db import add_audit_log, authenticate_user, register_pharmacist
from main_window import MainWindow
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "icons" / "logo.png"


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.current_mode = "admin"

        self.setWindowTitle("Khalis Dawa")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 36, 40, 36)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setMinimumSize(560, 720)
        card.setMaximumWidth(620)
        card.setStyleSheet("""
            QFrame#loginCard {
                background-color: white;
                border-radius: 30px;
                border: 1px solid #dbe5f2;
            }
        """)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(48, 38, 48, 42)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logo = QLabel()
        logo.setFixedSize(68, 68)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        pixmap = QPixmap(str(LOGO_PATH))
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    52,
                    52,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        brand = QLabel("Khalis Dawa")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("""
            QLabel {
                font-size: 34px;
                font-weight: 800;
                color: #0f172a;
                background: transparent;
                border: none;
            }
        """)

        title = QLabel("Log in")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setMinimumHeight(64)
        title.setStyleSheet("""
            QLabel {
                font-size: 38px;
                font-weight: 400;
                color: #111827;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("Use your Khalis Dawa account")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 400;
                color: #334155;
                background: transparent;
                border: none;
            }
        """)

        info = QLabel(
            "Staff-only access for administrators and pharmacists. "
            "Choose the account type above, then continue with your credentials."
        )
        info.setWordWrap(True)
        info.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 14px;
                line-height: 1.4;
                background: transparent;
                border: none;
            }
        """)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        self.admin_mode_btn = QPushButton("Admin")
        self.admin_mode_btn.setFixedHeight(48)
        self.admin_mode_btn.clicked.connect(lambda: self.set_mode("admin"))

        self.pharmacist_mode_btn = QPushButton("Pharmacist")
        self.pharmacist_mode_btn.setFixedHeight(48)
        self.pharmacist_mode_btn.clicked.connect(lambda: self.set_mode("pharmacist"))

        mode_row.addWidget(self.admin_mode_btn)
        mode_row.addWidget(self.pharmacist_mode_btn)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(58)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(58)

        helper = QLabel("Switch to Pharmacist mode to create a pharmacist account.")
        helper.setWordWrap(True)
        helper.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 14px;
                background: transparent;
                border: none;
            }
        """)

        self.login_button = QPushButton("Proceed")
        self.login_button.setFixedHeight(52)
        self.login_button.setFixedWidth(168)
        self.login_button.clicked.connect(self.login)

        self.register_button = QPushButton("Create account")
        self.register_button.setFixedHeight(52)
        self.register_button.clicked.connect(self.register_user)

        input_style = """
            QLineEdit {
                background-color: #fbfdff;
                border: 1px solid #c9d5e7;
                border-radius: 14px;
                padding: 0 18px;
                font-size: 18px;
                color: #111827;
            }

            QLineEdit:focus {
                border: 1px solid #2563eb;
                background-color: white;
            }
        """

        self.username_input.setStyleSheet(input_style)
        self.password_input.setStyleSheet(input_style)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 24px;
                font-weight: 700;
                font-size: 16px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2563eb;
                border: none;
                border-radius: 20px;
                font-weight: 700;
                font-size: 16px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #eff6ff;
            }
        """)

        action_row = QHBoxLayout()
        action_row.setSpacing(14)
        action_row.addStretch()
        action_row.addWidget(self.register_button)
        action_row.addWidget(self.login_button)

        header_block = QVBoxLayout()
        header_block.setSpacing(8)
        header_block.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        header_block.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        header_block.addWidget(brand)
        header_block.addWidget(title)
        header_block.addWidget(subtitle)

        card_layout.addLayout(header_block)
        card_layout.addSpacing(14)
        card_layout.addLayout(mode_row)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(helper)
        card_layout.addSpacing(10)
        card_layout.addWidget(info)
        card_layout.addStretch()
        card_layout.addLayout(action_row)

        card.setLayout(card_layout)
        main_layout.addWidget(card)

        self.setLayout(main_layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #edf2fa;
            }
        """)

        self.set_mode("admin")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

    def set_mode(self, mode):
        self.current_mode = mode

        active_style = """
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: 1px solid #2563eb;
                border-radius: 16px;
                font-weight: 700;
                font-size: 15px;
            }
        """

        inactive_style = """
            QPushButton {
                background-color: #fbfdff;
                color: #2563eb;
                border: 1px solid #c9d5e7;
                border-radius: 16px;
                font-weight: 700;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #eff6ff;
            }
        """

        self.admin_mode_btn.setStyleSheet(active_style if mode == "admin" else inactive_style)
        self.pharmacist_mode_btn.setStyleSheet(active_style if mode == "pharmacist" else inactive_style)

        self.register_button.setVisible(mode == "pharmacist")

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        user = authenticate_user(username, password)

        if user is None:
            QMessageBox.critical(self, "Error", "Invalid username or password")
            return

        if self.current_mode == "admin" and user["role"] != "admin":
            QMessageBox.critical(self, "Error", "Please use Pharmacist mode for pharmacist accounts")
            return

        if self.current_mode == "pharmacist" and user["role"] != "pharmacist":
            QMessageBox.critical(self, "Error", "Please use Admin mode for admin account")
            return

        add_audit_log(
            user["username"],
            "Signed in",
            role=user["role"]
        )

        self.main_window = MainWindow(user)
        self.main_window.showMaximized()
        self.close()

    def register_user(self):
        if self.current_mode != "pharmacist":
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        success, message = register_pharmacist(username, password)

        if not success:
            QMessageBox.critical(self, "Registration Failed", message)
            return

        QMessageBox.information(self, "Registration", message)
        self.username_input.clear()
        self.password_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.showMaximized()
    sys.exit(app.exec())
