from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from database.db import get_audit_log_rows
from ui_theme import (
    filter_card_style,
    header_caps_style,
    input_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    primary_text_style,
    scroll_area_style,
    secondary_text_style,
    table_container_style,
    table_row_style,
)


class AuditLogsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("auditLogsPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        title = QLabel("Audit Logs")
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("Track actions performed by admins and pharmacists")
        subtitle.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()

        main_layout.addLayout(header_row)

        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9f0f6;
                border-radius: 20px;
            }
        """)

        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(18, 18, 18, 18)
        filter_layout.setSpacing(12)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by username, role, or action...")
        self.search_input.setFixedHeight(44)
        self.search_input.textChanged.connect(self.refresh_table)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #fbfdff;
                border: 1px solid #e2eaf3;
                border-radius: 12px;
                padding: 0 16px;
                color: #0f172a;
                font-size: 14px;
            }

            QLineEdit:focus {
                background-color: white;
                border: 1px solid #93c5fd;
            }
        """)

        filter_layout.addWidget(self.search_input)
        filter_card.setLayout(filter_layout)
        main_layout.addWidget(filter_card)

        self.table_layout = QVBoxLayout()
        self.table_layout.setSpacing(0)

        wrapper = QWidget()
        wrapper.setLayout(self.table_layout)
        wrapper.setStyleSheet("background: transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(wrapper)
        scroll.setStyleSheet(scroll_area_style())

        main_layout.addWidget(scroll)

        self.setLayout(main_layout)
        self.setStyleSheet(page_root_style("auditLogsPage"))

        self.refresh_table()

    def refresh_table(self):
        while self.table_layout.count():
            item = self.table_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9f0f6;
                border-radius: 20px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.make_header_row())

        rows = get_audit_log_rows(self.search_input.text())

        if not rows:
            empty = QLabel("No audit logs found")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(180)
            empty.setStyleSheet("""
                QLabel {
                    color: #6b7280;
                    font-size: 14px;
                }
            """)
            layout.addWidget(empty)
        else:
            for row in rows:
                layout.addWidget(self.make_row(row))

        container.setLayout(layout)
        self.table_layout.addWidget(container)

    def make_header_row(self):
        row = QWidget()
        row.setFixedHeight(50)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)

        labels = ["USERNAME", "ROLE", "DESCRIPTION", "DATE"]
        stretches = [2, 2, 6, 3]

        for index, text in enumerate(labels):
            label = QLabel(text)
            label.setStyleSheet("""
                QLabel {
                    color: #7b8798;
                    font-size: 11px;
                    font-weight: 700;
                    background: transparent;
                    border: none;
                }
            """)
            layout.addWidget(label, 0, index, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def make_row(self, row_data):
        row = QFrame()
        row.setObjectName("auditLogRow")
        row.setFixedHeight(76)
        row.setStyleSheet("""
            QFrame#auditLogRow {
                border-top: 1px solid #edf2f7;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        username = QLabel(row_data["username"])
        role = QLabel(row_data["role"] or "-")
        description = QLabel(row_data["description"])
        created_at = QLabel(row_data["created_at"])

        username.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        role.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        description.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        created_at.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        widgets = [username, role, description, created_at]
        stretches = [2, 2, 6, 3]

        for index, widget in enumerate(widgets):
            layout.addWidget(widget, 0, index, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row
