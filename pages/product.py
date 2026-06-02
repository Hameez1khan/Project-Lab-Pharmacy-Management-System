from PyQt6.QtCore import Qt
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
    add_product_record,
    delete_product_record,
    get_categories,
    get_product_rows,
    update_product_record,
)
from ui_theme import (
    PRIMARY,
    BLUE,
    filter_card_style,
    header_caps_style,
    input_style,
    page_root_style,
    page_subtitle_style,
    page_title_style,
    primary_button_style,
    primary_text_style,
    scroll_area_style,
    secondary_text_style,
    soft_button_style,
    table_container_style,
    table_row_style,
    checkbox_style,
    badge_style,
)


class ProductFormDialog(QDialog):
    def __init__(self, parent=None, product_row=None):
        super().__init__(parent)
        self.product_row = product_row

        self.setWindowTitle("Add Product" if product_row is None else "Edit Product")
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout()
        form = QFormLayout()
        form.setSpacing(14)

        self.name_input = QLineEdit()
        self.dosage_form_input = QLineEdit()
        self.barcode_input = QLineEdit()
        self.price_input = QLineEdit()
        self.min_stock_input = QLineEdit()
        self.category_input = QLineEdit()

        self.prescription_required_input = QCheckBox("Requires Prescription")
        self.prescription_required_input.setStyleSheet(checkbox_style(accent=BLUE))


        fields = [
            ("Medicine", self.name_input),
            ("Dosage Form", self.dosage_form_input),
            ("Barcode", self.barcode_input),
            ("Selling Price", self.price_input),
            ("Min Stock", self.min_stock_input),
            ("Category", self.category_input),
        ]

        for label, widget in fields:
            widget.setFixedHeight(42)
            widget.setStyleSheet(input_style())
            form.addRow(label, widget)

        form.addRow("Prescription", self.prescription_required_input)

        if product_row:
            self.name_input.setText(product_row["name"])
            self.dosage_form_input.setText(product_row["dosage_form"])
            self.barcode_input.setText(product_row["barcode"])
            self.price_input.setText(str(product_row["selling_price"]))
            self.min_stock_input.setText(str(product_row["min_stock_level"]))
            self.category_input.setText(product_row["category"])
            self.prescription_required_input.setChecked(product_row["prescription_required"])


        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        save_btn = QPushButton("Save")

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
            "dosage_form": self.dosage_form_input.text().strip(),
            "barcode": self.barcode_input.text().strip(),
            "selling_price": self.price_input.text().strip(),
            "min_stock_level": self.min_stock_input.text().strip(),
            "category": self.category_input.text().strip(),
            "prescription_required": self.prescription_required_input.isChecked(),
        }


