"""Shared visual system for the Khalis Dawa desktop application."""

APP_FONT = "Segoe UI"

CANVAS = "#f4f7f5"
SURFACE = "#ffffff"
SURFACE_SOFT = "#f7faf8"
SURFACE_TINT = "#eaf4ef"
SIDEBAR = "#fbfcfb"

BORDER = "#dfe8e3"
BORDER_SOFT = "#edf2ef"
TEXT = "#18251f"
TEXT_MUTED = "#68776f"
TEXT_SUBTLE = "#43534b"

PRIMARY = "#147a61"
PRIMARY_HOVER = "#0f654f"
PRIMARY_DARK = "#0b3f32"
PRIMARY_SOFT = "#e8f4ef"
BLUE = "#2f6f8f"
BLUE_HOVER = "#255b76"
SUCCESS = "#21845f"
SUCCESS_BG = "#eaf7f1"
DANGER = "#c84b4b"
DANGER_BG = "#fff0f0"
WARNING = "#b97818"
WARNING_BG = "#fff7e8"
PURPLE = "#7357a8"
PURPLE_BG = "#f3effa"
INFO = "#2f6f8f"
INFO_BG = "#edf6fa"

RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 8
CONTROL_HEIGHT = 40


def app_stylesheet():
    """Application-wide baseline for every native Qt control."""
    return f"""
        * {{ font-family: \"{APP_FONT}\"; outline: none; }}
        QWidget {{ color: {TEXT}; }}
        QToolTip {{ background:{PRIMARY_DARK}; color:white; border:none; border-radius:4px;
            padding:6px 8px; font-size:12px; }}

        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox,
        QDoubleSpinBox, QDateEdit {{
            background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
            border-radius:{RADIUS_SM}px; padding:0 12px; font-size:13px; min-height:38px;
            selection-background-color:{PRIMARY}; selection-color:white;
        }}
        QTextEdit, QPlainTextEdit {{ padding:9px 12px; }}
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
        QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{ border-color:#b7c9bf; }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
            border:2px solid {PRIMARY}; padding-left:11px; padding-right:11px;
        }}
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
        QDoubleSpinBox:disabled, QDateEdit:disabled {{
            background:#f0f3f1; color:#97a39d; border-color:{BORDER_SOFT};
        }}
        QComboBox::drop-down, QDateEdit::drop-down {{ border:none; width:28px; }}
        QComboBox QAbstractItemView {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
            padding:5px; selection-background-color:{PRIMARY_SOFT}; selection-color:{PRIMARY_DARK}; }}

        QPushButton {{ min-height:36px; border-radius:{RADIUS_SM}px; padding:0 14px;
            font-size:13px; font-weight:600; }}
        QPushButton:focus {{ border:2px solid #70b9a0; }}
        QPushButton:disabled {{ background:#e8edeb; color:#98a49e; border-color:#dfe6e2; }}

        QCheckBox, QRadioButton {{ spacing:8px; color:{TEXT_SUBTLE}; font-size:13px; }}
        QCheckBox::indicator, QRadioButton::indicator {{ width:16px; height:16px; }}

        QTableWidget, QTableView, QTreeWidget, QListWidget {{
            background:{SURFACE}; alternate-background-color:{SURFACE_SOFT}; color:{TEXT};
            border:1px solid {BORDER}; border-radius:{RADIUS_MD}px; gridline-color:{BORDER_SOFT};
            selection-background-color:{PRIMARY_SOFT}; selection-color:{PRIMARY_DARK};
        }}
        QHeaderView::section {{ background:#f6f9f7; color:{TEXT_MUTED}; border:none;
            border-bottom:1px solid {BORDER}; padding:10px 12px; font-size:11px; font-weight:700; }}
        QTableWidget::item, QTableView::item {{ padding:8px 10px; border-bottom:1px solid {BORDER_SOFT}; }}

        QTabWidget::pane {{ border:none; background:transparent; }}
        QTabBar::tab {{ background:transparent; color:{TEXT_MUTED}; border:none;
            border-bottom:2px solid transparent; padding:10px 16px; font-weight:600; }}
        QTabBar::tab:selected {{ color:{PRIMARY}; border-bottom-color:{PRIMARY}; }}

        QScrollBar:vertical {{ background:transparent; width:9px; margin:4px 2px; }}
        QScrollBar::handle:vertical {{ background:#bfcbc5; min-height:36px; border-radius:4px; }}
        QScrollBar::handle:vertical:hover {{ background:#96a89f; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
        QScrollBar:horizontal {{ background:transparent; height:9px; margin:2px 4px; }}
        QScrollBar::handle:horizontal {{ background:#bfcbc5; min-width:36px; border-radius:4px; }}
        QScrollBar::handle:horizontal:hover {{ background:#96a89f; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}

        QDialog, QMessageBox {{ background:{CANVAS}; }}
        QMenu {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
            border-radius:{RADIUS_SM}px; padding:5px; }}
        QMenu::item {{ padding:8px 20px; border-radius:4px; }}
        QMenu::item:selected {{ background:{PRIMARY_SOFT}; color:{PRIMARY_DARK}; }}
    """


