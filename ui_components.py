"""Small reusable interface components shared by data-heavy pages."""

import math

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from i18n import T, TF
from ui_theme import BORDER, PRIMARY, PRIMARY_SOFT, SURFACE, TEXT, TEXT_MUTED, soft_button_style


class PaginationBar(QFrame):
    """Compact previous/next pagination with a stable page size."""

    def __init__(self, on_change, page_size=50, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.page_size = int(page_size)
        self.current_page = 1
        self.total_records = 0
        self.setObjectName("paginationBar")
        self.setStyleSheet(
            f"QFrame#paginationBar {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:8px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)
        self.summary = QLabel()
        self.summary.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; border:none;")
        self.previous = QPushButton(T("Previous"))
        self.next = QPushButton(T("Next"))
        for button in (self.previous, self.next):
            button.setFixedSize(84, 32)
            button.setStyleSheet(soft_button_style())
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(92)
        self.page_label.setStyleSheet(
            f"color:{PRIMARY}; background:{PRIMARY_SOFT}; border:none; border-radius:6px; padding:7px 10px; font-size:11px; font-weight:700;"
        )
        self.previous.clicked.connect(self.go_previous)
        self.next.clicked.connect(self.go_next)
        layout.addWidget(self.summary)
        layout.addStretch()
        layout.addWidget(self.previous)
        layout.addWidget(self.page_label)
        layout.addWidget(self.next)
        self.set_total(0)

    @property
    def page_count(self):
        return max(1, math.ceil(self.total_records / self.page_size))

    @property
    def offset(self):
        return (self.current_page - 1) * self.page_size

    def reset(self):
        self.current_page = 1

    def set_total(self, total):
        self.total_records = max(0, int(total or 0))
        self.current_page = min(max(1, self.current_page), self.page_count)
        first = 0 if not self.total_records else self.offset + 1
        last = min(self.total_records, self.offset + self.page_size)
        self.summary.setText(TF("Showing {first}-{last} of {total}", first=first, last=last, total=self.total_records))
        self.page_label.setText(TF("Page {page} of {pages}", page=self.current_page, pages=self.page_count))
        self.previous.setEnabled(self.current_page > 1)
        self.next.setEnabled(self.current_page < self.page_count)

    def go_previous(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self.on_change()

    def go_next(self):
        if self.current_page >= self.page_count:
            return
        self.current_page += 1
        self.on_change()
