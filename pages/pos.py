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
from database.performance import CheckoutPerformance, measure_metric
from i18n import T, TF, force_ltr, format_date, format_money, ltr_text

BLUE = "#147a61"


def build_receipt_summary(plan, total_amount, payment_method):
    """Create the non-sensitive receipt data used by the completion message."""
    return {
        "items": [
            {
                "name": line["product_name"],
                "quantity": int(line["quantity"]),
                "unit_price": float(line["price"]),
                "subtotal": float(line["subtotal"]),
            }
            for line in plan
        ],
        "total": float(total_amount),
        "payment_method": payment_method,
    }


def soft_button_style():
    return """
        QPushButton {
            background-color: #f8fafc;
            color: #18251f;
            border: 1px solid #dbe4ee;
            border-radius: 8px;
            padding: 0 14px;
            font-weight: 700;
        }

        QPushButton:hover {
            background-color: #eef5ff;
        }
    """


def primary_button_style(background_color, hover_color):
    return f"""
        QPushButton {{
            background-color: {background_color};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0 14px;
            font-weight: 700;
        }}

        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """


def run_centered_modal(dialog, parent=None):
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    dialog.adjustSize()

    if parent is not None:
        parent_geometry = parent.frameGeometry()
        dialog_geometry = dialog.frameGeometry()
        dialog_geometry.moveCenter(parent_geometry.center())
        dialog.move(dialog_geometry.topLeft())

    dialog.raise_()
    dialog.activateWindow()
    return dialog.exec()






class BatchPickDialog(QDialog):
    def __init__(self, lines, total_amount, parent=None):
        super().__init__(parent)

        self.setWindowTitle(T("Batch Picking Instructions"))
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(T("Pick items from these batches"))
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #18251f;
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

            name = QLabel(TF("{name} × {count}", name=line["product_name"], count=line["quantity"]))
            name.setStyleSheet("""
                QLabel {
                    font-size: 15px;
                    font-weight: 700;
                    color: #18251f;
                }
            """)
            card_layout.addWidget(name)

            for allocation in line["allocations"]:
                info = QLabel(TF(
                    "Take {quantity} from batch {batch} (expires {expiry})",
                    quantity=allocation["quantity"],
                    batch=allocation["batch_number"],
                    expiry=format_date(allocation["expiry_date"]),
                ))
                info.setStyleSheet("color: #374151; font-size: 13px;")
                card_layout.addWidget(info)

            card.setLayout(card_layout)
            layout.addWidget(card)

        total = QLabel(TF("Total: {amount} Ft", amount=ltr_text(f"{total_amount:g}")))
        total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total.setAlignment(Qt.AlignmentFlag.AlignRight)
        total.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: 800;
                color: #18251f;
            }
        """)
        layout.addWidget(total)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton(T("Cancel"))
        confirm_btn = QPushButton(T("Confirm Checkout"))

        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)

        cancel_btn.setFixedHeight(38)
        confirm_btn.setFixedHeight(38)

        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #147a61;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #0f654f;
            }
        """)

        button_row.addWidget(cancel_btn)
        button_row.addWidget(confirm_btn)
        layout.addLayout(button_row)

        self.setLayout(layout)


