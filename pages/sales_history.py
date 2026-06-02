from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pathlib import Path
from database.db import (
    delete_sale_record,
    get_sale_receipt_data,
    get_sale_return_candidates,
    get_sales_history,
    process_sale_return,
)
from ui_theme import (
    BLUE,
    PRIMARY,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    filter_card_style,
    input_style,
    scroll_area_style,
    table_container_style,
    table_row_style,
    header_caps_style,
    primary_text_style,
    secondary_text_style,
    metric_text_style,
    soft_button_style,
    action_button_style,
    danger_button_style,
    primary_button_style,
)
class ReturnItemsDialog(QDialog):
    def __init__(self, sale_context, parent=None):
        super().__init__(parent)

        self.sale_context = sale_context
        self.quantity_inputs = {}

        self.setWindowTitle("Return Items")
        self.setModal(True)
        self.setMinimumWidth(620)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(f"Return items from {sale_context['receipt_number']}")
        title.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 18px;
                font-weight: 800;
            }
        """)

        subtitle = QLabel(
            f"Sold on {sale_context['sale_datetime']}. Returns are allowed until "
            f"{sale_context['return_deadline']}."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        for item in sale_context["items"]:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #f8fafc;
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                }
            """)

            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(8)

            name = QLabel(item["product_name"])
            name.setStyleSheet("""
                QLabel {
                    color: #111827;
                    font-size: 15px;
                    font-weight: 700;
                }
            """)

            meta = QLabel(
                f"Sold: {item['sold_quantity']} | Already returned: {item['returned_quantity']} | "
                f"Available now: {item['returnable_quantity']} | Unit price: {item['unit_price']:g} Ft"
            )
            meta.setStyleSheet("""
                QLabel {
                    color: #374151;
                    font-size: 13px;
                }
            """)

            card_layout.addWidget(name)
            card_layout.addWidget(meta)

            if item["expired_blocked_quantity"] > 0:
                expired_note = QLabel(
                    f"{item['expired_blocked_quantity']} unit(s) can no longer be returned because they are expired."
                )
                expired_note.setWordWrap(True)
                expired_note.setStyleSheet("""
                    QLabel {
                        color: #b45309;
                        font-size: 12px;
                        font-weight: 600;
                    }
                """)
                card_layout.addWidget(expired_note)

            controls = QHBoxLayout()
            controls.addStretch()

            quantity_label = QLabel("Return quantity")
            quantity_label.setStyleSheet("color: #111827; font-size: 13px; font-weight: 600;")

            quantity_input = QSpinBox()
            quantity_input.setRange(0, item["returnable_quantity"])
            quantity_input.setValue(0)
            quantity_input.setFixedHeight(34)
            quantity_input.setFixedWidth(90)
            quantity_input.setEnabled(item["returnable_quantity"] > 0)
            quantity_input.setStyleSheet("""
                QSpinBox {
                    background-color: white;
                    border: 1px solid #dbe4ee;
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 13px;
                    color: #111827;
                }

                QSpinBox:disabled {
                    background-color: #f3f4f6;
                    color: #9ca3af;
                }
            """)

            self.quantity_inputs[item["sale_item_id"]] = quantity_input

            controls.addWidget(quantity_label)
            controls.addWidget(quantity_input)

            card_layout.addLayout(controls)
            card.setLayout(card_layout)
            layout.addWidget(card)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Process Return")

        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)

        cancel_btn.setFixedHeight(38)
        confirm_btn.setFixedHeight(38)

        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        button_row.addWidget(cancel_btn)
        button_row.addWidget(confirm_btn)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def get_selected_items(self):
        selected_items = []

        for sale_item_id, quantity_input in self.quantity_inputs.items():
            quantity = int(quantity_input.value())
            if quantity > 0:
                selected_items.append({
                    "sale_item_id": sale_item_id,
                    "quantity": quantity,
                })

        return selected_items


class SalesHistoryPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.is_admin = self.current_user.get("role") == "admin"
        self.setObjectName("salesHistoryPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("Sales History")
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("View all completed sales")
        subtitle.setStyleSheet("""
            QLabel {
                color: #64748b;
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
                border-radius: 20px;
            }
        """)

        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(18, 18, 18, 18)
        filter_layout.setSpacing(12)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by receipt ID...")
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

        self.setStyleSheet(page_root_style("salesHistoryPage"))

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

        rows = get_sales_history(self.search_input.text())

        if not rows:
            empty = QLabel("No sales found")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(180)
            empty.setStyleSheet("""
                QLabel {
                    color: #64748b;
                    font-size: 14px;
                }
            """)
            layout.addWidget(empty)
        else:
            for row in rows:
                layout.addWidget(self.make_sales_row(row))

        container.setLayout(layout)
        self.table_layout.addWidget(container)

    def make_header_row(self):
        row = QWidget()
        row.setFixedHeight(50)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)

        labels = ["RECEIPT ID", "ITEMS", "DATE", "TOTAL", "PAYMENT", "ACTIONS"]
        stretches = [2, 1, 3, 2, 2, 4]



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
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if text in {"ITEMS", "TOTAL", "ACTIONS"}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(label, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def make_sales_row(self, row_data):
        row = QFrame()
        row.setObjectName("salesHistoryRow")
        row.setFixedHeight(76)
        row.setStyleSheet("""
            QFrame#salesHistoryRow {
                border-top: 1px solid #edf2f7;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        stretches = [2, 1, 3, 2, 2, 4]



        receipt_id = QLabel(row_data["receipt_number"])
        receipt_id.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        items = QLabel(str(row_data["items"]))
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

        date = QLabel(row_data["date"])
        date.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        total = QLabel(f"{row_data['total']:g} Ft")
        total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total.setStyleSheet("""
            QLabel {
                color: #16a34a;
                font-size: 14px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        payment = QLabel(row_data["payment_method"])
        payment.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)
        download_btn = QPushButton("Download")
        download_btn.setFixedSize(92, 32)
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.setStyleSheet("""
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

        download_btn.clicked.connect(lambda: self.download_receipt(row_data["id"]))

        actions_widget = QWidget()
        actions_widget.setStyleSheet("background: transparent; border: none;")
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        return_btn = QPushButton("Return")
        return_btn.setFixedSize(78, 32)
        return_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return_btn.clicked.connect(lambda: self.return_sale(row_data["id"]))
        return_btn.setStyleSheet("""
            QPushButton {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                color: #2563eb;
                padding: 0 12px;
            }

            QPushButton:hover {
                background-color: #dbeafe;
            }
        """)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(78, 32)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_sale(row_data["id"], row_data["receipt_number"]))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff7f7;
                border: 1px solid #f3caca;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                color: #dc2626;
                padding: 0 12px;
            }

            QPushButton:hover {
                background-color: #feecec;
            }
        """)

        actions_layout.addStretch()
        actions_layout.addWidget(download_btn)
        actions_layout.addWidget(return_btn)
        if self.is_admin:
            actions_layout.addWidget(delete_btn)
        actions_widget.setLayout(actions_layout)

        widgets = [receipt_id, items, date, total, payment, actions_widget]



        for index, widget in enumerate(widgets):
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if index in {1, 3, 5}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(widget, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row
 

    def delete_sale(self, sale_id, receipt_number=None):
        if not self.is_admin:
            QMessageBox.warning(self, "Access Denied", "Only administrators can delete sales history.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Sale",
            f"Are you sure you want to delete sale {receipt_number or sale_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_sale_record(
            sale_id,
            acting_username=self.current_user.get("username"),
            acting_role=self.current_user.get("role")
        )

        if not success:
            QMessageBox.warning(self, "Delete Failed", message)
            return

        QMessageBox.information(self, "Sale Deleted", message)
        self.refresh_table()

    def return_sale(self, sale_id):
        try:
            sale_context = get_sale_return_candidates(sale_id)
        except ValueError as error:
            QMessageBox.warning(self, "Return Failed", str(error))
            return

        if not sale_context["return_window_open"]:
            QMessageBox.warning(
                self,
                "Return Window Closed",
                f"{sale_context['receipt_number']} can only be returned until {sale_context['return_deadline']}."
            )
            return

        if not any(item["returnable_quantity"] > 0 for item in sale_context["items"]):
            QMessageBox.warning(
                self,
                "Nothing Returnable",
                "All remaining sold units are already returned or expired."
            )
            return

        dialog = ReturnItemsDialog(sale_context, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_items = dialog.get_selected_items()
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Items Selected",
                "Select at least one item quantity to return."
            )
            return

        items_by_id = {
            item["sale_item_id"]: item
            for item in sale_context["items"]
        }
        refund_total = sum(
            items_by_id[item["sale_item_id"]]["unit_price"] * item["quantity"]
            for item in selected_items
        )

        confirm = QMessageBox.question(
            self,
            "Confirm Return",
            f"Process return for {sale_context['receipt_number']}?\nRefund amount: {refund_total:g} Ft",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = process_sale_return(
            sale_id,
            selected_items,
            acting_username=self.current_user.get("username"),
            acting_role=self.current_user.get("role")
        )

        if not success:
            QMessageBox.warning(self, "Return Failed", message)
            return

        QMessageBox.information(self, "Return Complete", message)
        self.refresh_table()


    def download_receipt(self, sale_id):
        receipt_data = get_sale_receipt_data(sale_id)

        if not receipt_data:
            QMessageBox.warning(self, "Receipt Error", "Sale receipt data could not be found.")
            return

        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)

        file_path = downloads_dir / f"Receipt-{receipt_data['receipt_number'].replace('#', '')}.html"

        html = self.build_receipt_html(receipt_data)
        file_path.write_text(html, encoding="utf-8")

        QMessageBox.information(
            self,
            "Receipt Downloaded",
            f"Receipt saved to Downloads as Receipt-{receipt_data['receipt_number'].replace('#', '')}.html"
        )

    def build_receipt_html(self, receipt_data):
        item_rows = ""
        for index, item in enumerate(receipt_data["items"], start=1):
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
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{receipt_data['receipt_number']}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 24px;
                    color: #111827;
                    background: white;
                }}

                .receipt {{
                    max-width: 900px;
                    margin: 0 auto;
                    border: 1px solid #d1d5db;
                    padding: 28px 36px 36px 36px;
                    min-height: 1100px;
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
                    color: #111827;
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
                    color: #111827;
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
                    border: 1px solid #111827;
                }}

                .total-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 12px 16px;
                    font-size: 15px;
                    font-weight: 700;
                    background: #111827;
                    color: white;
                }}

                .thank-you {{
                    margin-top: 70px;
                    text-align: center;
                    color: #6b7280;
                    font-size: 18px;
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
                    <div class="invoice-label">Invoice</div>
                    <div class="brand-block">
                        <img src="{logo_path}" alt="Pharmacy Logo" class="logo">
                        <h1 class="brand-name">Khalis Dawa</h1>
                        <p class="brand-subtitle">Pharmacy Receipt</p>
                        <div class="receipt-no">{receipt_data['receipt_number']}</div>
                    </div>
                    <div style="width: 120px;"></div>
                </div>

                <div class="meta">
                    <div><strong>Date:</strong> {receipt_data['date']}</div>
                    <div><strong>Payment Method:</strong> {receipt_data['payment_method']}</div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>No.</th>
                            <th>Item</th>
                            <th>Quantity</th>
                            <th>Unit Price</th>
                            <th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {item_rows}
                    </tbody>
                </table>

                <div class="total-box">
                    <div class="total-row">
                        <span>TOTAL</span>
                        <span>{receipt_data['total']:g} Ft</span>
                    </div>
                </div>

                <div class="thank-you">
                    Thank you for shopping with Khalis Dawa.
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



    
