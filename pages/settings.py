from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QComboBox
)
from database.db import add_audit_log, get_connection, get_password_manageable_users

from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from ui_theme import (
    BORDER,
    PRIMARY,
    SURFACE_SOFT,
    TEXT,
    filter_card_style,
    input_style,
    message_style,
    page_subtitle_style,
    page_title_style,
    page_root_style,
    primary_button_style,
)


BASE_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = BASE_DIR / "assets" / "icons"

SHOW_PASSWORD_ICON = ICON_DIR / "show_pass.png"
HIDE_PASSWORD_ICON = ICON_DIR / "hide_pass.jpeg"


class SettingsPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.setObjectName("settingsPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(28)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        title = QLabel("Settings & profile")
        title.setStyleSheet(page_title_style().replace("30px", "28px"))

        subtitle = QLabel("Manage account passwords and access")
        subtitle.setStyleSheet(page_subtitle_style())

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        card = QFrame()
        card.setMaximumWidth(930)
        card.setMinimumHeight(560)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet(filter_card_style())

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 28)
        card_layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(88)
        header.setStyleSheet("""
            QWidget {
                background-color: white;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }
        """)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(28, 0, 28, 0)
        header_layout.setSpacing(12)

        lock_icon = QLabel("■")
        lock_icon.setFixedWidth(20)
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_icon.setStyleSheet("""
            QLabel {
                color: #22c55e;
                font-size: 20px;
                font-weight: 700;
                border: none;
            }
        """)

        header_text = QLabel("Password Management")
        header_text.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: 700;
                color: #111827;
                border: none;
            }
        """)

        header_layout.addWidget(lock_icon)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        header.setLayout(header_layout)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("""
            QFrame {
                background-color: #f1f5f9;
                border: none;
            }
        """)

        card_layout.addWidget(header)
        card_layout.addWidget(separator)

        form_area = QWidget()
        form_area.setStyleSheet("border: none; background-color: white;")

        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(32, 36, 32, 0)
        form_layout.setSpacing(24)

        target_user_box = QVBoxLayout()
        target_user_box.setSpacing(10)

        target_user_label = QLabel("Select User")
        target_user_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #111827;
                border: none;
            }
        """)

        self.user_selector = QComboBox()
        self.user_selector.addItems(get_password_manageable_users())
        self.user_selector.currentTextChanged.connect(self.handle_user_selection_change)

        self.user_selector.setFixedHeight(42)
        self.user_selector.setStyleSheet(input_style())

        target_user_box.addWidget(target_user_label)
        target_user_box.addWidget(self.user_selector)
        form_layout.addLayout(target_user_box)

        self.current_password, self.current_toggle = self.create_password_field(
            "Admin Current Password",
            "Enter admin current password"
        )

        self.new_password, self.new_toggle = self.create_password_field(
            "New Password",
            "Enter new password"
        )

        self.confirm_password, self.confirm_toggle = self.create_password_field(
            "Confirm New Password",
            "Confirm new password"
        )

        form_layout.addLayout(self.current_password["layout"])
        form_layout.addLayout(self.new_password["layout"])
        form_layout.addLayout(self.confirm_password["layout"])

        self.current_toggle.clicked.connect(
            lambda: self.toggle_password(self.current_password["field"], self.current_toggle)
        )
        self.new_toggle.clicked.connect(
            lambda: self.toggle_password(self.new_password["field"], self.new_toggle)
        )
        self.confirm_toggle.clicked.connect(
            lambda: self.toggle_password(self.confirm_password["field"], self.confirm_toggle)
        )

        self.handle_user_selection_change(self.user_selector.currentText())


        self.message_label = QLabel("")
        self.message_label.setVisible(False)
        self.message_label.setWordWrap(True)
        form_layout.addWidget(self.message_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.update_btn = QPushButton("Update Password")
        self.update_btn.setFixedSize(168, 44)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(primary_button_style(color=PRIMARY, hover="#0b5f5a"))
        self.update_btn.clicked.connect(self.change_password)

        button_layout.addWidget(self.update_btn)
        form_layout.addLayout(button_layout)

        form_area.setLayout(form_layout)
        card_layout.addWidget(form_area)

        card.setLayout(card_layout)
        main_layout.addWidget(card)

        self.setLayout(main_layout)

        self.setStyleSheet(page_root_style("settingsPage"))

    def create_password_field(self, label_text, placeholder_text):
        container = QVBoxLayout()
        container.setSpacing(10)

        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 700;
                color: #111827;
                border: none;
            }
        """)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(16, 0, 12, 0)
        input_row.setSpacing(8)

        field_shell = QFrame()
        field_shell.setFixedHeight(50)
        field_shell.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)

        shell_layout = QHBoxLayout()
        shell_layout.setContentsMargins(16, 0, 10, 0)
        shell_layout.setSpacing(8)

        field = QLineEdit()
        field.setPlaceholderText(placeholder_text)
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setFixedHeight(30)
        field.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                color: #111827;
                font-size: 14px;
                padding: 0;
            }

            QLineEdit::placeholder {
                color: #6b7280;
            }
        """)

        toggle_btn = QPushButton()
        toggle_btn.setFixedSize(36, 36)
        toggle_btn.setIcon(QIcon(str(SHOW_PASSWORD_ICON)))
        toggle_btn.setIconSize(toggle_btn.size() * 0.45)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background-color: transparent;
                border-radius: 10px;
            }}

            QPushButton:hover {{
                background-color: {SURFACE_SOFT};
            }}
        """)

        shell_layout.addWidget(field)
        shell_layout.addWidget(toggle_btn)
        field_shell.setLayout(shell_layout)
        input_row.addWidget(field_shell)

        container.addWidget(label)
        container.addLayout(input_row)

        return {
            "layout": container,
            "field": field,
            "label": label,
        }, toggle_btn


    def toggle_password(self, field, button):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setIcon(QIcon(str(HIDE_PASSWORD_ICON)))
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            button.setIcon(QIcon(str(SHOW_PASSWORD_ICON)))

    def show_message(self, text, success=True):
        self.message_label.setVisible(True)
        self.message_label.setText(text)

        if success:
            self.message_label.setStyleSheet(message_style(True))
        else:
            self.message_label.setStyleSheet(message_style(False))

    def change_password(self):
        target_user = self.user_selector.currentText().strip()
        current = self.current_password["field"].text()
        new = self.new_password["field"].text()
        confirm = self.confirm_password["field"].text()

        if not current or not new or not confirm:
            self.show_message("Please fill in all fields", False)
            return

        if new != confirm:
            self.show_message("New passwords do not match", False)
            return

        if len(new) < 4:
            self.show_message("Password must be at least 4 characters long", False)
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM users WHERE username = ?", (target_user,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            self.show_message("Selected user account not found", False)
            return

        if current != result[0]:
            conn.close()
            selected_role = self.get_selected_user_role()
            if selected_role == "admin":
                self.show_message("Admin current password is incorrect", False)
            else:
                self.show_message("Pharmacist current password is incorrect", False)
            return

        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (new, target_user)
        )

        add_audit_log(
            self.current_user.get("username") or "admin",
            f"Updated password for {target_user}",
            role=self.current_user.get("role"),
            conn=conn,
            cursor=cursor
        )

        conn.commit()
        conn.close()

        self.show_message(f"Password updated successfully for {target_user}.", True)

        self.current_password["field"].clear()
        self.new_password["field"].clear()
        self.confirm_password["field"].clear()

    def handle_user_selection_change(self, _selected_text=""):
        self.current_password["field"].clear()
        if hasattr(self, "message_label"):
            self.message_label.setVisible(False)
        self.update_current_password_label()

    def get_selected_user_role(self):
        selected_user = self.user_selector.currentText().strip()
        if not selected_user:
            return ""

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ?", (selected_user,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return ""

        return str(row["role"] or "").strip().lower()

    def update_current_password_label(self):
        selected_role = self.get_selected_user_role()

        if selected_role == "admin":
            self.current_password["label"].setText("Admin Current Password")
            self.current_password["field"].setPlaceholderText("Enter admin current password")
        else:
            self.current_password["label"].setText("Pharmacist Current Password")
            self.current_password["field"].setPlaceholderText("Enter pharmacist current password")