def page_root_style(object_name):
    return f"QWidget#{object_name} {{ background-color:{CANVAS}; }}"


def page_title_style():
    return f"QLabel {{ color:{TEXT}; font-size:24px; font-weight:700; background:transparent; border:none; }}"


def page_subtitle_style():
    return f"QLabel {{ color:{TEXT_MUTED}; font-size:13px; background:transparent; border:none; }}"


def surface_card_style(radius=RADIUS_LG):
    return f"QFrame {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:{radius}px; }}"


def filter_card_style():
    return surface_card_style()


def table_container_style():
    return surface_card_style()


def table_row_style():
    return f"QFrame {{ border:none; border-bottom:1px solid {BORDER_SOFT}; background:{SURFACE}; }}"


def header_caps_style():
    return f"QLabel {{ color:{TEXT_MUTED}; font-size:11px; font-weight:700; background:transparent; border:none; }}"


def primary_text_style():
    return f"QLabel {{ color:{TEXT}; font-size:13px; font-weight:700; background:transparent; border:none; }}"


def secondary_text_style():
    return f"QLabel {{ color:{TEXT_SUBTLE}; font-size:13px; background:transparent; border:none; }}"


def metric_text_style(color=PRIMARY):
    return f"QLabel {{ color:{color}; font-size:14px; font-weight:700; background:transparent; border:none; }}"


def input_style():
    return f"""
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
            background:{SURFACE}; border:1px solid {BORDER}; border-radius:{RADIUS_SM}px;
            padding:0 12px; color:{TEXT}; font-size:13px; min-height:38px;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
        QDoubleSpinBox:focus, QDateEdit:focus {{ border:2px solid {PRIMARY}; }}
        QComboBox::drop-down, QDateEdit::drop-down {{ border:none; width:28px; }}
        QComboBox QAbstractItemView {{ background:{SURFACE}; border:1px solid {BORDER};
            selection-background-color:{PRIMARY_SOFT}; selection-color:{PRIMARY_DARK}; padding:4px; }}
    """


def scroll_area_style():
    return "QScrollArea { background:transparent; border:none; }"


def primary_button_style(color=PRIMARY, hover=PRIMARY_HOVER):
    return f"""
        QPushButton {{ background:{color}; color:white; border:none; border-radius:{RADIUS_SM}px;
            font-size:13px; font-weight:700; padding:0 16px; min-height:38px; }}
        QPushButton:hover {{ background:{hover}; }}
        QPushButton:pressed {{ background:{PRIMARY_DARK}; }}
        QPushButton:disabled {{ background:#dce5e1; color:#8b9992; }}
    """


def soft_button_style():
    return f"""
        QPushButton {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:{RADIUS_SM}px;
            font-size:12px; font-weight:700; color:{TEXT}; padding:0 13px; min-height:36px; }}
        QPushButton:hover {{ background:{PRIMARY_SOFT}; border-color:#b9d4c8; color:{PRIMARY_DARK}; }}
    """


def action_button_style():
    return f"""
        QPushButton {{ background:{PRIMARY_SOFT}; border:1px solid #c7dfd4; border-radius:{RADIUS_SM}px;
            font-size:12px; font-weight:700; color:{PRIMARY}; padding:0 13px; min-height:36px; }}
        QPushButton:hover {{ background:#d9eee5; border-color:#9fc9b7; }}
    """


def danger_button_style():
    return f"""
        QPushButton {{ background:{DANGER_BG}; border:1px solid #efcaca; border-radius:{RADIUS_SM}px;
            font-size:12px; font-weight:700; color:{DANGER}; padding:0 13px; min-height:36px; }}
        QPushButton:hover {{ background:#fbe2e2; border-color:#e8abab; }}
    """


def checkbox_style(accent=PRIMARY):
    return f"""
        QCheckBox {{ font-size:13px; color:{TEXT_SUBTLE}; spacing:8px; }}
        QCheckBox::indicator {{ width:16px; height:16px; border:1px solid #bdc9c3;
            border-radius:4px; background:white; }}
        QCheckBox::indicator:checked {{ background:{accent}; border-color:{accent}; }}
    """


def list_widget_style(mono=False):
    family = "Consolas" if mono else APP_FONT
    return f"""
        QListWidget {{ background:{SURFACE}; border:none; color:{TEXT_SUBTLE}; font-size:13px; font-family:{family}; }}
        QListWidget::item {{ border-bottom:1px solid {BORDER_SOFT}; padding:10px 0; }}
    """


def badge_style(bg=PRIMARY_SOFT, fg=PRIMARY):
    return f"QLabel {{ background:{bg}; color:{fg}; border:none; border-radius:10px; padding:4px 8px; font-size:11px; font-weight:700; }}"


def dialog_card_style():
    return surface_card_style()


def message_style(success=True):
    color = SUCCESS if success else DANGER
    background = SUCCESS_BG if success else DANGER_BG
    return f"QLabel {{ color:{color}; background:{background}; border-radius:{RADIUS_SM}px; padding:9px 11px; font-size:12px; }}"
