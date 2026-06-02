from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QComboBox, QScrollArea,
    QSizePolicy, QMessageBox, QDialog, QFormLayout,
    QSpinBox
)

from database.db import (
    cart_requires_prescription,
    create_sale,
    get_categories,
    get_products_for_pos,
    get_available_stock,
    is_valid_customer_ssn,
    preview_sale_allocations,
)






class BatchPickDialog(QDialog):
    def __init__(self, lines, total_amount, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Batch Picking Instructions")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Pick items from these batches")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #111827;
            }
        """)
        layout.addWidget(title)

        for line in lines:
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

            name = QLabel(f"{line['product_name']} x{line['quantity']}")
            name.setStyleSheet("""
                QLabel {
                    font-size: 15px;
                    font-weight: 700;
                    color: #111827;
                }
            """)
            card_layout.addWidget(name)

            for allocation in line["allocations"]:
                info = QLabel(
                    f"Take {allocation['quantity']} from batch "
                    f"{allocation['batch_number']} "
                    f"(expires {allocation['expiry_date']})"
                )
                info.setStyleSheet("color: #374151; font-size: 13px;")
                card_layout.addWidget(info)

            card.setLayout(card_layout)
            layout.addWidget(card)

        total = QLabel(f"Total: {total_amount:g} Ft")
        total.setAlignment(Qt.AlignmentFlag.AlignRight)
        total.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: 800;
                color: #111827;
            }
        """)
        layout.addWidget(total)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Confirm Checkout")

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


class PaymentMethodDialog(QDialog):
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Payment Method")
        self.setModal(True)
        self.setFixedWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Select payment method")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #111827;
            }
        """)

        total = QLabel(f"Total: {total_amount:g} Ft")
        total.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 700;
                color: #0f766e;
            }
        """)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Card"])
        self.method_combo.setFixedHeight(38)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #111827;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
                background: transparent;
            }
        """)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Confirm")

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

        layout.addWidget(title)
        layout.addWidget(total)
        layout.addWidget(self.method_combo)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def get_payment_method(self):
        return self.method_combo.currentText()



class QuantityDialog(QDialog):
    def __init__(self, product_name, max_quantity, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select Quantity")
        self.setModal(True)
        self.setFixedWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(f"{product_name}")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #111827;
            }
        """)

        form = QFormLayout()
        form.setSpacing(12)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, max_quantity)
        self.quantity_input.setValue(1)
        self.quantity_input.setFixedHeight(38)
        self.quantity_input.setStyleSheet("""
            QSpinBox {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #111827;
            }
            QSpinBox:focus {
                border: 1px solid #2563eb;
            }
        """)
        form.addRow("Quantity", self.quantity_input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Add")

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

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def get_quantity(self):
        return int(self.quantity_input.value())


class CustomerIdentityDialog(QDialog):
    def __init__(self, details_required=False, parent=None):
        super().__init__(parent)

        self.details_required = details_required
        self.declined = False

        self.setWindowTitle("Customer Details")
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Customer details")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #111827;
            }
        """)

        subtitle = QLabel(
            "SSN and name are required because the cart contains prescription products."
            if details_required else
            "Customer can share SSN and name, or decline for non-prescription purchases."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6b7280;
            }
        """)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Customer name")
        self.name_input.setFixedHeight(38)

        self.ssn_input = QLineEdit()
        self.ssn_input.setPlaceholderText("Customer SSN")
        self.ssn_input.setFixedHeight(38)

        input_style = """
            QLineEdit {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #111827;
            }

            QLineEdit:focus {
                border: 1px solid #2563eb;
            }
        """

        self.name_input.setStyleSheet(input_style)
        self.ssn_input.setStyleSheet(input_style)

        form.addRow("Customer Name", self.name_input)
        form.addRow("Customer SSN", self.ssn_input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        if not details_required:
            decline_btn = QPushButton("Decline")
            decline_btn.setFixedHeight(38)
            decline_btn.clicked.connect(self.decline)
            button_row.addWidget(decline_btn)

        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Continue")

        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)

        cancel_btn.setFixedHeight(40)
        confirm_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(soft_button_style())
        confirm_btn.setStyleSheet(primary_button_style(BLUE, BLUE))

        button_row.addWidget(cancel_btn)
        button_row.addWidget(confirm_btn)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def decline(self):
        self.declined = True
        self.accept()

    def get_payload(self):
        return {
            "declined": self.declined,
            "customer_name": self.name_input.text().strip(),
            "customer_ssn": self.ssn_input.text().strip(),
        }



class POSPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()

        self.current_user = current_user or {}
        self.cart = {}

        self.setObjectName("posPage")

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 24, 24, 22)
        main_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(18)

        title = QLabel("Point of Sale")
        title.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 23px;
                font-weight: 800;
                background: transparent;
            }
        """)

        subtitle = QLabel("Search products, add medicines to cart, and checkout")
        subtitle.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 14px;
                background: transparent;
            }
        """)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        left_layout.addLayout(title_box)

        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search medicines by name or barcode")
        self.search_input.setFixedHeight(42)
        self.search_input.textChanged.connect(self.refresh_products)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(42)
        self.category_filter.currentTextChanged.connect(self.refresh_products)

        input_style = """
            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 14px;
                color: #111827;
                font-size: 14px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #2563eb;
            }

            QLineEdit:disabled {
                background-color: #f8fafc;
                color: #9ca3af;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
                background: transparent;
            }

            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }

            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e5e7eb;
                selection-background-color: #eef5ff;
                selection-color: #111827;
                outline: none;
                padding: 4px;
            }

            QComboBox QAbstractItemView::item {
                min-height: 32px;
                padding: 6px 10px;
                border-radius: 6px;
            }

            QComboBox QAbstractItemView QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 2px;
                border: none;
            }

            QComboBox QAbstractItemView QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 40px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }

            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: transparent;
            }

            QComboBox QAbstractItemView QScrollBar::add-page:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """

        self.search_input.setStyleSheet(input_style)
        self.category_filter.setStyleSheet(input_style)


        search_row.addWidget(self.search_input, stretch=5)
        search_row.addWidget(self.category_filter, stretch=2)
        left_layout.addLayout(search_row)

        self.product_grid = QGridLayout()
        self.product_grid.setHorizontalSpacing(16)
        self.product_grid.setVerticalSpacing(16)
        self.product_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        product_grid_widget = QWidget()
        product_grid_widget.setStyleSheet("background: transparent;")

        grid_wrapper = QVBoxLayout()
        grid_wrapper.setContentsMargins(0, 0, 0, 0)
        grid_wrapper.setSpacing(0)
        grid_wrapper.addLayout(self.product_grid)
        grid_wrapper.addStretch()

        product_grid_widget.setLayout(grid_wrapper)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(product_grid_widget)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 6px 2px 6px 2px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 2px 6px 2px 6px;
                border: none;
            }

            QScrollBar::handle:horizontal {
                background: #cbd5e1;
                min-width: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #94a3b8;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)

        left_layout.addWidget(scroll_area, stretch=1)

        cart_panel = self.create_cart_panel()

        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addWidget(cart_panel, stretch=1)

        self.setLayout(main_layout)
        self.setStyleSheet("""
            QWidget#posPage {
                background-color: #f8faf9;
            }
        """)

        self.refresh_filters()
        self.refresh_products()
        self.update_cart()

    def refresh_filters(self):
        selected = self.category_filter.currentText()

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for category in get_categories():
            self.category_filter.addItem(category)

        index = self.category_filter.findText(selected)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def create_product_card(self, product):
        card = QFrame()
        card.setMinimumHeight(172)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e7edf3;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        name = QLabel(product["name"])
        name.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 16px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        category = QLabel(product["category"])
        category.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)

        prescription_label = None
        if product.get("prescription_required"):
            prescription_label = QLabel("Requires prescription")
            prescription_label.setStyleSheet("""
                QLabel {
                    background-color: #fff7ed;
                    color: #c2410c;
                    border: 1px solid #fdba74;
                    border-radius: 10px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)

        available_display = "100+" if product["available_stock"] > 100 else str(product["available_stock"])
        available_label = QLabel(f"Available: {available_display}")
        available_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)

        price_row = QHBoxLayout()
        price_row.setSpacing(8)

        if product.get("has_discount"):
            old_price = QLabel(f"{product['original_price']:g} Ft")
            old_price.setStyleSheet("""
                QLabel {
                    color: #9ca3af;
                    font-size: 13px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                    text-decoration: line-through;
                }
            """)

            new_price = QLabel(f"{product['price']:g} Ft")
            new_price.setStyleSheet("""
                QLabel {
                    color: #dc2626;
                    font-size: 15px;
                    font-weight: 800;
                    background: transparent;
                    border: none;
                }
            """)

            discount_badge = QLabel(f"-{int(product['discount_percent'])}%")
            discount_badge.setStyleSheet("""
                QLabel {
                    background-color: #fef2f2;
                    color: #dc2626;
                    border-radius: 10px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)

            price_row.addWidget(old_price)
            price_row.addWidget(new_price)
            price_row.addWidget(discount_badge)
            price_row.addStretch()
        else:
            price = QLabel(f"{product['price']:g} Ft")
            price.setStyleSheet("""
                QLabel {
                    color: #0f766e;
                    font-size: 15px;
                    font-weight: 800;
                    background: transparent;
                    border: none;
                }
            """)
            price_row.addWidget(price)
            price_row.addStretch()

        add_btn = QPushButton("Add")
        add_btn.setFixedSize(72, 34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setEnabled(product["available_stock"] > 0)
        add_btn.clicked.connect(lambda: self.add_to_cart(product))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
            }

            QPushButton:hover {
                background-color: #16a34a;
            }

            QPushButton:pressed {
                background-color: #15803d;
            }

            QPushButton:disabled {
                background-color: #d1d5db;
                color: white;
            }
        """)

        bottom_row = QHBoxLayout()
        bottom_row.addLayout(price_row)
        bottom_row.addWidget(add_btn)

        layout.addWidget(name)
        layout.addWidget(category)
        if prescription_label is not None:
            layout.addWidget(prescription_label)
        layout.addStretch()
        layout.addWidget(available_label)
        layout.addLayout(bottom_row)

        card.setLayout(layout)
        return card

    def sync_cart_pricing(self):
        if not self.cart:
            return

        current_products = {
            product["id"]: product
            for product in get_products_for_pos()
        }

        missing_product_ids = []

        for product_id, item in self.cart.items():
            current_product = current_products.get(product_id)
            if current_product is None:
                missing_product_ids.append(product_id)
                continue

            item["name"] = current_product["name"]
            item["price"] = current_product["price"]
            item["original_price"] = current_product.get("original_price", current_product["price"])
            item["has_discount"] = current_product.get("has_discount", False)
            item["discount_percent"] = current_product.get("discount_percent", 0)

        for product_id in missing_product_ids:
            self.cart.pop(product_id, None)


    def create_cart_panel(self):
        panel = QFrame()
        panel.setMinimumWidth(300)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e7edf3;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Cart")
        title.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 20px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        self.cart_list = QListWidget()
        self.cart_list.setFrameShape(QFrame.Shape.NoFrame)
        self.cart_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.cart_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: none;
                outline: none;
                color: #374151;
                font-size: 13px;
            }

            QListWidget::item {
                border-bottom: 1px solid #f1f5f9;
                padding: 10px 0;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 0 4px 0;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 40px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
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

        self.total_label = QLabel("Total: 0 Ft")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 18px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        checkout_btn = QPushButton("Checkout")
        checkout_btn.setFixedHeight(42)
        checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        checkout_btn.clicked.connect(self.checkout)
        checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        clear_btn = QPushButton("Empty Cart")
        clear_btn.setFixedHeight(40)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.empty_cart)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff1f2;
                color: #dc2626;
                border: 1px solid #fecdd3;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #ffe4e6;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(self.cart_list, stretch=1)
        layout.addWidget(self.total_label)
        layout.addWidget(clear_btn)
        layout.addWidget(checkout_btn)

        panel.setLayout(layout)
        return panel

    def refresh_products(self):
        while self.product_grid.count():
            item = self.product_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        search_text = self.search_input.text().strip()
        selected_category = self.category_filter.currentText()

        filtered_products = get_products_for_pos(search_text, selected_category)

        if not filtered_products:
            empty_label = QLabel("No medicines found")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setMinimumHeight(160)
            empty_label.setStyleSheet("""
                QLabel {
                    color: #6b7280;
                    font-size: 15px;
                    background-color: white;
                    border: 1px solid #edf0f4;
                    border-radius: 9px;
                }
            """)
            self.product_grid.addWidget(empty_label, 0, 0, 1, 3)
            return

        for index, product in enumerate(filtered_products):
            row = index // 3
            column = index % 3
            self.product_grid.addWidget(
                self.create_product_card(product),
                row,
                column
            )

        for column in range(3):
            self.product_grid.setColumnStretch(column, 1)

        for row in range((len(filtered_products) // 3) + 2):
            self.product_grid.setRowStretch(row, 0)

    def add_to_cart(self, product):
        product_id = product["id"]
        available_stock = get_available_stock(product_id)
        already_in_cart = self.cart.get(product_id, {}).get("quantity", 0)
        max_addable = available_stock - already_in_cart

        if max_addable <= 0:
            QMessageBox.warning(
                self,
                "Stock Limit",
                f"Only {available_stock} non-expired unit(s) of {product['name']} are available."
            )
            return

        dialog = QuantityDialog(product["name"], max_addable, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        quantity_to_add = dialog.get_quantity()

        if product_id not in self.cart:
            self.cart[product_id] = {
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "original_price": product.get("original_price", product["price"]),
                "has_discount": product.get("has_discount", False),
                "discount_percent": product.get("discount_percent", 0),
                "prescription_required": product.get("prescription_required", False),
                "quantity": 0,
            }


        self.cart[product_id]["quantity"] += quantity_to_add
        self.update_cart()

    def update_cart(self):

        self.sync_cart_pricing()
        self.cart_list.clear()
        total = 0

        if not self.cart:
            empty_item = QListWidgetItem("Cart is empty")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cart_list.addItem(empty_item)
            self.total_label.setText("Total: 0 Ft")
            return

        for item in self.cart.values():
            subtotal = item["price"] * item["quantity"]
            total += subtotal

            line_text = f"{item['name']} x{item['quantity']} = {subtotal:g} Ft"
            self.cart_list.addItem(line_text)

        self.total_label.setText(f"Total: {total:g} Ft")



    def checkout(self):
        if not self.cart:
            QMessageBox.information(
                self,
                "Cart Empty",
                "Please add medicines to the cart first."
            )
            return

        self.sync_cart_pricing()
        self.update_cart()

        cart_items = list(self.cart.values())

        identity_required = cart_requires_prescription(cart_items)

        identity_dialog = CustomerIdentityDialog(details_required=identity_required, parent=self)
        if identity_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        identity = identity_dialog.get_payload()
        customer_name = identity["customer_name"]
        customer_ssn = identity["customer_ssn"]

        if identity_required and (not customer_name or not customer_ssn):
            QMessageBox.warning(
                self,
                "Customer Details Required",
                "Customer SSN and name are required because the cart contains prescription products."
            )
            return

        if not identity_required and identity["declined"]:
            customer_name = None
            customer_ssn = None
        elif customer_name or customer_ssn:
            if not customer_name or not customer_ssn:
                QMessageBox.warning(
                    self,
                    "Incomplete Details",
                    "Please provide both customer name and SSN, or decline."
                )
                return

        if customer_ssn and not is_valid_customer_ssn(customer_ssn):
            QMessageBox.warning(
                self,
                "Invalid SSN",
                "Customer SSN must contain 9 digits."
            )
            return

        try:
            plan, total_amount = preview_sale_allocations(cart_items)
        except ValueError as error:
            QMessageBox.warning(self, "Insufficient Stock", str(error))
            return

        dialog = BatchPickDialog(plan, total_amount, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payment_dialog = PaymentMethodDialog(total_amount, self)
        if payment_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payment_method = payment_dialog.get_payment_method()

        try:
            create_sale(
                cart_items,
                payment_method,
                cashier_id=self.current_user.get("id", 1),
                acting_username=self.current_user.get("username"),
                acting_role=self.current_user.get("role"),
                customer_ssn=customer_ssn or None,
                customer_name=customer_name or None
            )
        except ValueError as error:
            QMessageBox.warning(self, "Checkout Failed", str(error))
            return

        self.cart.clear()
        self.update_cart()
        self.refresh_products()

        QMessageBox.information(
            self,
            "Checkout Complete",
            "Sale saved and FEFO picking instructions confirmed."
        )




    def empty_cart(self):
        if not self.cart:
            QMessageBox.information(
                self,
                "Cart Empty",
                "The cart is already empty."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Empty Cart",
            "Are you sure you want to remove all items from the cart?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.cart.clear()
        self.update_cart()


