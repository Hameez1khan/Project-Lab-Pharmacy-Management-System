from pathlib import Path
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from i18n import T, format_date, format_money

from database.db import (
    get_connection,
    get_dashboard_stats,
    get_expiring_soon,
    get_low_stock_products,
    get_recent_sales,
)
try:
    from database.db import get_dashboard_sales_trend
except ImportError:
    get_dashboard_sales_trend = None
from ui_theme import (
    BORDER,
    BORDER_SOFT,
    DANGER,
    DANGER_BG,
    INFO,
    INFO_BG,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SUCCESS,
    SUCCESS_BG,
    SURFACE_SOFT,
    TEXT,
    TEXT_MUTED,
    WARNING,
    WARNING_BG,
    badge_style,
    list_widget_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    surface_card_style,
)


BASE_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = BASE_DIR / "assets" / "icons"


class NetSalesChart(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_points(self, points):
        self.points = [
            (point.get("date"), point.get("net_sales", 0))
            if isinstance(point, dict) else tuple(point)
            for point in (points or [])
        ]
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        bounds = QRectF(54, 20, max(1, self.width() - 78), max(1, self.height() - 60))
        values = [max(0.0, float(point[1] or 0)) for point in self.points]
        if not values or max(values) <= 0:
            painter.setPen(QColor("#68776f"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, T("No sales activity in the last 30 days"))
            painter.end()
            return

        high = max(values)
        painter.setPen(QPen(QColor("#dfe8e3"), 1))
        for step in range(5):
            y = bounds.bottom() - bounds.height() * step / 4
            painter.drawLine(QPointF(bounds.left(), y), QPointF(bounds.right(), y))
            painter.setPen(QColor("#68776f"))
            painter.drawText(QRectF(0, y - 9, 48, 18), Qt.AlignmentFlag.AlignRight, f"{high * step / 4:,.0f}")
            painter.setPen(QPen(QColor("#dfe8e3"), 1))

        width = bounds.width() / max(1, len(values) - 1)
        path = QPainterPath()
        area = QPainterPath()
        coordinates = []
        for index, value in enumerate(values):
            point = QPointF(bounds.left() + index * width, bounds.bottom() - (value / high) * bounds.height())
            coordinates.append(point)
            path.moveTo(point) if index == 0 else path.lineTo(point)
        area.moveTo(bounds.left(), bounds.bottom())
        area.lineTo(coordinates[0])
        for point in coordinates[1:]:
            area.lineTo(point)
        area.lineTo(bounds.right(), bounds.bottom())
        area.closeSubpath()
        painter.fillPath(area, QColor(232, 244, 239, 190))
        painter.setPen(QPen(QColor(PRIMARY), 3))
        painter.drawPath(path)
        painter.setBrush(QColor(PRIMARY))
        painter.setPen(Qt.PenStyle.NoPen)
        for point in coordinates:
            painter.drawEllipse(point, 3.5, 3.5)

        painter.setPen(QColor("#68776f"))
        for index in sorted({0, len(self.points) // 2, len(self.points) - 1}):
            x = bounds.left() + index * width
            label_left = min(max(x - 45, bounds.left()), bounds.right() - 90)
            painter.drawText(QRectF(label_left, bounds.bottom() + 8, 90, 20),
                             Qt.AlignmentFlag.AlignCenter, format_date(self.points[index][0]))
        painter.end()


class DashboardPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.current_role = (self.current_user.get("role") or "admin").lower()

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
                background: #bfcbc5;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #96a89f;
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
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content.setMinimumWidth(0)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 28)
        main_layout.setSpacing(22)

        title = QLabel(T("Overview" if self.current_role == "admin" else "My workspace"))
        title.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 24px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel(T(
            "A clear picture of pharmacy operations"
            if self.current_role == "admin"
            else "Everything needed for today's shift"
        ))
        subtitle.setStyleSheet("""
            QLabel {
                color: #68776f;
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

        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(8)
        actions = (
            (("New sale", "pos"), ("Review batches", "batches"), ("View reports", "reports"))
            if self.current_role == "admin"
            else (("New sale", "pos"), ("View prescriptions", "prescriptions"), ("Sales history", "sales"))
        )
        for index, (label, destination) in enumerate(actions):
            button = QPushButton(T(label))
            button.setMinimumHeight(36)
            button.setProperty("primary", index == 0)
            button.clicked.connect(
                lambda _checked=False, key=destination: self.navigate_requested.emit(key)
            )
            quick_actions.addWidget(button)
        quick_actions.addStretch()
        main_layout.addLayout(quick_actions)

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(18)
        self.cards_layout.setVerticalSpacing(16)

        self.card_values = {}

        if self.current_role == "admin":
            cards = [
                ("Medicines", INFO, ICON_DIR / "Medicine.png", INFO_BG, 0, 0),
                ("Sales", SUCCESS, "$", SUCCESS_BG, 0, 1),
                ("Returned Items", "#7357a8", "R", "#f3effa", 0, 2),
                ("Expiration Alert", WARNING, "!", WARNING_BG, 1, 0),
                ("Low Stock", DANGER, "L", DANGER_BG, 1, 1),
                ("Revenue", PRIMARY, "Ft", PRIMARY_SOFT, 1, 2),
            ]
        else:
            cards = [
                ("Sales Today", SUCCESS, "$", SUCCESS_BG, 0, 0),
                ("Prescriptions Today", INFO, "Rx", INFO_BG, 0, 1),
                ("Returns Today", "#7357a8", "R", "#f3effa", 0, 2),
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

        chart_panel = QFrame()
        chart_panel.setStyleSheet(surface_card_style())
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(22, 18, 22, 18)
        chart_title = QLabel(T("Daily net sales - last 30 days"))
        chart_title.setStyleSheet(f"color:{TEXT};font-size:14px;font-weight:700;background:transparent")
        self.sales_chart = NetSalesChart()
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(self.sales_chart)
        main_layout.addWidget(chart_panel)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(18)

        self.low_stock_list = QListWidget()
        self.expiry_list = QListWidget()

        recent_panel = self.create_list_panel(
            title=T("Low Stock Products"),
            action_symbol="!",
            list_widget=self.low_stock_list,
            warning=True,
        )

        expiry_panel = self.create_list_panel(
            title=T("Batches expiring within 30 days"),
            action_symbol="!",
            list_widget=self.expiry_list,
            warning=True,
        )

        bottom_layout.addWidget(recent_panel, 1)
        bottom_layout.addWidget(expiry_panel, 1)
        main_layout.addLayout(bottom_layout)

        self.recent_sales_list = QListWidget()
        recent_sales_panel = self.create_list_panel(
            title=T("Recent transactions"),
            action_symbol="5",
            list_widget=self.recent_sales_list,
        )
        recent_sales_panel.setMinimumHeight(220)
        main_layout.addWidget(recent_sales_panel)

        content.setLayout(main_layout)
        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)

        self.setLayout(root_layout)
        self.setStyleSheet("""
            QWidget#dashboardPage {
                background-color: #f4f7f5;
            }
        """)

    def create_stat_card(self, label, value_color, icon, icon_bg):
        card = QFrame()
        card.setMinimumHeight(108)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dfe8e3;
                border-radius: 10px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(14)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title = QLabel(T(label))
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
                border-radius: 10px;
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
                border: 1px solid #dfe8e3;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()

        title_label = QLabel(T(title))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: #18251f;
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
                background-color: {"#fff7e8" if warning else SURFACE_SOFT};
                color: {"#b97818" if warning else PRIMARY};
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
                color: #18251f;
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
                background: #bfcbc5;
                min-height: 40px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #96a89f;
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
        if self.current_role == "pharmacist":
            self._refresh_pharmacist_stats()
            trend = get_dashboard_sales_trend(days=30) if get_dashboard_sales_trend else []
            self.sales_chart.set_points(trend)
            self.refresh_low_stock_products()
            self.refresh_expiring_soon()
            self.refresh_recent_sales()
            return

        medicines, sales, returned_items, expired, low_stock, revenue = get_dashboard_stats()

        self.card_values["Medicines"].setText(str(medicines))
        self.card_values["Sales"].setText(str(sales))
        self.card_values["Returned Items"].setText(str(returned_items))
        self.card_values["Expiration Alert"].setText(str(expired))
        self.card_values["Low Stock"].setText(str(low_stock))
        amount = f"{revenue:,.2f}".rstrip("0").rstrip(".")
        self.card_values["Revenue"].setText(f"{amount} Ft")
        self.card_values["Revenue"].setToolTip(T("All-time sales minus refunds"))

        trend = []
        if get_dashboard_sales_trend is not None:
            try:
                trend = get_dashboard_sales_trend(days=30)
            except Exception:
                trend = []
        self.sales_chart.set_points(trend)

        self.refresh_low_stock_products()
        self.refresh_expiring_soon()
        self.refresh_recent_sales()

    def refresh_recent_sales(self):
        self.recent_sales_list.clear()
        rows = get_recent_sales()
        if not rows:
            self.add_empty_item(self.recent_sales_list, T("No recent transactions."))
            return
        for row in rows:
            text = "   ".join((
                row["receipt_number"],
                format_date(row["sale_datetime"]),
                T("Cash") if row["payment_method"].lower() == "cash" else T("Card"),
                format_money(row["total_amount"]),
            ))
            item = QListWidgetItem(text)
            item.setSizeHint(item.sizeHint().expandedTo(item.sizeHint()))
            self.recent_sales_list.addItem(item)

    def _refresh_pharmacist_stats(self):
        conn = get_connection()
        sales = conn.execute(
            "SELECT COUNT(*) AS count FROM sales WHERE date(sale_datetime)=date('now')"
        ).fetchone()["count"]
        prescriptions = conn.execute(
            "SELECT COUNT(*) AS count FROM prescriptions WHERE date(created_at)=date('now')"
        ).fetchone()["count"]
        returns = conn.execute(
            "SELECT COUNT(*) AS count FROM returns WHERE date(return_datetime)=date('now')"
        ).fetchone()["count"]
        conn.close()
        self.card_values["Sales Today"].setText(str(sales))
        self.card_values["Prescriptions Today"].setText(str(prescriptions))
        self.card_values["Returns Today"].setText(str(returns))

    def refresh_low_stock_products(self):
        self.low_stock_list.clear()
        low_stock_products = get_low_stock_products()

        if not low_stock_products:
            self.add_empty_item(self.low_stock_list, T("No low stock products"))
            return

        header = QListWidgetItem()
        self.low_stock_list.addItem(header)
        header_item = self.low_stock_list.item(0)
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        header_widget = self._make_dashboard_table_header(
            [T("Product"), T("Available"), T("Min Required")],
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
            self.add_empty_item(self.expiry_list, T("No batches expiring soon"))
            return

        header = QListWidgetItem()
        self.expiry_list.addItem(header)
        header_item = self.expiry_list.item(0)
        header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        header_widget = self._make_dashboard_table_header(
            [T("Product"), T("Batch"), T("Expiry Date")],
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
            label = QLabel(T(text).upper())
            label.setStyleSheet("""
                QLabel {
                    color: #68776f;
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
                border-bottom: 1px solid #edf2ef;
            }
        """)
        layout = QGridLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(0)

        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        available_badge = self._make_value_badge(
            f"{available_units}",
            bg=WARNING_BG if available_units == 0 else INFO_BG,
            fg=WARNING if available_units == 0 else INFO,
        )

        minimum_badge = self._make_value_badge(
            f"{min_required_units}",
            bg="#f8fafc",
            fg="#43534b",
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
                border-bottom: 1px solid #edf2ef;
            }
        """)
        layout = QGridLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(0)

        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        batch_badge = self._make_value_badge(batch, bg=PRIMARY_SOFT, fg=PRIMARY)

        expiry_label = QLabel(format_date(expiry))
        expiry_label.setStyleSheet("""
            QLabel {
                color: #43534b;
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
