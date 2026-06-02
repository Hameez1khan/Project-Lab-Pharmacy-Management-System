from pathlib import Path
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from database.db import (
    get_dashboard_stats,
    get_expiring_soon,
    get_low_stock_products,
)
from ui_theme import (
    BORDER,
    BORDER_SOFT,
    PRIMARY,
    SURFACE_SOFT,
    TEXT,
    TEXT_MUTED,
    badge_style,
    list_widget_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    surface_card_style,
)


BASE_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = BASE_DIR / "assets" / "icons"


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("dashboardPage")

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 10px 4px 10px 0;
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
        """)

        content = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 28)
        main_layout.setSpacing(22)

        title = QLabel("Dashboard")
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("Home Page")
        subtitle.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        main_layout.addLayout(title_layout)

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(18)
        self.cards_layout.setVerticalSpacing(16)

        self.card_values = {}

        cards = [
            ("Medicines", "#2563eb", ICON_DIR / "Medicine.png", "#f3f6ff", 0, 0),
            ("Sales", "#16a34a", "$", "#effcf4", 0, 1),
            ("Returned Items", "#7c3aed", "R", "#f5f3ff", 0, 2),
            ("Expiration Alert", "#ea580c", "!", "#fff7ed", 1, 0),
            ("Low Stock", "#dc2626", "L", "#fff1f2", 1, 1),
            ("Revenue", "#0f766e", "Ft", "#effcf9", 1, 2),
        ]

        for label, value_color, icon, icon_bg, row, column in cards:
            card, value_label = self.create_stat_card(
                label=label,
                value_color=value_color,
                icon=icon,
                icon_bg=icon_bg,
            )
            self.cards_layout.addWidget(card, row, column)
            self.card_values[label] = value_label

        for column in range(3):
            self.cards_layout.setColumnStretch(column, 1)

        main_layout.addLayout(self.cards_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(18)

        self.low_stock_list = QListWidget()
        self.expiry_list = QListWidget()

        recent_panel = self.create_list_panel(
            title="Low Stock Products",
            action_symbol="!",
            list_widget=self.low_stock_list,
            warning=True,
        )

        expiry_panel = self.create_list_panel(
            title="Batches expiring within 30 days",
            action_symbol="!",
            list_widget=self.expiry_list,
            warning=True,
        )

        bottom_layout.addWidget(recent_panel, 1)
        bottom_layout.addWidget(expiry_panel, 1)
        main_layout.addLayout(bottom_layout)

        content.setLayout(main_layout)
        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)

        self.setLayout(root_layout)
        self.setStyleSheet("""
            QWidget#dashboardPage {
                background-color: #f8fafc;
            }
        """)

    def create_stat_card(self, label, value_color, icon, icon_bg):
        card = QFrame()
        card.setMinimumHeight(108)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dbe7f3;
                border-radius: 20px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(14)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title = QLabel(label)
        title.setStyleSheet(f"""
            QLabel {{
                color: #53627a;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)

        value = QLabel("0")
        value.setStyleSheet(f"""
            QLabel {{
                color: {value_color};
                font-size: 18px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)

        text_layout.addWidget(title)
        text_layout.addWidget(value)

        icon_label = QLabel()
        icon_label.setFixedSize(50, 50)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {icon_bg};
                color: {value_color};
                border: none;
                border-radius: 15px;
                padding: 8px;
                font-size: 17px;
                font-weight: 700;
            }}
        """)

        pixmap = QPixmap(str(icon))
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(
                    22,
                    22,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            icon_label.setText(str(icon))

        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(icon_label)

        card.setLayout(layout)
        return card, value

    def create_list_panel(self, title, action_symbol, list_widget, warning=False):
        panel = QFrame()
        panel.setMinimumHeight(342)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dbe7f3;
                border-radius: 20px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: #0f172a;
                font-size: 14px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)

        action = QLabel(action_symbol)
        action.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        action.setFixedSize(28, 28)
        action.setStyleSheet(f"""
            QLabel {{
                background-color: {"#fff7ed" if warning else SURFACE_SOFT};
                color: {"#ea580c" if warning else PRIMARY};
                border: 1px solid #f3e2c7;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)

        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(action)

        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: none;
                outline: none;
                color: #0f172a;
                font-size: 13px;
                font-family: "Segoe UI";
            }

            QListWidget::item {
                padding: 0px;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 6px 0 6px 0;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 40px;
                border-radius: 4px;
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
        """)



        layout.addLayout(header)
        layout.addWidget(list_widget)
        panel.setLayout(layout)

        return panel

    def refresh_data(self):
        medicines, sales, returned_items, expired, low_stock, revenue = get_dashboard_stats()

        self.card_values["Medicines"].setText(str(medicines))
        self.card_values["Sales"].setText(str(sales))
        self.card_values["Returned Items"].setText(str(returned_items))
        self.card_values["Expiration Alert"].setText(str(expired))
        self.card_values["Low Stock"].setText(str(low_stock))
        self.card_values["Revenue"].setText(f"{revenue:g} Ft")

        self.refresh_low_stock_products()
        self.refresh_expiring_soon()

    def refresh_low_stock_products(self):
        self.low_stock_list.clear()
        low_stock_products = get_low_stock_products()

        if not low_stock_products:
            self.add_empty_item(self.low_stock_list, "No low stock products")
            return

        header = QListWidgetItem()
        self.low_stock_list.addItem(header)
        header_item = self.low_stock_list.item(0)
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        header_widget = self._make_dashboard_table_header(
            ["Product", "Available", "Min Required"],
            [5, 2, 3],
        )
        header_item.setSizeHint(header_widget.sizeHint())
        self.low_stock_list.setItemWidget(header_item, header_widget)

        for name, available_units, min_required_units in low_stock_products:
            item = QListWidgetItem()
            row_widget = self._make_low_stock_row(name, available_units, min_required_units)
            item.setSizeHint(row_widget.sizeHint())
            self.low_stock_list.addItem(item)
            self.low_stock_list.setItemWidget(item, row_widget)




    def refresh_expiring_soon(self):
        self.expiry_list.clear()
        expiring = get_expiring_soon()

        if not expiring:
            self.add_empty_item(self.expiry_list, "No batches expiring soon")
            return

        header = QListWidgetItem()
        self.expiry_list.addItem(header)
        header_item = self.expiry_list.item(0)
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        header_widget = self._make_dashboard_table_header(
            ["Product", "Batch", "Expiry Date"],
            [5, 3, 3],
        )
        header_item.setSizeHint(header_widget.sizeHint())
        self.expiry_list.setItemWidget(header_item, header_widget)

        for name, batch, expiry in expiring:
            item = QListWidgetItem()
            row_widget = self._make_expiring_row(name, batch, expiry)
            item.setSizeHint(row_widget.sizeHint())
            self.expiry_list.addItem(item)
            self.expiry_list.setItemWidget(item, row_widget)


    def add_empty_item(self, list_widget, text):
        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setData(Qt.ItemDataRole.FontRole, self._list_body_font())
        list_widget.addItem(item)

    def _list_header_font(self):
        font = QFont("Segoe UI")
        font.setPointSize(9)
        font.setBold(True)
        return font

    def _list_body_font(self):
        font = QFont("Segoe UI")
        font.setPointSize(10)
        font.setBold(False)
        return font

    def _make_dashboard_table_header(self, labels, stretches):
        widget = QWidget()
        widget.setStyleSheet("background: transparent; border: none;")
        layout = QGridLayout()
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(0)

        for index, text in enumerate(labels):
            label = QLabel(text.upper())
            label.setStyleSheet("""
                QLabel {
                    color: #64748b;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 0px;
                    background: transparent;
                    border: none;
                }
            """)
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if index > 0:
                alignment = Qt.AlignmentFlag.AlignCenter
            layout.addWidget(label, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        widget.setLayout(layout)
        widget.setFixedHeight(42)
        return widget

    def _make_low_stock_row(self, name, available_units, min_required_units):
        widget = QWidget()
        widget.setObjectName("lowStockRow")
        widget.setStyleSheet("""
            QWidget#lowStockRow {
                background: transparent;
                border: none;
                border-bottom: 1px solid #edf2f7;
            }
        """)
        layout = QGridLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(0)

        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        available_badge = self._make_value_badge(
            f"{available_units}",
            bg="#fff7ed" if available_units == 0 else "#eff6ff",
            fg="#ea580c" if available_units == 0 else "#2563eb",
        )

        minimum_badge = self._make_value_badge(
            f"{min_required_units}",
            bg="#f8fafc",
            fg="#475569",
        )

        centered = Qt.AlignmentFlag.AlignVCenter
        layout.addWidget(name_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft | centered)
        layout.addWidget(available_badge, 0, 1, alignment=Qt.AlignmentFlag.AlignHCenter | centered)
        layout.addWidget(minimum_badge, 0, 2, alignment=Qt.AlignmentFlag.AlignHCenter | centered)
        layout.setColumnStretch(0, 5)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 3)

        widget.setLayout(layout)
        widget.setFixedHeight(64)
        return widget

    def _make_expiring_row(self, name, batch, expiry):
        widget = QWidget()
        widget.setObjectName("expiringRow")
        widget.setStyleSheet("""
            QWidget#expiringRow {
                background: transparent;
                border: none;
                border-bottom: 1px solid #edf2f7;
            }
        """)
        layout = QGridLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(0)

        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        batch_badge = self._make_value_badge(batch, bg="#eff6ff", fg="#2563eb")

        expiry_label = QLabel(expiry)
        expiry_label.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        centered = Qt.AlignmentFlag.AlignVCenter
        layout.addWidget(name_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft | centered)
        layout.addWidget(batch_badge, 0, 1, alignment=Qt.AlignmentFlag.AlignHCenter | centered)
        layout.addWidget(expiry_label, 0, 2, alignment=Qt.AlignmentFlag.AlignHCenter | centered)
        layout.setColumnStretch(0, 5)
        layout.setColumnStretch(1, 3)
        layout.setColumnStretch(2, 3)

        widget.setLayout(layout)
        widget.setFixedHeight(64)
        return widget

    def _make_value_badge(self, text, bg, fg):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: 14px;
                padding: 7px 12px;
                font-size: 12px;
                font-weight: 700;
            }}
        """)
        return label
