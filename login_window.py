from pathlib import Path
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from database.db import add_audit_log, authenticate_user, register_pharmacist
from i18n import LANGUAGES, T, language_name, set_language
from main_window import MainWindow
from ui_theme import (
    BORDER,
    CANVAS,
    DANGER,
    DANGER_BG,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_HOVER,
    PRIMARY_SOFT,
    SUCCESS,
    SUCCESS_BG,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    input_style,
    primary_button_style,
)


BASE_DIR = Path(__file__).resolve().parent
ICON_DIR = BASE_DIR / "assets" / "icons"
SHOW_PASSWORD_ICON = ICON_DIR / "show_pass.png"
HIDE_PASSWORD_ICON = ICON_DIR / "hide_pass.jpeg"


class LoginWindow(QWidget):
    """Role-aware sign-in experience with inline language selection."""

    def __init__(self):
        super().__init__()
        self.current_mode = "admin"
        self.password_visible = False

        self.setWindowTitle("Khalis Dawa")
        self.setMinimumSize(1040, 680)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self.setObjectName("loginWindow")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.brand_panel = self._build_brand_panel()
        self.form_panel = self._build_form_panel()
        root.addWidget(self.brand_panel, 5)
        root.addWidget(self.form_panel, 7)

        self.setStyleSheet(f"QWidget#loginWindow {{ background:{CANVAS}; }}")
        self.set_mode("admin")
        self.retranslate_ui()
        self.username_input.setFocus()

    def _build_brand_panel(self):
        panel = QFrame()
        panel.setObjectName("brandPanel")
        panel.setMinimumWidth(390)
        panel.setStyleSheet(f"""
            QFrame#brandPanel {{ background:{PRIMARY_DARK}; border:none; }}
            QLabel {{ background:transparent; border:none; color:white; }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(56, 46, 56, 46)
        layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("+")
        mark.setFixedSize(32, 32)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(f"background:{PRIMARY}; color:white; border-radius:8px; font-size:22px; font-weight:800;")
        name = QLabel("Khalis Dawa")
        name.setStyleSheet("font-size:17px; font-weight:700;")
        brand_row.addWidget(mark)
        brand_row.addWidget(name)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        layout.addStretch(2)

        self.brand_eyebrow = QLabel()
        self.brand_eyebrow.setStyleSheet(
            "color:#b7d8ca; font-size:11px; font-weight:700; padding:5px 0;"
        )
        self.brand_title = QLabel()
        self.brand_title.setWordWrap(True)
        self.brand_title.setMaximumWidth(440)
        self.brand_title.setStyleSheet("font-size:34px; font-weight:700; line-height:1.2;")
        self.brand_copy = QLabel()
        self.brand_copy.setWordWrap(True)
        self.brand_copy.setMaximumWidth(430)
        self.brand_copy.setStyleSheet("color:#b9d0c6; font-size:14px; line-height:1.5;")

        layout.addWidget(self.brand_eyebrow)
        layout.addWidget(self.brand_title)
        layout.addWidget(self.brand_copy)
        layout.addSpacing(24)

        assurance = QFrame()
        assurance.setStyleSheet(
            "QFrame { background:#164c3e; border:1px solid #2a6453; border-radius:10px; }"
        )
        assurance_layout = QHBoxLayout(assurance)
        assurance_layout.setContentsMargins(18, 16, 18, 16)
        assurance_layout.setSpacing(14)
        assurance_mark = QLabel(T("OK"))
        assurance_mark.setFixedSize(36, 36)
        assurance_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        assurance_mark.setStyleSheet(
            "background:#e8f4ef; color:#147a61; border-radius:18px; font-size:10px; font-weight:800;"
        )
        assurance_text = QVBoxLayout()
        assurance_text.setSpacing(2)
        self.assurance_title = QLabel()
        self.assurance_title.setStyleSheet("font-size:13px; font-weight:700;")
        self.assurance_copy = QLabel(
            "  |  ".join((T("FEFO inventory"), T("Audit history"), T("Local database")))
        )
        self.assurance_copy.setWordWrap(True)
        self.assurance_copy.setStyleSheet("color:#b9d0c6; font-size:11px;")
        assurance_text.addWidget(self.assurance_title)
        assurance_text.addWidget(self.assurance_copy)
        assurance_layout.addWidget(assurance_mark)
        assurance_layout.addLayout(assurance_text, 1)
        layout.addWidget(assurance)
        layout.addStretch(3)

        footer = QLabel(f"Khalis Dawa  |  {T('Pharmacy operations workspace')}")
        footer.setStyleSheet("color:#76998a; font-size:10px;")
        layout.addWidget(footer)
        return panel

    def _build_form_panel(self):
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setStyleSheet(f"QFrame#formPanel {{ background:{SURFACE}; border:none; }}")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(44, 28, 44, 36)
        outer.setSpacing(0)

        language_row = QHBoxLayout()
        language_row.addStretch()
        self.language_label = QLabel()
        self.language_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        self.language_combo = QComboBox()
        self.language_combo.addItems(list(LANGUAGES))
        self.language_combo.setCurrentText(language_name())
        self.language_combo.setFixedSize(150, 38)
        self.language_combo.setAccessibleName("Language")
        self.language_combo.setStyleSheet(input_style())
        self.language_combo.currentTextChanged.connect(self.change_language)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)
        outer.addLayout(language_row)
        outer.addStretch()

        form = QFrame()
        form.setMaximumWidth(520)
        form.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.setStyleSheet("QFrame { background:transparent; border:none; }")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        self.welcome_label = QLabel()
        self.welcome_label.setStyleSheet(f"color:{PRIMARY}; font-size:11px; font-weight:800;")
        self.title_label = QLabel()
        self.title_label.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:700;")
        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:13px;")
        form_layout.addWidget(self.welcome_label)
        form_layout.addWidget(self.title_label)
        form_layout.addWidget(self.subtitle_label)
        form_layout.addSpacing(14)

        mode_shell = QFrame()
        mode_shell.setStyleSheet(
            f"QFrame {{ background:{CANVAS}; border:1px solid {BORDER}; border-radius:8px; }}"
        )
        mode_layout = QHBoxLayout(mode_shell)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        mode_layout.setSpacing(4)
        self.admin_mode_btn = QPushButton()
        self.pharmacist_mode_btn = QPushButton()
        for button in (self.admin_mode_btn, self.pharmacist_mode_btn):
            button.setFixedHeight(38)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_mode_btn.clicked.connect(lambda: self.set_mode("admin"))
        self.pharmacist_mode_btn.clicked.connect(lambda: self.set_mode("pharmacist"))
        mode_layout.addWidget(self.admin_mode_btn)
        mode_layout.addWidget(self.pharmacist_mode_btn)
        form_layout.addWidget(mode_shell)
        form_layout.addSpacing(8)

        self.username_label = QLabel()
        self.password_label = QLabel()
        label_style = f"color:{TEXT}; font-size:12px; font-weight:700;"
        self.username_label.setStyleSheet(label_style)
        self.password_label.setStyleSheet(label_style)

        self.username_input = QLineEdit()
        self.username_input.setFixedHeight(46)
        self.username_input.setClearButtonEnabled(True)
        self.username_input.setStyleSheet(input_style())
        self.username_input.setAccessibleName("Username")

        password_shell = QFrame()
        password_shell.setFixedHeight(46)
        password_shell.setObjectName("passwordShell")
        password_shell.setStyleSheet(f"""
            QFrame#passwordShell {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:6px; }}
            QFrame#passwordShell:focus-within {{ border:2px solid {PRIMARY}; }}
        """)
        password_layout = QHBoxLayout(password_shell)
        password_layout.setContentsMargins(12, 0, 6, 0)
        password_layout.setSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; color:{TEXT}; font-size:13px; min-height:36px; padding:0; }}"
        )
        self.password_input.setAccessibleName("Password")
        self.password_input.returnPressed.connect(self.login)
        self.password_toggle = QPushButton()
        self.password_toggle.setFixedSize(34, 34)
        self.password_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.password_toggle.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:5px; padding:6px; }} "
            f"QPushButton:hover {{ background:{PRIMARY_SOFT}; }}"
        )
        self.password_toggle.clicked.connect(self.toggle_password)
        self._update_password_icon()
        password_layout.addWidget(self.password_input, 1)
        password_layout.addWidget(self.password_toggle)

        form_layout.addWidget(self.username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_label)
        form_layout.addWidget(password_shell)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        form_layout.addWidget(self.message_label)

        self.login_button = QPushButton()
        self.login_button.setFixedHeight(46)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setStyleSheet(primary_button_style())
        self.login_button.clicked.connect(self.login)
        form_layout.addSpacing(4)
        form_layout.addWidget(self.login_button)

        self.register_button = QPushButton()
        self.register_button.setFixedHeight(40)
        self.register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_button.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{PRIMARY}; border:none; font-size:12px; font-weight:700; }}
            QPushButton:hover {{ background:{PRIMARY_SOFT}; }}
        """)
        self.register_button.clicked.connect(self.register_user)
        form_layout.addWidget(self.register_button)

        self.helper_label = QLabel()
        self.helper_label.setWordWrap(True)
        self.helper_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.helper_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        form_layout.addWidget(self.helper_label)

        center = QHBoxLayout()
        center.addStretch()
        center.addWidget(form, 1)
        center.addStretch()
        outer.addLayout(center)
        outer.addStretch()
        return panel

    def retranslate_ui(self):
        self.brand_eyebrow.setText(T("Secure pharmacy workspace").upper())
        self.brand_title.setText(T("A healthier way to run your pharmacy."))
        self.brand_copy.setText(T(
            "Connected inventory. Confident dispensing. More time for the people who need you."
        ))
        self.assurance_title.setText(T("Secure pharmacy workspace"))
        self.language_label.setText(T("Language"))
        self.welcome_label.setText(T("Welcome back").upper())
        self.title_label.setText(T("Log in"))
        self.subtitle_label.setText(T("Sign in to continue to your workspace"))
        self.admin_mode_btn.setText(T("Admin"))
        self.pharmacist_mode_btn.setText(T("Pharmacist"))
        self.username_label.setText(T("Username"))
        self.password_label.setText(T("Password"))
        self.username_input.setPlaceholderText(T("Username"))
        self.password_input.setPlaceholderText(T("Password"))
        self.login_button.setText(T("Proceed"))
        self.register_button.setText(T("Create account"))
        self.helper_label.setText(T("Remembered on this device"))
        self._update_password_icon()
        self.set_mode(self.current_mode)

    def change_language(self, name):
        set_language(QApplication.instance(), name)
        self.setLayoutDirection(QApplication.instance().layoutDirection())
        self.retranslate_ui()

    def set_mode(self, mode):
        self.current_mode = mode
        active = f"""
            QPushButton {{ background:{SURFACE}; color:{PRIMARY_DARK}; border:1px solid #c9d9d1;
                border-radius:6px; font-size:12px; font-weight:700; }}
        """
        inactive = f"""
            QPushButton {{ background:transparent; color:{TEXT_MUTED}; border:1px solid transparent;
                border-radius:6px; font-size:12px; font-weight:600; }}
            QPushButton:hover {{ color:{PRIMARY}; background:{PRIMARY_SOFT}; }}
        """
        self.admin_mode_btn.setStyleSheet(active if mode == "admin" else inactive)
        self.pharmacist_mode_btn.setStyleSheet(active if mode == "pharmacist" else inactive)
        self.register_button.setVisible(mode == "pharmacist")
        self.clear_message()

    def _update_password_icon(self):
        icon_path = HIDE_PASSWORD_ICON if self.password_visible else SHOW_PASSWORD_ICON
        if icon_path.exists():
            self.password_toggle.setIcon(QIcon(str(icon_path)))
            self.password_toggle.setIconSize(self.password_toggle.size() * 0.48)
        self.password_toggle.setToolTip(T("Hide password") if self.password_visible else T("Show password"))

    def toggle_password(self):
        self.password_visible = not self.password_visible
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if self.password_visible else QLineEdit.EchoMode.Password
        )
        self._update_password_icon()

    def show_message(self, text, success=False):
        self.message_label.setText(text)
        self.message_label.setVisible(True)
        color = SUCCESS if success else DANGER
        background = SUCCESS_BG if success else DANGER_BG
        self.message_label.setStyleSheet(
            f"color:{color}; background:{background}; border-radius:6px; padding:9px 11px; font-size:12px;"
        )

    def clear_message(self):
        if hasattr(self, "message_label"):
            self.message_label.clear()
            self.message_label.setVisible(False)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.show_message(T("Please fill in all fields"))
            return

        self.login_button.setEnabled(False)
        QApplication.processEvents()
        try:
            user = authenticate_user(username, password)
        finally:
            self.login_button.setEnabled(True)

        if user is None:
            self.show_message(T("Invalid username or password"))
            self.password_input.selectAll()
            self.password_input.setFocus()
            return
        if self.current_mode == "admin" and user["role"] != "admin":
            self.show_message(T("Please use Pharmacist mode for pharmacist accounts"))
            return
        if self.current_mode == "pharmacist" and user["role"] != "pharmacist":
            self.show_message(T("Please use Admin mode for admin account"))
            return

        add_audit_log(user["username"], "Signed in", role=user["role"])
        self.main_window = MainWindow(user)
        self.main_window.showMaximized()
        self.close()

    def register_user(self):
        if self.current_mode != "pharmacist":
            return
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.show_message(T("Please fill in all fields"))
            return
        success, message = register_pharmacist(username, password)
        self.show_message(T(message), success)
        if success:
            self.username_input.clear()
            self.password_input.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.login()
            return
        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.showMaximized()
    sys.exit(app.exec())
