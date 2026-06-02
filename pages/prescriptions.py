from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pathlib import Path

from database.db import get_prescription_rows
from ui_theme import (
    BLUE,
    filter_card_style,
    header_caps_style,
    input_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    primary_text_style,
    scroll_area_style,
    secondary_text_style,
    soft_button_style,
    table_container_style,
    table_row_style,
)


class PrescriptionsPage(QWidget):
    def __init__(self, role="admin"):
        super().__init__()

        self.role = (role or "admin").lower()

        self.setObjectName("prescriptionsPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        title = QLabel("Prescriptions")
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("Track sensitive medicine sales")
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
        self.search_input.setPlaceholderText("Search by SSN, customer, or medicine...")
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
        self.setStyleSheet(page_root_style("prescriptionsPage"))

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

        rows = get_prescription_rows(self.search_input.text())

        if not rows:
            empty = QLabel("No prescription-tracked sales found")
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
        row.setFixedHeight(34)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        labels = ["SSN", "CUSTOMER", "MEDICINE", "AMOUNT", "DATE", "REPORT"]
        stretches = [3, 3, 4, 2, 3, 2]

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
            alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(label, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def make_row(self, row_data):
        row = QFrame()
        row.setObjectName("prescriptionRow")
        row.setFixedHeight(46)
        row.setStyleSheet("""
            QFrame#prescriptionRow {
                border-top: 1px solid #edf2f7;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        ssn = QLabel(row_data["customer_ssn"])
        customer_name = QLabel(row_data["customer_name"])
        medicine = QLabel(row_data["medicine_name"])
        amount = QLabel(str(row_data["amount"]))
        created_at = QLabel(row_data["created_at"])

        ssn.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 12px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        ssn.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        customer_name.setStyleSheet("""
            QLabel {
                color: #243b5a;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        customer_name.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        medicine.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        medicine.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        amount.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        amount.setMinimumHeight(22)
        amount.setStyleSheet("""
            QLabel {
                background-color: #eef4ff;
                color: #2563eb;
                border-radius: 11px;
                padding: 2px 12px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }
        """)
        created_at.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        created_at.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0;
                background: transparent;
                border: none;
            }
        """)

        report_btn = QPushButton("Report")
        report_btn.setFixedSize(80, 28)
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.clicked.connect(lambda: self.download_report(row_data))
        report_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #dbe4ee;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                color: #0f172a;
                padding: 0 12px;
            }

            QPushButton:hover {
                background-color: #eef5ff;
            }
        """)

        amount_wrap = QWidget()
        amount_wrap.setStyleSheet("background: transparent; border: none;")
        amount_layout = QHBoxLayout()
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.addStretch()
        amount_layout.addWidget(amount, alignment=Qt.AlignmentFlag.AlignCenter)
        amount_layout.addStretch()
        amount_wrap.setLayout(amount_layout)

        report_wrap = QWidget()
        report_wrap.setStyleSheet("background: transparent; border: none;")
        report_layout = QHBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.addStretch()
        report_layout.addWidget(report_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        report_layout.addStretch()
        report_wrap.setLayout(report_layout)

        widgets = [ssn, customer_name, medicine, amount_wrap, created_at, report_wrap]
        stretches = [3, 3, 4, 2, 3, 2]

        for index, widget in enumerate(widgets):
            alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(widget, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def download_report(self, row_data):
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)

        file_name = (
            f"Prescription-{row_data['customer_name'].replace(' ', '_')}"
            f"-{row_data['medicine_name'].replace(' ', '_')}.html"
        )
        file_path = downloads_dir / file_name

        html = self.build_prescription_report_html(row_data)
        file_path.write_text(html, encoding="utf-8")

        QMessageBox.information(
            self,
            "Prescription Report Downloaded",
            f"Prescription report saved to Downloads as {file_name}"
        )

    def build_prescription_report_html(self, row_data):
        barcode_svg = self.build_ssn_barcode_svg(row_data["customer_ssn"])
        logo_path = (Path(__file__).resolve().parent.parent / "assets" / "icons" / "logo.png").as_uri()

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Prescription Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 24px;
                    color: #111827;
                    background: white;
                }}

                .report {{
                    max-width: 900px;
                    margin: 0 auto;
                    border: 1px solid #d1d5db;
                    padding: 28px 36px 36px 36px;
                    min-height: 920px;
                    box-sizing: border-box;
                    position: relative;
                }}

                .header {{
                    margin-bottom: 28px;
                }}

                .topbar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 28px;
                }}

                .brand-block {{
                    text-align: center;
                    flex: 1;
                }}

                .logo {{
                    width: 54px;
                    height: 54px;
                    object-fit: contain;
                    margin-bottom: 12px;
                }}

                .brand-name {{
                    margin: 0;
                    font-size: 34px;
                    font-weight: 800;
                    color: #111827;
                }}

                .subtitle {{
                    margin: 8px 0 0 0;
                    font-size: 16px;
                    color: #4b5563;
                }}

                .details {{
                    margin-top: 28px;
                    line-height: 1.9;
                    font-size: 16px;
                }}

                .details strong {{
                    color: #111827;
                }}

                .summary-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 28px;
                }}

                .summary-table th,
                .summary-table td {{
                    border: 1px solid #d1d5db;
                    padding: 12px 14px;
                    text-align: left;
                    font-size: 14px;
                }}

                .summary-table th {{
                    background-color: #f3f4f6;
                    font-weight: 700;
                }}

                .barcode-block {{
                    position: absolute;
                    right: 36px;
                    bottom: 36px;
                    text-align: center;
                }}

                .barcode-label {{
                    margin-top: 10px;
                    font-size: 13px;
                    color: #374151;
                    letter-spacing: 1px;
                }}
            </style>
        </head>
        <body>
            <div class="report">
                <div class="header">
                    <div class="topbar">
                        <div style="width: 120px;"></div>
                        <div class="brand-block">
                            <img src="{logo_path}" alt="Pharmacy Logo" class="logo">
                            <h1 class="brand-name">Khalis Dawa</h1>
                            <p class="subtitle">Prescription Report</p>
                        </div>
                        <div style="width: 120px;"></div>
                    </div>
                </div>

                <div class="details">
                    <div><strong>Customer Name:</strong> {row_data['customer_name']}</div>
                    <div><strong>Date of Purchase:</strong> {row_data['created_at']}</div>
                </div>

                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Medicine</th>
                            <th>Quantity</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{row_data['medicine_name']}</td>
                            <td>{row_data['amount']}</td>
                        </tr>
                    </tbody>
                </table>

                <div class="barcode-block">
                    {barcode_svg}
                    <div class="barcode-label">{row_data['customer_ssn']}</div>
                </div>
            </div>
        </body>
        </html>
        """

    def build_ssn_barcode_svg(self, ssn):
        code39_patterns = {
            "0": "nnnwwnwnn",
            "1": "wnnwnnnnw",
            "2": "nnwwnnnnw",
            "3": "wnwwnnnnn",
            "4": "nnnwwnnnw",
            "5": "wnnwwnnnn",
            "6": "nnwwwnnnn",
            "7": "nnnwnnwnw",
            "8": "wnnwnnwnn",
            "9": "nnwwnnwnn",
            "*": "nwnnwnwnn",
        }

        encoded = f"*{ssn}*"
        narrow = 2
        wide = 5
        gap = 2
        height = 80

        x = 0
        rects = []

        for char in encoded:
            pattern = code39_patterns[char]
            for index, width_code in enumerate(pattern):
                width = wide if width_code == "w" else narrow
                if index % 2 == 0:
                    rects.append(
                        f'<rect x="{x}" y="0" width="{width}" height="{height}" fill="#111827" />'
                    )
                x += width
            x += gap

        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{x}" height="{height}" viewBox="0 0 {x} {height}">{"".join(rects)}</svg>'
