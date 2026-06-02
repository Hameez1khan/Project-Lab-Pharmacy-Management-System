from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("reportsPage")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 24, 24, 22)

        message = QLabel("This page is currently under progress, reserved for thesis.")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 18px;
                font-weight: 600;
                background: transparent;
            }
        """)

        layout.addStretch()
        layout.addWidget(message)
        layout.addStretch()

        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget#reportsPage {
                background-color: #f8faf9;
            }
        """)
