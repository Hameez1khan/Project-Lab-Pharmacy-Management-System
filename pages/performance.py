from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QHeaderView, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from database.performance import get_performance_statistics
from i18n import T, TF
from ui_theme import (
    BLUE, BORDER, CANVAS, SURFACE, SURFACE_SOFT, TEXT, TEXT_MUTED,
    page_subtitle_style, page_title_style, soft_button_style,
)


def display_metric_key(key):
    translated = T(key)
    return key.replace("_", " ").title() if translated == key else translated


class PerformancePage(QWidget):
    """Administrator-facing POS timing statistics, ready for sidebar integration."""

    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user or {}
        self.setObjectName("performancePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(12)

        title = QLabel(T("POS Performance"))
        title.setMinimumHeight(42)
        title.setStyleSheet(page_title_style())
        subtitle = QLabel(T("Measured checkout and interaction times from this device"))
        subtitle.setStyleSheet(page_subtitle_style())
        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(T("Period")))
        self.period = QComboBox()
        for label, days in (("Last 7 days", 7), ("Last 30 days", 30),
                            ("Last 90 days", 90), ("Last 365 days", 365)):
            self.period.addItem(T(label), days)
        self.period.setCurrentIndex(1)
        toolbar.addWidget(self.period)
        toolbar.addStretch()
        refresh = QPushButton(T("Refresh"))
        refresh.setStyleSheet(soft_button_style())
        refresh.clicked.connect(self.refresh)
        toolbar.addWidget(refresh)
        layout.addLayout(toolbar)

        self.metric_values = []
        cards = QGridLayout()
        for index, (caption, color) in enumerate((
            ("Checkout attempts", BLUE), ("Success rate", "#0f766e"),
            ("Median processing", "#7c3aed"), ("Processing P95", "#a84418"),
        )):
            card = QFrame()
            card.setObjectName("metricCard")
            box = QVBoxLayout(card)
            box.setContentsMargins(16, 12, 16, 12)
            label = QLabel(T(caption))
            label.setStyleSheet(page_subtitle_style())
            value = QLabel("-")
            value.setStyleSheet(
                f"background:transparent;color:{color};font-size:19px;font-weight:700"
            )
            box.addWidget(label)
            box.addWidget(value)
            card.setStyleSheet(
                f"QFrame#metricCard {{background:{SURFACE};border:1px solid {BORDER};"
                f"border-top:3px solid {color};border-radius:6px;}}"
            )
            cards.addWidget(card, 0, index)
            cards.setColumnStretch(index, 1)
            self.metric_values.append(value)
        layout.addLayout(cards)

        self.summary = QLabel()
        self.summary.setStyleSheet(page_subtitle_style())
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            T("Operation"), T("Phase"), T("Type"), T("Count"), T("Average (ms)"),
            T("Minimum (ms)"), T("Maximum (ms)"), T("Median (ms)"),
            T("P95 (ms)"), T("Failed"),
        ])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

        self.setStyleSheet(f"""
            QWidget#performancePage {{background:{CANVAS};color:{TEXT};}}
            QWidget#performancePage QLabel {{color:{TEXT};}}
            QComboBox {{background:white;color:{TEXT};border:1px solid {BORDER};
                        padding:5px 9px;border-radius:5px;}}
            QTableWidget {{background:{SURFACE};color:{TEXT};border:1px solid {BORDER};
                           selection-background-color:#dbeafe;selection-color:{TEXT};}}
            QTableWidget::item {{padding:0 8px;border-bottom:1px solid {BORDER};}}
            QHeaderView::section {{background:{SURFACE_SOFT};color:{TEXT_MUTED};padding:8px;
                                  border:0;border-bottom:1px solid {BORDER};font-weight:600;}}
        """)
        self.period.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        data = get_performance_statistics(self.period.currentData() or 30)
        checkout = data["checkout"]
        values = (
            str(data["attempts"]), f"{data['success_rate']:.1f}%",
            f"{checkout['median']:.1f} ms", f"{checkout['p95']:.1f} ms",
        )
        for label, value in zip(self.metric_values, values):
            label.setText(value)
        self.summary.setText(TF(
            "Successful: {success} | Failed: {failed} | Cancelled: {cancelled}",
            success=data["successful"], failed=data["failed"],
            cancelled=data["cancelled"],
        ))

        rows = data["phases"]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                display_metric_key(row["operation"]),
                display_metric_key(row["phase"]),
                display_metric_key(row["metric_kind"]),
                row["count"], row["avg"], row["min"], row["max"],
                row["median"], row["p95"], row["failed"],
            )
            for column, value in enumerate(values):
                text = f"{value:.1f}" if isinstance(value, float) else str(value)
                item = QTableWidgetItem(text)
                alignment = (Qt.AlignmentFlag.AlignRight if column >= 3
                             else Qt.AlignmentFlag.AlignLeft)
                item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_index, column, item)
