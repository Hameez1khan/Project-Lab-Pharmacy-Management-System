APP_FONT = "Segoe UI"

CANVAS = "#f8faf9"
SURFACE = "#ffffff"
SURFACE_SOFT = "#f8fafc"
SURFACE_TINT = "#eef5ff"
BORDER = "#e7edf3"
BORDER_SOFT = "#f1f5f9"
TEXT = "#111827"
TEXT_MUTED = "#6b7280"
TEXT_SUBTLE = "#374151"

PRIMARY = "#22c55e"
PRIMARY_HOVER = "#16a34a"
BLUE = "#2563eb"
BLUE_HOVER = "#1d4ed8"
SUCCESS = "#16a34a"
SUCCESS_BG = "#ecfdf5"
DANGER = "#dc2626"
DANGER_BG = "#fff1f2"
WARNING = "#c2410c"
WARNING_BG = "#fff7ed"
PURPLE = "#7c3aed"
PURPLE_BG = "#f5f3ff"


def app_stylesheet():
    return ""


def page_root_style(object_name):
    return f"""
        QWidget#{object_name} {{
            background-color: {CANVAS};
        }}
    """


def page_title_style():
    return f"""
        QLabel {{
            color: {TEXT};
            font-size: 23px;
            font-weight: 800;
            background: transparent;
            border: none;
        }}
    """


def page_subtitle_style():
    return f"""
        QLabel {{
            color: {TEXT_MUTED};
            font-size: 14px;
            background: transparent;
            border: none;
        }}
    """


def surface_card_style(radius=12):
    return f"""
        QFrame {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: {radius}px;
        }}
    """


def filter_card_style():
    return surface_card_style(radius=12)


def table_container_style():
    return surface_card_style(radius=12)


def table_row_style():
    return f"""
        QFrame {{
            border-top: 1px solid {BORDER_SOFT};
            background-color: {SURFACE};
        }}
    """


def header_caps_style():
    return f"""
        QLabel {{
            color: #8b5e6b;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0;
        }}
    """


def primary_text_style():
    return f"""
        QLabel {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 700;
        }}
    """


def secondary_text_style():
    return f"""
        QLabel {{
            color: {TEXT_SUBTLE};
            font-size: 14px;
        }}
    """


def metric_text_style(color="#0f766e"):
    return f"""
        QLabel {{
            color: {color};
            font-size: 14px;
            font-weight: 700;
        }}
    """


def input_style():
    return f"""
        QLineEdit, QComboBox, QSpinBox {{
            background-color: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0 14px;
            color: {TEXT};
            font-size: 14px;
        }}

        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 1px solid {BLUE};
        }}

        QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
            background-color: {SURFACE_SOFT};
            color: #9ca3af;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 28px;
            background: transparent;
        }}

        QComboBox::down-arrow {{
            width: 10px;
            height: 10px;
        }}

        QComboBox QAbstractItemView {{
            background-color: white;
            border: 1px solid #e5e7eb;
            selection-background-color: #eef5ff;
            selection-color: {TEXT};
            outline: none;
            padding: 4px;
        }}

        QComboBox QAbstractItemView::item {{
            min-height: 32px;
            padding: 6px 10px;
            border-radius: 6px;
        }}
    """


def scroll_area_style():
    return """
        QScrollArea {
            background: transparent;
            border: none;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 6px 2px 6px 2px;
            border: none;
        }

        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 40px;
            border-radius: 5px;
        }

        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
            border: none;
            background: transparent;
        }

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: transparent;
        }

        QScrollBar:horizontal {
            background: transparent;
            height: 10px;
            margin: 2px 6px 2px 6px;
            border: none;
        }

        QScrollBar::handle:horizontal {
            background: #cbd5e1;
            min-width: 40px;
            border-radius: 5px;
        }

        QScrollBar::handle:horizontal:hover {
            background: #94a3b8;
        }

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0px;
            border: none;
            background: transparent;
        }

        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: transparent;
        }
    """


def primary_button_style(color=PRIMARY, hover=PRIMARY_HOVER):
    return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            padding: 0 14px;
        }}

        QPushButton:hover {{
            background-color: {hover};
        }}
    """


def soft_button_style():
    return """
        QPushButton {
            background-color: #f8fafc;
            border: 1px solid #dbe4ee;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            color: #111827;
            padding: 0 12px;
        }

        QPushButton:hover {
            background-color: #eef5ff;
        }
    """


def action_button_style():
    return """
        QPushButton {
            background-color: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            color: #2563eb;
            padding: 0 12px;
        }

        QPushButton:hover {
            background-color: #dbeafe;
        }
    """


def danger_button_style():
    return """
        QPushButton {
            background-color: #fff1f2;
            border: 1px solid #fecdd3;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            color: #dc2626;
            padding: 0 12px;
        }

        QPushButton:hover {
            background-color: #ffe4e6;
        }
    """


def checkbox_style(accent=BLUE):
    return f"""
        QCheckBox {{
            font-size: 14px;
            color: {TEXT_SUBTLE};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            background: white;
        }}

        QCheckBox::indicator:checked {{
            background-color: {accent};
            border: 1px solid {accent};
        }}
    """


def list_widget_style(mono=False):
    font_family = "Consolas" if mono else APP_FONT
    return f"""
        QListWidget {{
            background-color: white;
            border: none;
            outline: none;
            color: {TEXT_SUBTLE};
            font-size: 13px;
            font-family: {font_family};
        }}

        QListWidget::item {{
            border-bottom: 1px solid {BORDER_SOFT};
            padding: 10px 0;
        }}
    """


def badge_style(bg="#eef5ff", fg=BLUE):
    return f"""
        QLabel {{
            background-color: {bg};
            color: {fg};
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 700;
        }}
    """


def dialog_card_style():
    return f"""
        QFrame {{
            background-color: white;
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
    """


def message_style(success=True):
    if success:
        return """
            QLabel {
                color: #15803d;
                font-size: 13px;
            }
        """

    return """
        QLabel {
            color: #dc2626;
            font-size: 13px;
        }
    """