class PaymentMethodDialog(QDialog):
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)

        self.setWindowTitle(T("Payment Method"))
        self.setModal(True)
        self.setFixedWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(T("Select payment method"))
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #18251f;
            }
        """)

        total = QLabel(TF("Total: {amount} Ft", amount=ltr_text(f"{total_amount:g}")))
        total.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 700;
                color: #147a61;
            }
        """)

        self.method_combo = QComboBox()
        self.method_combo.addItem(T("Cash"), "Cash")
        self.method_combo.addItem(T("Card"), "Card")
        self.method_combo.setFixedHeight(38)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #18251f;
            }

            QComboBox::drop-down {
                border: none;
                width: 28px;
                background: transparent;
            }
        """)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton(T("Cancel"))
        confirm_btn = QPushButton(T("Confirm"))

        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)

        cancel_btn.setFixedHeight(38)
        confirm_btn.setFixedHeight(38)

        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #147a61;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #0f654f;
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
        return self.method_combo.currentData()



class QuantityDialog(QDialog):
    def __init__(self, product_name, max_quantity, parent=None):
        super().__init__(parent)

        self.setWindowTitle(T("Select Quantity"))
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
                color: #18251f;
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
                color: #18251f;
            }
            QSpinBox:focus {
                border: 1px solid #147a61;
            }
        """)
        form.addRow(T("Quantity"), self.quantity_input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton(T("Cancel"))
        confirm_btn = QPushButton(T("Add"))

        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)

        cancel_btn.setFixedHeight(38)
        confirm_btn.setFixedHeight(38)

        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #147a61;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #0f654f;
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

        self.setWindowTitle(T("Customer details"))
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(T("Customer details"))
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #18251f;
            }
        """)

        subtitle = QLabel(T(
            "SSN and name are required because the cart contains prescription products."
            if details_required else
            "Customer can share SSN and name, or decline for non-prescription purchases."
        ))
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
        self.name_input.setPlaceholderText(T("Customer name"))
        self.name_input.setFixedHeight(38)

        self.ssn_input = QLineEdit()
        self.ssn_input.setPlaceholderText(T("Customer SSN"))
        force_ltr(self.ssn_input)
        self.ssn_input.setFixedHeight(38)

        input_style = """
            QLineEdit {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #18251f;
            }

            QLineEdit:focus {
                border: 1px solid #147a61;
            }
        """

        self.name_input.setStyleSheet(input_style)
        self.ssn_input.setStyleSheet(input_style)

        form.addRow(T("Customer Name"), self.name_input)
        form.addRow(T("Customer SSN"), self.ssn_input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        if not details_required:
            decline_btn = QPushButton(T("Decline"))
            decline_btn.setFixedHeight(38)
            decline_btn.clicked.connect(self.decline)
            button_row.addWidget(decline_btn)

        cancel_btn = QPushButton(T("Cancel"))
        confirm_btn = QPushButton(T("Continue"))

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

        title = QLabel(T("Point of Sale"))
        title.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 23px;
                font-weight: 800;
                background: transparent;
            }
        """)

        subtitle = QLabel(T("Search products, add medicines to cart, and checkout"))
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
        self.search_input.setPlaceholderText(T("Search medicines by name or barcode"))
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
                color: #18251f;
                font-size: 14px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #147a61;
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
                selection-color: #18251f;
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
                background: #bfcbc5;
                min-height: 40px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
                background: #96a89f;
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
                background: #bfcbc5;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #96a89f;
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
                background: #bfcbc5;
                min-width: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #96a89f;
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
        selected = self.category_filter.currentData()

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem(T("All Categories"), "")
        for category in get_categories():
            self.category_filter.addItem(category, category)

        index = self.category_filter.findData(selected)
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
                color: #18251f;
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
            prescription_label = QLabel(T("Requires prescription"))
            prescription_label.setStyleSheet("""
                QLabel {
                    background-color: #fff7e8;
                    color: #c2410c;
                    border: 1px solid #fdba74;
                    border-radius: 10px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)

        available_display = "100+" if product["available_stock"] > 100 else str(product["available_stock"])
        available_label = QLabel(TF("Available: {value}", value=available_display))
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
            old_price = force_ltr(QLabel(format_money(product["original_price"], 0)), right=True)
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

            new_price = force_ltr(QLabel(format_money(product["price"], 0)), right=True)
            new_price.setStyleSheet("""
                QLabel {
                    color: #c84b4b;
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
                    color: #c84b4b;
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
            price = force_ltr(QLabel(format_money(product["price"], 0)), right=True)
            price.setStyleSheet("""
                QLabel {
                    color: #147a61;
                    font-size: 15px;
                    font-weight: 800;
                    background: transparent;
                    border: none;
                }
            """)
            price_row.addWidget(price)
            price_row.addStretch()

        add_btn = QPushButton(T("Add"))
        add_btn.setFixedSize(72, 34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setEnabled(product["available_stock"] > 0)
        add_btn.clicked.connect(lambda: self.add_to_cart(product))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #147a61;
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

        title = QLabel(T("Cart"))
        title.setStyleSheet("""
            QLabel {
                color: #18251f;
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
                background: #bfcbc5;
                min-height: 40px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #96a89f;
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

        self.total_label = QLabel(TF("Total: {amount} Ft", amount=ltr_text("0")))
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label.setStyleSheet("""
            QLabel {
                color: #18251f;
                font-size: 18px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        checkout_btn = QPushButton(T("Checkout"))
        checkout_btn.setFixedHeight(42)
        checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        checkout_btn.clicked.connect(self.checkout)
        checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #147a61;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #0f654f;
            }
        """)

        clear_btn = QPushButton(T("Empty Cart"))
        clear_btn.setFixedHeight(40)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.empty_cart)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff0f0;
                color: #c84b4b;
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
        selected_category = self.category_filter.currentData() or ""

        search_kind = "barcode" if search_text and search_text.isdigit() else "text"
        with measure_metric(
            "search", "product_lookup", metadata={"search_kind": search_kind}
        ):
            filtered_products = get_products_for_pos(search_text, selected_category)

        if not filtered_products:
            empty_label = QLabel(T("No medicines found"))
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
        with measure_metric("cart", "availability_lookup"):
            available_stock = get_available_stock(product_id)
        already_in_cart = self.cart.get(product_id, {}).get("quantity", 0)
        max_addable = available_stock - already_in_cart

        if max_addable <= 0:
            QMessageBox.warning(
                self,
                T("Stock Limit"),
                TF("Only {count} non-expired unit(s) of {name} are available.", count=available_stock, name=product["name"])
            )
            return

        dialog = QuantityDialog(product["name"], max_addable, self)
        with measure_metric("cart", "quantity_selection", metric_kind="interaction"):
            if run_centered_modal(dialog, self) != QDialog.DialogCode.Accepted:
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


        with measure_metric("cart", "cart_update"):
            self.cart[product_id]["quantity"] += quantity_to_add
            self.update_cart()

    def update_cart(self):

        self.sync_cart_pricing()
        self.cart_list.clear()
        total = 0

        if not self.cart:
            empty_item = QListWidgetItem(T("Your cart is empty"))
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cart_list.addItem(empty_item)
            self.total_label.setText(TF("Total: {amount} Ft", amount=ltr_text("0")))
            return

        for item in self.cart.values():
            subtotal = item["price"] * item["quantity"]
            total += subtotal

            line_text = f"{item['name']} x{item['quantity']} = {subtotal:g} Ft"
            self.cart_list.addItem(line_text)

        self.total_label.setText(TF("Total: {amount} Ft", amount=ltr_text(f"{total:g}")))



    def checkout(self):
        item_count = len(self.cart)
        unit_count = sum(int(item.get("quantity", 0)) for item in self.cart.values())
        performance = CheckoutPerformance(item_count, unit_count)
        outcome = "failed"
        error_category = None

        try:
            if not self.cart:
                QMessageBox.information(
                    self,
                    T("Cart Empty"),
                    T("Please add medicines to the cart first.")
                )
                error_category = "EmptyCart"
                return

            with performance.measure("cart_availability"):
                self.sync_cart_pricing()
                self.update_cart()
                cart_items = list(self.cart.values())

            with performance.measure("prescription_check"):
                identity_required = cart_requires_prescription(cart_items)

            identity_dialog = CustomerIdentityDialog(
                details_required=identity_required, parent=self
            )
            with performance.measure("customer_details", "interaction"):
                if run_centered_modal(identity_dialog, self) != QDialog.DialogCode.Accepted:
                    outcome = "cancelled"
                    return

            identity = identity_dialog.get_payload()
            customer_name = identity["customer_name"]
            customer_ssn = identity["customer_ssn"]

            if identity_required and (not customer_name or not customer_ssn):
                QMessageBox.warning(
                    self,
                    T("Customer Details Required"),
                    T("Customer SSN and name are required because the cart contains prescription products.")
                )
                error_category = "MissingCustomerDetails"
                return

            if not identity_required and identity["declined"]:
                customer_name = None
                customer_ssn = None
            elif customer_name or customer_ssn:
                if not customer_name or not customer_ssn:
                    QMessageBox.warning(
                        self,
                        T("Incomplete Details"),
                        T("Please provide both customer name and SSN, or decline.")
                    )
                    error_category = "IncompleteCustomerDetails"
                    return

            if customer_ssn and not is_valid_customer_ssn(customer_ssn):
                QMessageBox.warning(
                    self,
                    T("Invalid SSN"),
                    T("Customer SSN must contain 9 digits.")
                )
                error_category = "InvalidCustomerSSN"
                return

            try:
                with performance.measure("fefo_allocation"):
                    plan, total_amount = preview_sale_allocations(cart_items)
            except ValueError as error:
                error_category = type(error).__name__
                QMessageBox.warning(self, T("Insufficient Stock"), T(str(error)))
                return

            dialog = BatchPickDialog(plan, total_amount, self)
            with performance.measure("batch_confirmation", "interaction"):
                if run_centered_modal(dialog, self) != QDialog.DialogCode.Accepted:
                    outcome = "cancelled"
                    return

            payment_dialog = PaymentMethodDialog(total_amount, self)
            with performance.measure("payment_selection", "interaction"):
                if run_centered_modal(payment_dialog, self) != QDialog.DialogCode.Accepted:
                    outcome = "cancelled"
                    return

            payment_method = payment_dialog.get_payment_method()

            try:
                with performance.measure(
                    "transaction",
                    metadata={"includes_inventory_deduction": True},
                ):
                    saved_plan, saved_total = create_sale(
                        cart_items,
                        payment_method,
                        cashier_id=self.current_user.get("id", 1),
                        acting_username=self.current_user.get("username"),
                        acting_role=self.current_user.get("role"),
                        customer_ssn=customer_ssn or None,
                        customer_name=customer_name or None,
                        performance_callback=performance.record_phase,
                    )
                with performance.measure("receipt_summary"):
                    receipt_summary = build_receipt_summary(
                        saved_plan, saved_total, payment_method
                    )
            except ValueError as error:
                error_category = type(error).__name__
                QMessageBox.warning(self, T("Checkout Failed"), T(str(error)))
                return
            except Exception as error:
                error_category = type(error).__name__
                QMessageBox.critical(
                    self,
                    T("Checkout Failed"),
                    TF("An unexpected error occurred while saving the sale:\n{error}", error=error)
                )
                return

            with performance.measure("post_checkout_refresh"):
                self.cart.clear()
                self.update_cart()
                self.refresh_products()

            outcome = "success"
            performance.finish(outcome)
            QMessageBox.information(
                self,
                T("Checkout Complete"),
                TF(
                    "Sale saved and FEFO picking instructions confirmed. Total: {total}",
                    total=format_money(receipt_summary["total"]),
                )
            )
        finally:
            performance.finish(outcome, error_category)




    def empty_cart(self):
        if not self.cart:
            QMessageBox.information(
                self,
                T("Cart Empty"),
                T("The cart is already empty.")
            )
            return

        confirm = QMessageBox.question(
            self,
            T("Empty Cart"),
            T("Are you sure you want to remove all items from the cart?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.cart.clear()
        self.update_cart()


