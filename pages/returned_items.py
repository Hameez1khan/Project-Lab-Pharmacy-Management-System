from pathlib import Path

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
    QVBoxLayout,
    QWidget,
)

from database.db import (
    delete_return_record,
    get_return_report_data,
    get_returns_history,
    get_returns_history_count,
)
from i18n import T, TF, force_ltr, format_date, format_money, is_rtl, language
from ui_components import PaginationBar
from ui_theme import (
    PRIMARY,
    filter_card_style,
    header_caps_style,
    input_style,
    metric_text_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    primary_text_style,
    scroll_area_style,
    secondary_text_style,
    soft_button_style,
    table_container_style,
    table_row_style,
    danger_button_style,
)


class ReturnedItemsPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.is_admin = self.current_user.get("role") == "admin"
        self.setObjectName("returnedItemsPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel(T("Returned Items"))
        title.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel(T("Track completed returns and refund documents"))
        subtitle.setStyleSheet("""
            QLabel {
                color: #68776f;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9f0f6;
                border-radius: 8px;
            }
        """)

        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(18, 18, 18, 18)
        filter_layout.setSpacing(12)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("Search by return ID or sale receipt..."))
        self.search_input.setFixedHeight(44)
        self.search_input.textChanged.connect(lambda: self.refresh_table(reset=True))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #fbfdff;
                border: 1px solid #e2eaf3;
                border-radius: 12px;
                padding: 0 16px;
                color: #18251f;
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
        self.pagination = PaginationBar(self.refresh_table, page_size=25)
        main_layout.addWidget(self.pagination)
        self.setLayout(main_layout)

        self.setStyleSheet(page_root_style("returnedItemsPage"))

        self.refresh_table()

    def refresh_table(self, *_args, reset=False):
        if reset and hasattr(self, "pagination"):
            self.pagination.reset()
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
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.make_header_row())

        search = self.search_input.text()
        self.pagination.set_total(get_returns_history_count(search))
        rows = get_returns_history(search, self.pagination.page_size, self.pagination.offset)

        if not rows:
            empty = QLabel(T("No returned items found"))
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
                layout.addWidget(self.make_return_row(row))

        container.setLayout(layout)
        self.table_layout.addWidget(container)

    def make_header_row(self):
        row = QWidget()
        row.setFixedHeight(50)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)

        labels = [
            "RECEIPT ID",
            "ITEMS",
            "DATE RETURNED",
            "REFUND",
            "SOURCE SALE",
            "REPORT",
        ]
        stretches = [2, 1, 3, 2, 2, 2]

        if self.is_admin:
            labels.append("ACTIONS")
            stretches.append(2)

        for index, text in enumerate(labels):
            label = QLabel(T(text))
            label.setStyleSheet("""
                QLabel {
                    color: #7b8798;
                    font-size: 11px;
                    font-weight: 700;
                    background: transparent;
                    border: none;
                }
            """)
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if text in {"ITEMS", "REFUND", "REPORT", "ACTIONS"}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(label, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def make_return_row(self, row_data):
        row = QFrame()
        row.setObjectName("returnedItemRow")
        row.setFixedHeight(76)
        row.setStyleSheet("""
            QFrame#returnedItemRow {
                border-top: 1px solid #edf2ef;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        stretches = [2, 1, 3, 2, 2, 2]
        if self.is_admin:
            stretches.append(2)

        receipt_id = force_ltr(QLabel(row_data["return_receipt_number"]))
        items = QLabel(str(row_data["total_items"]))
        date = force_ltr(QLabel(format_date(row_data["date"], include_time=True)))
        refund_amount = force_ltr(QLabel(format_money(row_data["refund_amount"], 0)), right=True)
        source_sale = force_ltr(QLabel(row_data["source_receipt_number"]))

        receipt_id.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        items.setAlignment(Qt.AlignmentFlag.AlignCenter)
        items.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        date.setStyleSheet("""
            QLabel {
                color: #43534b;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)
        refund_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        refund_amount.setStyleSheet("""
            QLabel {
                color: #16a34a;
                font-size: 14px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)
        source_sale.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        report_btn = QPushButton(T("Download"))
        report_btn.setFixedSize(92, 32)
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.clicked.connect(lambda: self.download_return_report(row_data["id"]))
        report_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #dbe4ee;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                color: #18251f;
                padding: 0 12px;
            }

            QPushButton:hover {
                background-color: #eef5ff;
            }
        """)

        action_btn = QPushButton(T("Delete"))
        action_btn.setFixedSize(84, 32)
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        action_btn.clicked.connect(
            lambda: self.delete_return(row_data["id"], row_data["return_receipt_number"])
        )
        action_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff7f7;
                border: 1px solid #f3caca;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                color: #c84b4b;
                padding: 0 12px;
            }

            QPushButton:hover {
                background-color: #feecec;
            }
        """)

        report_widget = QWidget()
        report_widget.setStyleSheet("background: transparent; border: none;")
        report_layout = QHBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.setSpacing(0)
        report_layout.addStretch()
        report_layout.addWidget(report_btn)
        report_layout.addStretch()
        report_widget.setLayout(report_layout)

        actions_widget = QWidget()
        actions_widget.setStyleSheet("background: transparent; border: none;")
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(0)
        actions_layout.addStretch()
        actions_layout.addWidget(action_btn)
        actions_layout.addStretch()
        actions_widget.setLayout(actions_layout)

        widgets = [
            receipt_id,
            items,
            date,
            refund_amount,
            source_sale,
            report_widget,
        ]

        if self.is_admin:
            widgets.append(actions_widget)

        for index, widget in enumerate(widgets):
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if index in {1, 3, 5, 6}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(widget, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def delete_return(self, return_id, return_receipt_number):
        if not self.is_admin:
            QMessageBox.warning(self, T("Access Denied"), T("Only administrators can delete returned items."))
            return

        confirm = QMessageBox.question(
            self,
            T("Delete Return"),
            TF("Are you sure you want to delete return {receipt}?", receipt=return_receipt_number),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_return_record(
            return_id,
            acting_username=self.current_user.get("username") or "admin",
            acting_role=self.current_user.get("role"),
        )

        if not success:
            QMessageBox.warning(self, T("Delete Failed"), T(message))
            return

        QMessageBox.information(self, T("Return Deleted"), T(message))
        self.refresh_table()

    def download_return_report(self, return_id):
        report_data = get_return_report_data(return_id)

        if not report_data:
            QMessageBox.warning(self, T("Return Report Error"), T("Return report data could not be found."))
            return

        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)

        file_path = downloads_dir / f"Return-{report_data['return_receipt_number'].replace('#', '')}.html"
        html = self.build_return_report_html(report_data)
        file_path.write_text(html, encoding="utf-8")

        QMessageBox.information(
            self,
            T("Return Report Downloaded"),
            TF("Return report saved to Downloads as {filename}",
               filename=f"Return-{report_data['return_receipt_number'].replace('#', '')}.html")
        )

    def build_return_report_html(self, report_data):
        item_rows = ""
        for index, item in enumerate(report_data["items"], start=1):
            item_rows += f"""
                <tr>
                    <td>{index}</td>
                    <td>{item['name']}</td>
                    <td>{item['quantity']}</td>
                    <td>{item['unit_price']:g} Ft</td>
                    <td>{item['subtotal']:g} Ft</td>
                </tr>
            """

        logo_path = (Path(__file__).resolve().parent.parent / "assets" / "icons" / "logo.png").as_uri()

        return f"""
        <!DOCTYPE html>
        <html lang="{language()}" dir="{'rtl' if is_rtl() else 'ltr'}">
        <head>
            <meta charset="UTF-8">
            <title>{report_data['return_receipt_number']}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 24px;
                    color: #18251f;
                    background: white;
                }}

                .receipt {{
                    max-width: 900px;
                    margin: 0 auto;
                    border: 1px solid #d1d5db;
                    padding: 28px 36px 36px 36px;
                    min-height: 1040px;
                    box-sizing: border-box;
                    position: relative;
                }}

                .topbar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 28px;
                }}

                .invoice-label {{
                    font-size: 28px;
                    font-weight: 800;
                    color: #18251f;
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
                    color: #18251f;
                }}

                .brand-subtitle {{
                    margin: 8px 0 0 0;
                    font-size: 16px;
                    color: #4b5563;
                }}

                .receipt-no {{
                    margin-top: 10px;
                    font-size: 15px;
                    font-weight: 700;
                    color: #444444;
                }}

                .meta {{
                    margin-top: 26px;
                    margin-bottom: 26px;
                    line-height: 1.9;
                    font-size: 16px;
                }}

                .meta strong {{
                    color: #18251f;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 18px;
                    margin-bottom: 28px;
                }}

                th, td {{
                    border: 1px solid #d1d5db;
                    padding: 12px 14px;
                    text-align: left;
                    font-size: 14px;
                }}

                th {{
                    background-color: #f3f4f6;
                    font-weight: 700;
                }}

                .total-box {{
                    width: 320px;
                    margin-left: auto;
                    margin-top: 18px;
                    border: 1px solid #18251f;
                }}

                .total-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 12px 16px;
                    font-size: 15px;
                    font-weight: 700;
                    background: #18251f;
                    color: white;
                }}

                .summary-card {{
                    margin-top: 24px;
                    background-color: #f8fafc;
                    border: 1px solid #dbe4ee;
                    border-radius: 12px;
                    padding: 16px 18px;
                }}

                .summary-card div {{
                    font-size: 14px;
                    color: #374151;
                    margin-bottom: 8px;
                }}

                .summary-card div:last-child {{
                    margin-bottom: 0;
                }}

                .footer {{
                    position: absolute;
                    left: 36px;
                    right: 36px;
                    bottom: 28px;
                    text-align: center;
                    color: #374151;
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <div class="topbar">
                    <div class="invoice-label">{T("Return")}</div>
                    <div class="brand-block">
                        <img src="{logo_path}" alt="Pharmacy Logo" class="logo">
                        <h1 class="brand-name">Khalis Dawa</h1>
                        <p class="brand-subtitle">{T("Returned Items Report")}</p>
                        <div class="receipt-no">{report_data['return_receipt_number']}</div>
                    </div>
                    <div style="width: 120px;"></div>
                </div>

                <div class="meta">
                    <div><strong>{T("Date returned")}:</strong> {format_date(report_data['return_date'], include_time=True)}</div>
                    <div><strong>{T("Source sale")}:</strong> {report_data['source_receipt_number']}</div>
                    <div><strong>{T("Original Sale Date")}:</strong> {format_date(report_data['source_sale_date'], include_time=True)}</div>
                    <div><strong>{T("Processed By")}:</strong> {report_data['processed_by']}</div>
                    <div><strong>{T("Payment Method")}:</strong> {T(report_data['payment_method'])}</div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>{T("No.")}</th>
                            <th>{T("Item")}</th>
                            <th>{T("Quantity")}</th>
                            <th>{T("Unit Price")}</th>
                            <th>{T("Subtotal")}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {item_rows}
                    </tbody>
                </table>

                <div class="summary-card">
                    <div><strong>{T("Total Items Returned")}:</strong> {report_data['total_items']}</div>
                    <div><strong>{T("Original Sale Receipt")}:</strong> {report_data['source_receipt_number']}</div>
                </div>

                <div class="total-box">
                    <div class="total-row">
                        <span>{T("Refund total").upper()}</span>
                        <span>{report_data['refund_total']:g} Ft</span>
                    </div>
                </div>

                <div class="footer">
                    Khalis Dawa&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                    kunigunda utja 25, 1037. BUDAPEST&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                    dummymail@khalisdawa.com
                </div>
            </div>
        </body>
        </html>
        """