class ProductPage(QWidget):
    def __init__(self, role="admin", current_user=None):
        super().__init__()

        self.role = (role or "admin").lower()
        self.is_admin = self.role == "admin"
        self.current_user = current_user or {}

        self.setObjectName("productPage")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(22)

        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        title = QLabel("Products")
        title.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        subtitle = QLabel("View and manage product records")
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

        if self.is_admin:
            add_btn = QPushButton("+ Add Product")
            add_btn.setFixedSize(170, 42)
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
            header_row.addWidget(add_btn)

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
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.setFixedHeight(44)
        self.search_input.textChanged.connect(self.refresh_table)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(44)
        self.category_filter.setFixedWidth(340)
        self.category_filter.currentTextChanged.connect(self.refresh_table)

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

        filter_layout.addWidget(self.search_input, stretch=1)
        filter_layout.addWidget(self.category_filter)
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
        self.setStyleSheet(page_root_style("productPage"))

        self.reload_filters()
        self.refresh_table()

    def reload_filters(self):
        current = self.category_filter.currentText()

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for category in get_categories():
            self.category_filter.addItem(category)

        index = self.category_filter.findText(current)
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

        layout.addWidget(self.make_header_row())

        rows = get_product_rows(
            search_text=self.search_input.text(),
            category=self.category_filter.currentText(),
        )

        if not rows:
            empty = QLabel("No products found")
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
                layout.addWidget(self.make_product_row(row))

        container.setLayout(layout)
        self.table_layout.addWidget(container)

    def make_header_row(self):
        row = QWidget()
        row.setFixedHeight(52)
        row.setStyleSheet("background: transparent; border: none;")

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)

        labels = ["NAME", "FORM", "BARCODE", "PRICE", "MIN STOCK", "CATEGORY", "RX", "AVAILABLE"]
        stretches = [3, 2, 3, 2, 2, 2, 1, 2]


        if self.is_admin:
            labels.append("ACTIONS")
            stretches.append(2)

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
            if text in {"CATEGORY", "RX", "AVAILABLE"}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            if text == "ACTIONS":
                alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(label, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def make_product_row(self, row_data):
        row = QFrame()
        row.setObjectName("productRow")
        row.setFixedHeight(82)
        row.setStyleSheet("""
            QFrame#productRow {
                border-top: 1px solid #edf2f7;
                background-color: white;
                border-radius: 0px;
            }
        """)

        layout = QGridLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(0)

        widgets = []

        name = QLabel(row_data["name"])
        name.setStyleSheet("""
            QLabel {
                color: #0f172a;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        dosage_form = QLabel(row_data["dosage_form"])
        dosage_form.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        barcode = QLabel(row_data["barcode"] or "-")
        barcode.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        price = QLabel(f"{row_data['selling_price']:g} Ft")
        price.setStyleSheet("""
            QLabel {
                color: #0f766e;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        min_stock = QLabel(str(row_data["min_stock_level"]))
        min_stock.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        category = QLabel(row_data["category"])
        category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        category.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        category.setMinimumHeight(26)
        category.setStyleSheet("""
            QLabel {
                background-color: #eef4ff;
                color: #2563eb;
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }
        """)

        prescription = QLabel("Yes" if row_data["prescription_required"] else "No")
        prescription.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prescription.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        prescription.setMinimumHeight(26)
        prescription.setStyleSheet(f"""
            QLabel {{
                background-color: {'#fff1f2' if row_data['prescription_required'] else '#ecfdf5'};
                color: {'#dc2626' if row_data['prescription_required'] else '#16a34a'};
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }}
        """)

        available_color = "#dc2626" if row_data["available_stock"] <= 0 else "#16a34a"
        available_bg = "#fff1f2" if row_data["available_stock"] <= 0 else "#ecfdf5"
        available_stock = QLabel(f"{row_data['available_stock']} units")
        available_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        available_stock.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        available_stock.setMinimumHeight(26)
        available_stock.setStyleSheet(f"""
            QLabel {{
                background-color: {available_bg};
                color: {available_color};
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
                border: none;
            }}
        """)

        widgets.extend([name, dosage_form, barcode, price, min_stock, category, prescription, available_stock])

        stretches = [3, 2, 3, 2, 2, 2, 1, 2]


        if self.is_admin:
            actions = QWidget()
            actions.setStyleSheet("background: transparent; border: none;")
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(8)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(56, 30)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.open_edit_dialog(row_data))

            delete_btn = QPushButton("Delete")
            delete_btn.setFixedSize(64, 30)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda: self.delete_product(row_data))

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

            actions_layout.addStretch()
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions.setLayout(actions_layout)

            widgets.append(actions)
            stretches.append(2)

        category_wrap = QWidget()
        category_wrap.setStyleSheet("background: transparent; border: none;")
        category_layout = QHBoxLayout()
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.addStretch()
        category_layout.addWidget(category, alignment=Qt.AlignmentFlag.AlignCenter)
        category_layout.addStretch()
        category_wrap.setLayout(category_layout)

        prescription_wrap = QWidget()
        prescription_wrap.setStyleSheet("background: transparent; border: none;")
        prescription_layout = QHBoxLayout()
        prescription_layout.setContentsMargins(0, 0, 0, 0)
        prescription_layout.addStretch()
        prescription_layout.addWidget(prescription, alignment=Qt.AlignmentFlag.AlignCenter)
        prescription_layout.addStretch()
        prescription_wrap.setLayout(prescription_layout)

        available_wrap = QWidget()
        available_wrap.setStyleSheet("background: transparent; border: none;")
        available_layout = QHBoxLayout()
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.addStretch()
        available_layout.addWidget(available_stock, alignment=Qt.AlignmentFlag.AlignCenter)
        available_layout.addStretch()
        available_wrap.setLayout(available_layout)

        widgets = [name, dosage_form, barcode, price, min_stock, category_wrap, prescription_wrap, available_wrap]

        if self.is_admin:
            widgets.append(actions)

        for index, widget in enumerate(widgets):
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if index in {5, 6, 7}:
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            if self.is_admin and index == len(widgets) - 1:
                alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            layout.addWidget(widget, 0, index, alignment=alignment)
            layout.setColumnStretch(index, stretches[index])

        row.setLayout(layout)
        return row

    def open_add_dialog(self):
        dialog = ProductFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.get_payload()
        if not self.validate_payload(payload):
            return

        success, message = add_product_record(
            payload["name"],
            payload["dosage_form"],
            payload["barcode"],
            payload["selling_price"],
            payload["min_stock_level"],
            payload["category"],
            prescription_required=payload["prescription_required"],
        )


        if not success:
            QMessageBox.warning(self, "Add Product Failed", message)
            return

        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Added product {payload['name']}",
            role=self.current_user.get("role", "")
        )

        self.reload_filters()
        self.refresh_table()

    def open_edit_dialog(self, row_data):
        dialog = ProductFormDialog(self, row_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.get_payload()
        if not self.validate_payload(payload):
            return

        success, message = update_product_record(
            row_data["id"],
            payload["name"],
            payload["dosage_form"],
            payload["barcode"],
            payload["selling_price"],
            payload["min_stock_level"],
            payload["category"],
            payload["prescription_required"],
        )


        if not success:
            QMessageBox.warning(self, "Update Product Failed", message)
            return

        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Updated product {payload['name']}",
            role=self.current_user.get("role", "")
        )

        self.reload_filters()
        self.refresh_table()

    def delete_product(self, row_data):
        confirm = QMessageBox.question(
            self,
            "Delete Product",
            f"Delete product {row_data['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_product_record(row_data["id"])

        if not success:
            QMessageBox.warning(self, "Delete Failed", message)
            return

        add_audit_log(
            self.current_user.get("username", "Unknown"),
            f"Deleted product {row_data['name']}",
            role=self.current_user.get("role", "")
        )

        QMessageBox.information(self, "Product Deleted", message)
        self.reload_filters()
        self.refresh_table()

    def validate_payload(self, payload):
        required = ["name", "selling_price", "min_stock_level", "category"]
        if any(not payload[key] for key in required):
            QMessageBox.warning(self, "Missing Data", "Please fill in all required fields.")
            return False

        try:
            price = float(payload["selling_price"])
            if price < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Data", "Selling price must be a valid non-negative number.")
            return False

        try:
            min_stock = int(payload["min_stock_level"])
            if min_stock < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Data", "Min stock must be a valid non-negative number.")
            return False

        barcode = payload["barcode"].strip()
        if barcode and not barcode.isdigit():
            QMessageBox.warning(
                self,
                "Invalid Barcode",
                "Product barcode must contain digits only."
            )
            return False

        return True

