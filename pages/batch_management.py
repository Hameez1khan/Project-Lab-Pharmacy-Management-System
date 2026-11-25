from datetime import datetime

from PyQt6.QtCore import Qt
from i18n import T, TF, force_ltr, format_date, format_money
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
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


from database.db import (
    add_audit_log,
    add_batch_record,
    delete_batch_record,
    get_batch_rows,
    get_categories,
    get_product_by_name,
    update_batch_record,
)
from ui_theme import (
    PRIMARY,
    BLUE,
    badge_style,
    checkbox_style,
    filter_card_style,
    header_caps_style,
    input_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    primary_button_style,
    primary_text_style,
    scroll_area_style,
    soft_button_style,
    table_container_style,
    table_row_style,
)




class BatchFormDialog(QDialog):
    def __init__(self, parent=None, batch_row=None):
        super().__init__(parent)
        self.batch_row = batch_row

        self.setWindowTitle(T("Add Batch" if batch_row is None else "Edit Batch"))
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout()
        form = QFormLayout()
        form.setSpacing(14)

        self.name_input = QLineEdit()
        self.category_input = QLineEdit()
        self.batch_input = QLineEdit()
        self.quantity_input = QLineEdit()
        self.expiry_input = QLineEdit()
        self.price_input = QLineEdit()
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText("0.00")
        self.min_stock_input = QLineEdit()

        self.expiry_input.setPlaceholderText("YYYY-MM-DD")

        fields = [
            ("Medicine", self.name_input),
            ("Batch", self.batch_input),
            ("Quantity", self.quantity_input),
            ("Expiry", self.expiry_input),
            ("Purchase cost per unit (Ft)", self.cost_input),
        ]

        if batch_row is not None:
            fields.extend([
                ("Product selling price (Ft)", self.price_input),
                ("Min Stock", self.min_stock_input),
            ])



        for label, widget in fields:
            widget.setFixedHeight(42)
            widget.setStyleSheet(input_style())
            form.addRow(T(label), widget)

        


        if batch_row:
            self.name_input.setText(batch_row["name"])
            self.batch_input.setText(batch_row["batch_number"])
            self.quantity_input.setText(str(batch_row["stock"]))
            self.expiry_input.setText(batch_row["expiry_date"])
            self.price_input.setText(str(batch_row["price"]))
            self.cost_input.setText(f"{batch_row['purchase_unit_cost']:.2f}")
            self.cost_input.setReadOnly(True)
            self.min_stock_input.setText(str(batch_row["min_stock_level"]))


            self.name_input.setEnabled(False)
            self.batch_input.setEnabled(False)



        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton(T("Cancel"))
        save_btn = QPushButton(T("Save"))

        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)

        for button in (cancel_btn, save_btn):
            button.setFixedHeight(36)

        save_btn.setStyleSheet(primary_button_style(color=BLUE, hover="#1e40af"))
        cancel_btn.setStyleSheet(soft_button_style())

        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)

        layout.addLayout(form)
        layout.addLayout(button_row)
        self.setLayout(layout)

    def get_payload(self):
        return {
            "name": self.name_input.text().strip(),
            "batch_number": self.batch_input.text().strip(),
            "quantity": self.quantity_input.text().strip(),
            "expiry_date": self.expiry_input.text().strip(),
            "category": self.category_input.text().strip(),
            "price": self.price_input.text().strip(),
            "purchase_unit_cost": self.cost_input.text().strip().replace(",", "."),
            "min_stock_level": self.min_stock_input.text().strip(),
        }



class BatchManagementPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.setObjectName("batchManagementPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        # ================= HEADER =================
        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        title = QLabel(T("Batch-based Inventory Management"))
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel(T("Product Batch Manager"))
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

        add_btn = QPushButton(T("+ Add Batch"))
        add_btn.setFixedSize(164, 42)
        add_btn.clicked.connect(self.open_add_dialog)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
                padding: 0 16px;
            }

            QPushButton:hover {
                background-color: #16a34a;
            }
        """)

        header_row.addLayout(header_text)
        header_row.addStretch()
        header_row.addWidget(add_btn)

        main_layout.addLayout(header_row)

        # ================= FILTER CARD =================
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
        self.search_input.setPlaceholderText(T("Search medicines..."))
        self.search_input.setFixedHeight(44)
        self.search_input.textChanged.connect(self.refresh_table)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(44)
        self.category_filter.setFixedWidth(220)
        self.category_filter.currentTextChanged.connect(self.refresh_table)


        self.expired_only_checkbox = QCheckBox(T("Expired Batches"))
        self.expired_only_checkbox.stateChanged.connect(self.refresh_table)
        self.expired_only_checkbox.setStyleSheet(checkbox_style(accent="#f59e0b"))
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
        self.category_filter.setStyleSheet("""
            QComboBox {
                background-color: #fbfdff;
                border: 1px solid #e2eaf3;
                border-radius: 12px;
                padding: 0 14px;
                color: #0f172a;
                font-size: 14px;
            }

            QComboBox:focus {
                background-color: white;
                border: 1px solid #93c5fd;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
                background: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #dbe5f2;
                selection-background-color: #eef5ff;
                selection-color: #0f172a;
                outline: none;
                padding: 4px;
            }

            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 4px 10px;
                border-radius: 6px;
            }
        """)

        checkbox_wrap = QWidget()
        checkbox_wrap.setStyleSheet("background: transparent; border: none;")
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(4, 0, 0, 0)
        checkbox_layout.setSpacing(8)
        checkbox_layout.addWidget(self.expired_only_checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        checkbox_layout.addStretch()
        checkbox_wrap.setLayout(checkbox_layout)

        filter_layout.addWidget(self.search_input, stretch=1)
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(checkbox_wrap, stretch=0)
        filter_card.setLayout(filter_layout)

        main_layout.addWidget(filter_card)

        # ================= TABLE AREA =================
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
        self.setStyleSheet(page_root_style("batchManagementPage"))

        self.reload_filters()
        self.refresh_table()

    def reload_filters(self):
        current = self.category_filter.currentData()

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem(T("All Categories"), "")
        for category in get_categories():
            self.category_filter.addItem(category, category)

        index = self.category_filter.findData(current)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

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

        header = self.make_header_row()
        layout.addWidget(header)

        rows = get_batch_rows(
            search_text=self.search_input.text(),
            category=self.category_filter.currentData() or "",
        )

        if self.expired_only_checkbox.isChecked():
            rows = [row for row in rows if row["expired"]]


        if not rows:
            empty = QLabel(T("No batches found"))
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
                layout.addWidget(self.make_batch_row(row))

        container.setLayout(layout)
        self.table_layout.addWidget(container)

    def make_header_row(self):
        row = QWidget()
        row.setFixedHeight(52)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        widgets = []

        labels = [
            "MEDICINE", "CATEGORY", "BATCH", "STOCK",
            "BUY / UNIT", "SELL / UNIT", "MARGIN", "EXPIRY", "ACTIONS",
        ]

        for index, text in enumerate(labels):
            label = QLabel(T(text))
            label.setAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | (
                    Qt.AlignmentFlag.AlignLeft
                    if index == 0
                    else Qt.AlignmentFlag.AlignHCenter
                )
            )
            label.setStyleSheet("""
                QLabel {
                    color: #7b8798;
                    font-size: 11px;
                    font-weight: 700;
                    background: transparent;
                    border: none;
                }
            """)
            widgets.append(label)

        self.configure_table_columns(layout, widgets)
        row.setLayout(layout)
        return row
        
    def configure_table_columns(self, layout, widgets):
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        stretches = [3, 2, 2, 2, 2, 2, 2, 2, 0]
        actions_width = 138  # Edit + spacing + Delete

        for index, widget in enumerate(widgets):
            if index == len(widgets) - 1:
                widget.setFixedWidth(actions_width)
                layout.setColumnMinimumWidth(index, actions_width)
            else:
                widget.setMinimumWidth(0)
                widget.setSizePolicy(
                    QSizePolicy.Policy.Ignored,
                    QSizePolicy.Policy.Preferred,
                )
                layout.setColumnMinimumWidth(index, 0)

            layout.setColumnStretch(index, stretches[index])
            layout.addWidget(widget, 0, index)

    def make_batch_row(self, row_data):
        today = datetime.today().date()

        try:
            expiry_date_obj = datetime.strptime(row_data["expiry_date"], "%Y-%m-%d").date()
            days_left = (expiry_date_obj - today).days

            if row_data["expired"]:
                expiry_status = "Expired"
                expiry_color = "#ef4444"
            elif days_left <= 30:
                expiry_status = "Expiring soon"
                expiry_color = "#f59e0b"
            else:
                expiry_status = "Good"
                expiry_color = "#22c55e"
        except ValueError:
            expiry_status = "Invalid date"
            expiry_color = "#ef4444"

        row = QFrame()
        row.setObjectName("batchRow")
        row.setFixedHeight(78)
        row.setStyleSheet("""
            QFrame#batchRow {
                border-top: 1px solid #edf2f7;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)


        medicine = QLabel(row_data["name"])
        medicine.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        category = QLabel(row_data["category"])
        category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        category.setFixedHeight(28)
        category.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        category.setStyleSheet("""
            QLabel {
                background-color: #eef4ff;
                color: #2563eb;
                border: none;
                border-radius: 8px;
                padding: 0px 12px;
                font-size: 11px;
                font-weight: 700;
            }
        """)

        batch = force_ltr(QLabel(row_data["batch_number"]))
        batch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        batch.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        stock_color = "#fef2f2" if row_data["expired"] or row_data["stock"] <= 0 else "#ecfdf5"
        stock_text_color = "#dc2626" if row_data["expired"] or row_data["stock"] <= 0 else "#16a34a"

        stock = QLabel(TF("{count} units", count=row_data["stock"]))
        stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stock.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        stock.setStyleSheet(f"""
            QLabel {{
                background-color: {stock_color};
                color: {stock_text_color};
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                border: none;
            }}
        """)
        stock.setMinimumHeight(26)

        sell = float(row_data["price"])
        buy = float(row_data["purchase_unit_cost"])
        cost_label = force_ltr(QLabel(format_money(buy)), right=True)
        price = force_ltr(QLabel(format_money(sell)), right=True)
        margin = force_ltr(QLabel(f"{100 * (sell - buy) / sell:.1f}%" if sell > 0 and buy > 0 else T("N/A")), right=True)
        margin.setToolTip(T("Gross margin at the current selling price, before discounts"))
        for label in (cost_label, margin):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background:transparent; border:none; color:#334155;")
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price.setStyleSheet("""
            QLabel {
                color: #0f766e;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        expiry_badge = QLabel(T(expiry_status))
        expiry_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        expiry_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        expiry_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {expiry_color};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        expiry_badge.setMinimumHeight(24)

        expiry_date = force_ltr(QLabel(format_date(row_data["expiry_date"])))
        expiry_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        expiry_date.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        expiry_badge.setFixedHeight(24)
        expiry_date.setFixedHeight(18)

        expiry_badge.setFixedHeight(24)
        expiry_date.setFixedHeight(18)

        expiry_wrap = QWidget()
        expiry_wrap.setStyleSheet(
            "background: transparent; border: none;"
        )

        expiry_layout = QVBoxLayout()
        expiry_layout.setContentsMargins(0, 0, 0, 0)
        expiry_layout.setSpacing(4)

        expiry_layout.addStretch()
        expiry_layout.addWidget(
            expiry_badge,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        expiry_layout.addWidget(
            expiry_date,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        expiry_layout.addStretch()

        expiry_wrap.setLayout(expiry_layout)


        actions = QWidget()
        actions.setStyleSheet("background: transparent; border: none;")
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        edit_btn = QPushButton(T("Edit"))
        edit_btn.setFixedSize(58, 32)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.open_edit_dialog(row_data))

        delete_btn = QPushButton(T("Delete"))
        delete_btn.setFixedSize(72, 32)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_batch(row_data))

        edit_btn.setStyleSheet("""
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

        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(delete_btn)
        actions.setLayout(actions_layout)

        category_wrap = QWidget()
        category_wrap.setStyleSheet("background: transparent; border: none;")
        category_layout = QHBoxLayout()
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.addStretch()
        category_layout.addWidget(category, alignment=Qt.AlignmentFlag.AlignCenter)
        category_layout.addStretch()
        category_wrap.setLayout(category_layout)

        stock_wrap = QWidget()
        stock_wrap.setStyleSheet("background: transparent; border: none;")
        stock_layout = QHBoxLayout()
        stock_layout.setContentsMargins(0, 0, 0, 0)
        stock_layout.addStretch()
        stock_layout.addWidget(stock, alignment=Qt.AlignmentFlag.AlignCenter)
        stock_layout.addStretch()
        stock_wrap.setLayout(stock_layout)

        widgets = [
            medicine,
            category_wrap,
            batch,
            stock_wrap,
            cost_label,
            price,
            margin,
            expiry_wrap,
            actions,
        ]

        self.configure_table_columns(layout, widgets)

        row.setLayout(layout)
        
        return row

    def open_add_dialog(self):
        dialog = BatchFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.get_payload()
        if not self.validate_payload(payload):
            return

        product = get_product_by_name(payload["name"])
        if not product:
            QMessageBox.warning(
                self,
                T("Invalid Product"),
                T("This product does not exist. Please add batches only for existing medicines.")
            )
            return

        success, message = add_batch_record(
            payload["name"], payload["batch_number"], payload["quantity"],
            payload["expiry_date"], payload["purchase_unit_cost"],
        )

        if not success:
            QMessageBox.warning(self, T("Add Batch Failed"), T(message))
            return

        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Added batch {payload['batch_number']} for {payload['name']}",
            role=self.current_user.get("role", "")
        )

        self.reload_filters()
        self.refresh_table()


    def open_edit_dialog(self, row_data):
        dialog = BatchFormDialog(self, row_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.get_payload()
        if not self.validate_payload(payload):
            return

        reason = "Batch details edited"
        if int(payload["quantity"]) != int(row_data["stock"]):
            from PyQt6.QtWidgets import QInputDialog
            reason, ok = QInputDialog.getText(
                self, T("Stock adjustment"),
                T("Reason for changing stock (for example, damage or count correction):")
            )
            if not ok:
                return
            reason = reason.strip()
            if not reason:
                QMessageBox.warning(self, T("Reason required"), T("Stock was not changed."))
                return

        if not update_batch_record(
            row_data["batch_id"], payload["quantity"], payload["expiry_date"],
            payload["price"], payload["min_stock_level"], reason=reason,
        ):
            QMessageBox.warning(self, T("Not saved"), T("This batch no longer exists."))
            return

        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Updated batch {row_data['batch_number']} for {row_data['name']}",
            role=self.current_user.get("role", "")
        )

        self.refresh_table()

    def delete_batch(self, row_data):
        confirm = QMessageBox.question(
            self,
            T("Delete Batch"),
            TF("Delete batch {batch} for {name}?", batch=row_data["batch_number"], name=row_data["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        delete_batch_record(row_data["batch_id"])
        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Deleted batch {row_data['batch_number']} for {row_data['name']}",
            role=self.current_user.get("role", "")
        )
        self.refresh_table()

    def validate_payload(self, payload):
        required = ["name", "batch_number", "quantity", "expiry_date"]
        if any(not payload[key] for key in required):
            QMessageBox.warning(self, T("Missing Data"), T("Please fill in every required field."))
            return False

        try:
            quantity = int(payload["quantity"])
            if quantity < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, T("Invalid Data"), T("Quantity must be a valid non-negative number."))
            return False

        try:
            datetime.strptime(payload["expiry_date"], "%Y-%m-%d")
        except ValueError:
            QMessageBox.warning(self, T("Invalid Date"), T("Expiry date must be in YYYY-MM-DD format."))
            return False

        return True
