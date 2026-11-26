from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QDoubleSpinBox,
    QFormLayout, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from database.db import (
    delete_supplier,
    change_purchase_order_status,
    create_order_from_recommendations,
    get_purchase_order,
    get_purchase_orders,
    get_purchase_history,
    get_purchase_products,
    get_purchase_receipt,
    get_purchase_receipt_items,
    get_suppliers,
    get_reorder_suggestions,
    receive_purchase,
    save_purchase_order,
    save_supplier,
)
from i18n import T, TF, force_ltr, format_date, format_money, format_number
from ui_theme import (
    BLUE, BORDER, CANVAS, DANGER, SURFACE, SURFACE_SOFT, TEXT, TEXT_MUTED,
    danger_button_style, input_style, page_subtitle_style, page_title_style,
    primary_button_style, soft_button_style,
)


def details_dialog_style():
    return f"""
        QDialog {{ background: {CANVAS}; color: {TEXT}; }}
        QLabel {{ color: {TEXT}; }}
        QTableWidget {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; }}
        QTableWidget::item {{ padding: 0 8px; border-bottom: 1px solid {BORDER}; }}
        QHeaderView::section {{ background: {SURFACE_SOFT}; color: {TEXT_MUTED};
            padding: 8px; border: 0; border-bottom: 1px solid {BORDER}; font-weight: 700; }}
        QTextEdit {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
            border-radius: 6px; padding: 7px; }}
    """


class SupplierDialog(QDialog):
    def __init__(self, supplier=None, parent=None):
        super().__init__(parent)
        self.supplier = supplier or {}
        self.setWindowTitle(T("Edit Supplier" if supplier else "Add Supplier"))
        self.setModal(True)
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        form = QFormLayout()
        form.setSpacing(12)
        self.fields = {}
        for key, label in (
            ("name", "Supplier name"),
            ("contact_person", "Contact person"),
            ("phone", "Phone"),
            ("email", "Email"),
            ("address", "Address"),
        ):
            field = QLineEdit(str(self.supplier.get(key) or ""))
            field.setMinimumHeight(40)
            field.setStyleSheet(input_style())
            if key in ("phone", "email"):
                force_ltr(field)
            form.addRow(T(label), field)
            self.fields[key] = field
        self.lead_time = QSpinBox()
        self.lead_time.setRange(0, 365)
        self.lead_time.setValue(int(self.supplier.get("lead_time_days") or 7))
        self.lead_time.setSuffix(T(" days"))
        self.lead_time.setMinimumHeight(40)
        form.addRow(T("Lead time"), self.lead_time)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(T("Cancel"))
        save = QPushButton(T("Save"))
        cancel.setStyleSheet(soft_button_style())
        save.setStyleSheet(primary_button_style(BLUE, "#1d4ed8"))
        for button in (cancel, save):
            button.setMinimumHeight(38)
            button.setMinimumWidth(100)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def values(self):
        values = {key: field.text().strip() for key, field in self.fields.items()}
        values["lead_time_days"] = self.lead_time.value()
        return values


class PurchaseDetailsDialog(QDialog):
    def __init__(self, receipt, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Purchase details"))
        self.setModal(True)
        self.resize(780, 560)
        self.setStyleSheet(details_dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title = QLabel(T("Purchase details"))
        title.setStyleSheet(page_title_style())
        layout.addWidget(title)

        summary = QGridLayout()
        summary.setHorizontalSpacing(18)
        summary.setVerticalSpacing(8)
        details = (
            ("Reference number", receipt["reference_number"]),
            ("Supplier", receipt["supplier"]),
            ("Received date", format_date(receipt["received_date"])),
            ("Received by", receipt["received_by"]),
        )
        for index, (label, value) in enumerate(details):
            label_widget = QLabel(T(label))
            label_widget.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 600;")
            value_widget = QLabel(str(value or ""))
            value_widget.setStyleSheet(f"color: {TEXT}; font-weight: 700;")
            summary.addWidget(label_widget, index // 2 * 2, index % 2)
            summary.addWidget(value_widget, index // 2 * 2 + 1, index % 2)
        layout.addLayout(summary)

        item_title = QLabel(T("Received items"))
        item_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        layout.addWidget(item_title)

        table = QTableWidget(len(items), 6)
        table.setHorizontalHeaderLabels([
            T("Product"), T("Batch number"), T("Expiry"), T("Quantity"),
            T("Unit cost (Ft)"), T("Line total"),
        ])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for row_index, item in enumerate(items):
            values = (
                item["product"], item["batch_number"], format_date(item["expiry_date"]),
                format_number(item["quantity"], 0), format_money(item["unit_cost"]),
                format_money(item["total_cost"]),
            )
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        layout.addWidget(table, 1)

        notes_title = QLabel(T("Delivery notes"))
        notes_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        layout.addWidget(notes_title)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(receipt.get("notes") or T("No delivery notes provided."))
        notes.setFixedHeight(92)
        notes.setStyleSheet(input_style())
        layout.addWidget(notes)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(T("Close"))
        close.setStyleSheet(soft_button_style())
        close.setMinimumSize(100, 38)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)


class PurchaseOrderDetailsDialog(QDialog):
    def __init__(self, order, items, receipts, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Purchase Order Details"))
        self.setModal(True)
        self.resize(900, 650)
        self.setStyleSheet(details_dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        title = QLabel(order["order_number"])
        title.setStyleSheet(page_title_style())
        layout.addWidget(title)

        summary = QGridLayout()
        details = (
            ("Supplier", order["supplier"]),
            ("Status", T(order["status"].replace("_", " ").title())),
            ("Order date", format_date(order["order_date"])),
            ("Expected delivery", format_date(order["expected_date"])),
            ("Created by", order.get("created_by") or ""),
            ("Lead time", TF("{days} days", days=order.get("lead_time_days", 7))),
        )
        for index, (label, value) in enumerate(details):
            label_widget = QLabel(T(label))
            label_widget.setStyleSheet(f"color:{TEXT_MUTED};font-weight:600;")
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet(f"color:{TEXT};font-weight:700;")
            row, column = divmod(index, 3)
            summary.addWidget(label_widget, row * 2, column)
            summary.addWidget(value_widget, row * 2 + 1, column)
        layout.addLayout(summary)

        table = QTableWidget(len(items), 6)
        table.setHorizontalHeaderLabels([T(value) for value in (
            "Product", "Ordered", "Received", "Outstanding", "Unit cost (Ft)",
            "Line total",
        )])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        for row_index, item in enumerate(items):
            values = (
                item["product"], format_number(item["ordered_quantity"], 0),
                format_number(item["received_quantity"], 0),
                format_number(item["outstanding_quantity"], 0),
                format_money(item["unit_cost"]), format_money(item["total_cost"]),
            )
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        layout.addWidget(table, 1)

        lower = QGridLayout()
        lower.addWidget(QLabel(T("Order notes")), 0, 0)
        lower.addWidget(QLabel(T("Related receipts")), 0, 1)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(
            T(order.get("notes")) if order.get("notes") else T("No order notes provided.")
        )
        notes.setFixedHeight(90)
        notes.setStyleSheet(input_style())
        receipt_text = QTextEdit()
        receipt_text.setReadOnly(True)
        receipt_text.setFixedHeight(90)
        receipt_text.setStyleSheet(input_style())
        receipt_text.setPlainText("\n".join(
            TF("{reference} on {date}", reference=row["reference_number"],
               date=format_date(row["received_date"]))
            for row in receipts
        ) or T("No receipts recorded."))
        lower.addWidget(notes, 1, 0)
        lower.addWidget(receipt_text, 1, 1)
        layout.addLayout(lower)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(T("Close"))
        close.setMinimumSize(100, 38)
        close.setStyleSheet(soft_button_style())
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)


class PurchaseOrderDialog(QDialog):
    def __init__(self, suppliers, products, order=None, items=None, parent=None):
        super().__init__(parent)
        self.suppliers = suppliers
        self.products = products
        self.order = order or {}
        self.existing_items = items or []
        self.setWindowTitle(T("Edit Purchase Order" if order else "New Purchase Order"))
        self.resize(900, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        form = QGridLayout()
        self.supplier = QComboBox()
        self.supplier.addItem(T("Select supplier"), None)
        for supplier in suppliers:
            self.supplier.addItem(supplier["name"], supplier["id"])
        self.order_date = QDateEdit(QDate.currentDate())
        self.expected_date = QDateEdit(QDate.currentDate().addDays(7))
        for field in (self.order_date, self.expected_date):
            field.setCalendarPopup(True)
            field.setDisplayFormat("yyyy-MM-dd")
        self.status = QComboBox()
        self.status.addItem(T("Draft"), "draft")
        self.status.addItem(T("Pending"), "pending")
        for column, (label, field) in enumerate((
            ("Supplier", self.supplier), ("Order date", self.order_date),
            ("Expected delivery", self.expected_date), ("Status", self.status),
        )):
            form.addWidget(QLabel(T(label)), 0, column)
            form.addWidget(field, 1, column)
        layout.addLayout(form)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(T("Order items")))
        toolbar.addStretch()
        add = QPushButton(T("+ Add item"))
        add.setStyleSheet(soft_button_style())
        add.clicked.connect(self.add_row)
        toolbar.addWidget(add)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            T("Product"), T("Quantity"), T("Unit cost (Ft)"),
            T("Line total"), T("Actions"),
        ])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText(T("Optional order notes"))
        self.notes.setFixedHeight(68)
        layout.addWidget(self.notes)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(T("Cancel"))
        save = QPushButton(T("Save Purchase Order"))
        cancel.setStyleSheet(soft_button_style())
        save.setStyleSheet(primary_button_style())
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        if order:
            self.supplier.setCurrentIndex(self.supplier.findData(order["supplier_id"]))
            self.order_date.setDate(QDate.fromString(order["order_date"], "yyyy-MM-dd"))
            self.expected_date.setDate(QDate.fromString(order["expected_date"], "yyyy-MM-dd"))
            self.status.setCurrentIndex(self.status.findData(order["status"]))
            self.notes.setPlainText(order.get("notes") or "")
        for item in self.existing_items or [None]:
            self.add_row(item)

    def add_row(self, item=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        product = QComboBox()
        product.addItem(T("Select product"), None)
        for entry in self.products:
            product.addItem(entry["name"], entry["id"])
        quantity = QSpinBox()
        quantity.setRange(1, 1_000_000)
        cost = QDoubleSpinBox()
        cost.setRange(0.01, 999_999_999)
        cost.setDecimals(2)
        cost.setSuffix(T(" Ft"))
        total = QLabel(format_money(0))
        total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remove = QPushButton(T("Remove"))
        remove.setStyleSheet(danger_button_style())
        remove.clicked.connect(lambda _=False, button=remove: self.remove_row(button))
        refresh = lambda _=0: total.setText(format_money(quantity.value() * cost.value()))
        quantity.valueChanged.connect(refresh)
        cost.valueChanged.connect(refresh)
        if item:
            product.setCurrentIndex(product.findData(item["product_id"]))
            quantity.setValue(int(item["ordered_quantity"]))
            cost.setValue(float(item["unit_cost"]))
        refresh()
        for column, widget in enumerate((product, quantity, cost, total, remove)):
            self.table.setCellWidget(row, column, widget)

    def remove_row(self, button):
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 4) is button:
                self.table.removeRow(row)
                break

    def values(self):
        return {
            "supplier_id": self.supplier.currentData(),
            "order_date": self.order_date.date().toString("yyyy-MM-dd"),
            "expected_date": self.expected_date.date().toString("yyyy-MM-dd"),
            "status": self.status.currentData(),
            "notes": self.notes.toPlainText(),
            "items": [{
                "product_id": self.table.cellWidget(row, 0).currentData(),
                "quantity": self.table.cellWidget(row, 1).value(),
                "unit_cost": f"{self.table.cellWidget(row, 2).value():.2f}",
            } for row in range(self.table.rowCount())],
        }


class ReceiveOrderDialog(QDialog):
    def __init__(self, order, items, current_user, parent=None):
        super().__init__(parent)
        self.order, self.items, self.current_user = order, items, current_user
        self.setWindowTitle(T("Receive Purchase Order"))
        self.resize(980, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        title = QLabel(TF("Receive {number}", number=order["order_number"]))
        title.setStyleSheet(page_title_style())
        layout.addWidget(title)
        form = QGridLayout()
        self.reference = QLineEdit()
        self.reference.setPlaceholderText(T("Supplier invoice or delivery note"))
        self.received_date = QDateEdit(QDate.currentDate())
        self.received_date.setCalendarPopup(True)
        self.received_date.setMaximumDate(QDate.currentDate())
        self.received_date.setDisplayFormat("yyyy-MM-dd")
        form.addWidget(QLabel(T("Reference number")), 0, 0)
        form.addWidget(QLabel(T("Received date")), 0, 1)
        form.addWidget(self.reference, 1, 0)
        form.addWidget(self.received_date, 1, 1)
        layout.addLayout(form)
        self.table = QTableWidget(len(items), 7)
        self.table.setHorizontalHeaderLabels([
            T("Product"), T("Outstanding"), T("Receive now"), T("Batch"),
            T("Expiry"), T("Unit cost (Ft)"), T("Line total"),
        ])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item["product"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(item["outstanding_quantity"])))
            quantity = QSpinBox()
            quantity.setRange(0, int(item["outstanding_quantity"]))
            batch = QLineEdit()
            batch.setPlaceholderText(T("Batch number"))
            expiry = QDateEdit(QDate.currentDate().addYears(1))
            expiry.setCalendarPopup(True)
            expiry.setMinimumDate(QDate.currentDate().addDays(1))
            expiry.setDisplayFormat("yyyy-MM-dd")
            cost = QDoubleSpinBox()
            cost.setRange(0.01, 999_999_999)
            cost.setDecimals(2)
            cost.setValue(float(item["unit_cost"]))
            total = QLabel(format_money(0))
            total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            refresh = lambda _=0, q=quantity, c=cost, label=total: label.setText(
                format_money(q.value() * c.value())
            )
            quantity.valueChanged.connect(refresh)
            cost.valueChanged.connect(refresh)
            for column, widget in enumerate((quantity, batch, expiry, cost, total), start=2):
                self.table.setCellWidget(row, column, widget)
        layout.addWidget(self.table, 1)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText(T("Optional delivery notes"))
        self.notes.setFixedHeight(60)
        layout.addWidget(self.notes)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(T("Cancel"))
        receive = QPushButton(T("Receive selected quantities"))
        cancel.setStyleSheet(soft_button_style())
        receive.setStyleSheet(primary_button_style())
        cancel.clicked.connect(self.reject)
        receive.clicked.connect(self.submit)
        buttons.addWidget(cancel)
        buttons.addWidget(receive)
        layout.addLayout(buttons)

    def submit(self):
        lines = []
        for row, item in enumerate(self.items):
            quantity = self.table.cellWidget(row, 2).value()
            if quantity <= 0:
                continue
            lines.append({
                "purchase_order_item_id": item["id"], "product_id": item["product_id"],
                "quantity": quantity, "batch_number": self.table.cellWidget(row, 3).text(),
                "expiry_date": self.table.cellWidget(row, 4).date().toString("yyyy-MM-dd"),
                "unit_cost": f"{self.table.cellWidget(row, 5).value():.2f}",
            })
        try:
            receipt_id = receive_purchase(
                self.order["supplier_id"], self.reference.text(),
                self.received_date.date().toString("yyyy-MM-dd"), lines,
                self.notes.toPlainText(), self.current_user.get("username"),
                self.current_user.get("role"), self.order["id"],
            )
        except Exception as error:
            QMessageBox.warning(self, T("Purchase Orders"), T(str(error)))
            return
        QMessageBox.information(
            self, T("Purchase Orders"),
            TF("Purchase receipt P-{receipt:05d} was saved and stock was updated.", receipt=receipt_id),
        )
        self.accept()


class PurchasingPage(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user or {}
        self.products = []
        self.suppliers = []
        self.setObjectName("purchasingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(16)

        title = QLabel(T("Purchasing"))
        title.setMinimumHeight(42)
        title.setStyleSheet(page_title_style())
        subtitle = QLabel(T("Receive supplier deliveries and keep their complete history"))
        subtitle.setStyleSheet(page_subtitle_style())
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.build_orders_tab(), T("Purchase Orders"))
        self.tabs.addTab(self.build_reorder_tab(), T("Reorder Suggestions"))
        self.tabs.addTab(self.build_receive_tab(), T("Receive Stock"))
        self.tabs.addTab(self.build_history_tab(), T("Purchase History"))
        self.tabs.addTab(self.build_suppliers_tab(), T("Suppliers"))
        layout.addWidget(self.tabs, 1)

        self.setStyleSheet(f"""
            QWidget#purchasingPage {{ background: {CANVAS}; color: {TEXT}; }}
            QWidget#purchasingPage QLabel {{ color: {TEXT}; }}
            QTabWidget::pane {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; }}
            QTabBar::tab {{ background: {SURFACE_SOFT}; color: {TEXT_MUTED}; padding: 10px 18px;
                           border: 1px solid {BORDER}; border-bottom: none; min-width: 130px; }}
            QTabBar::tab:selected {{ background: {SURFACE}; color: {BLUE}; font-weight: 700; }}
            QTableWidget {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; selection-background-color: #dbeafe; }}
            QTableWidget::item {{ padding: 0 8px; border-bottom: 1px solid {BORDER}; }}
            QHeaderView::section {{ background: {SURFACE_SOFT}; color: {TEXT_MUTED}; padding: 8px;
                                   border: 0; border-bottom: 1px solid {BORDER}; font-weight: 700; }}
            QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{ background: white; color: {TEXT};
                border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px 10px; }}
            QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{ border: 1px solid {BLUE}; }}
        """)
        self.refresh()

    def build_orders_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        self.order_search = QLineEdit()
        self.order_search.setPlaceholderText(T("Search by order number or supplier..."))
        self.order_search.setStyleSheet(input_style())
        self.order_search.setMinimumHeight(40)
        self.order_status_filter = QComboBox()
        for label, value in (("All statuses", "all"), ("Draft", "draft"),
                             ("Pending", "pending"), ("Ordered", "ordered"),
                             ("Partially received", "partially_received"),
                             ("Fully received", "fully_received"), ("Cancelled", "cancelled")):
            self.order_status_filter.addItem(T(label), value)
        new_order = QPushButton(T("+ New Purchase Order"))
        new_order.setStyleSheet(primary_button_style())
        new_order.setMinimumHeight(40)
        new_order.clicked.connect(self.new_purchase_order)
        self.order_search.textChanged.connect(self.refresh_orders)
        self.order_status_filter.currentIndexChanged.connect(self.refresh_orders)
        toolbar.addWidget(self.order_search, 1)
        toolbar.addWidget(self.order_status_filter)
        toolbar.addWidget(new_order)
        layout.addLayout(toolbar)
        self.orders_table = self.make_table([
            "Order number", "Supplier", "Order date", "Expected", "Status",
            "Ordered", "Received", "Outstanding", "Total cost", "Actions",
        ])
        self.orders_table.horizontalHeader().setSectionResizeMode(
            9, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.orders_table, 1)
        return page

    def build_reorder_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        controls = QHBoxLayout()
        self.reorder_supplier = QComboBox()
        self.reorder_supplier.setMinimumWidth(190)
        self.reorder_period = QComboBox()
        for days in (7, 30, 60, 90):
            self.reorder_period.addItem(TF("{days} days", days=days), days)
        self.reorder_period.setCurrentIndex(1)
        self.safety_days = QSpinBox()
        self.safety_days.setRange(0, 365)
        self.safety_days.setValue(7)
        self.reorder_supplier.currentIndexChanged.connect(self.refresh_reorders)
        self.reorder_period.currentIndexChanged.connect(self.refresh_reorders)
        self.safety_days.valueChanged.connect(self.refresh_reorders)
        recalculate = QPushButton(T("Recalculate"))
        recalculate.setStyleSheet(soft_button_style())
        recalculate.clicked.connect(self.refresh_reorders)
        convert = QPushButton(T("Create Draft Order"))
        convert.setStyleSheet(primary_button_style())
        convert.clicked.connect(self.convert_recommendations)
        for label, field in (("Supplier", self.reorder_supplier),
                             ("Sales period", self.reorder_period),
                             ("Safety stock days", self.safety_days)):
            controls.addWidget(QLabel(T(label)))
            controls.addWidget(field)
        controls.addStretch()
        controls.addWidget(recalculate)
        controls.addWidget(convert)
        layout.addLayout(controls)
        self.reorder_table = QTableWidget(0, 10)
        self.reorder_table.setHorizontalHeaderLabels([T(value) for value in (
            "Select", "Product", "Movement", "Daily sales", "Usable stock",
            "Outstanding PO", "Reorder point", "Suggested", "Order quantity", "Calculation",
        )])
        self.reorder_table.verticalHeader().hide()
        self.reorder_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reorder_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.reorder_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.reorder_table, 1)
        return page

    def build_receive_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QGridLayout()
        header.setHorizontalSpacing(12)
        header.setVerticalSpacing(6)
        self.supplier_combo = QComboBox()
        self.reference_input = QLineEdit()
        self.received_date = QDateEdit(QDate.currentDate())
        self.received_date.setCalendarPopup(True)
        self.received_date.setMaximumDate(QDate.currentDate())
        self.received_date.setDisplayFormat("yyyy-MM-dd")
        force_ltr(self.reference_input)
        for field in (self.supplier_combo, self.reference_input):
            field.setMinimumHeight(40)
            field.setStyleSheet(input_style())
        self.supplier_combo.setMinimumWidth(200)
        self.reference_input.setPlaceholderText(T("Supplier invoice or delivery note"))
        self.reference_input.setMinimumWidth(190)
        self.received_date.setMinimumHeight(40)

        for column, (label, field) in enumerate((
            ("Supplier", self.supplier_combo),
            ("Reference number", self.reference_input),
            ("Received date", self.received_date),
        )):
            header.addWidget(QLabel(T(label)), 0, column)
            header.addWidget(field, 1, column)
            header.setColumnStretch(column, 2 if column < 2 else 1)
        layout.addLayout(header)

        item_toolbar = QHBoxLayout()
        item_title = QLabel(T("Received items"))
        item_title.setStyleSheet("font-size:15px;font-weight:700;color:#111827")
        add_line = QPushButton(T("+ Add item"))
        add_line.setStyleSheet(soft_button_style())
        add_line.setMinimumHeight(36)
        add_line.clicked.connect(self.add_item_row)
        item_toolbar.addWidget(item_title)
        item_toolbar.addStretch()
        item_toolbar.addWidget(add_line)
        layout.addLayout(item_toolbar)

        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels([
            T("Product"), T("Batch"), T("Expiry"), T("Quantity"),
            T("Unit cost (Ft)"), T("Line total"), T("Actions"),
        ])
        self.items_table.verticalHeader().hide()
        self.items_table.verticalHeader().setDefaultSectionSize(48)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.items_table.setMinimumHeight(230)
        layout.addWidget(self.items_table, 1)

        notes_row = QHBoxLayout()
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText(T("Optional delivery notes"))
        self.notes_input.setFixedHeight(66)
        submit = QPushButton(T("Receive delivery"))
        submit.setStyleSheet(primary_button_style())
        submit.setMinimumSize(170, 44)
        submit.clicked.connect(self.submit_receipt)
        notes_row.addWidget(QLabel(T("Notes")))
        notes_row.addWidget(self.notes_input, 1)
        notes_row.addWidget(submit)
        layout.addLayout(notes_row)
        return page

    def build_history_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText(T("Search by supplier or reference..."))
        self.history_search.setMinimumHeight(40)
        self.history_search.setStyleSheet(input_style())
        self.history_search.textChanged.connect(self.refresh_history)
        layout.addWidget(self.history_search)
        self.history_table = self.make_table([
            "Reference", "Supplier", "Received date", "Items", "Quantity",
            "Total cost", "Received by", "Actions",
        ])
        layout.addWidget(self.history_table, 1)
        return page

    def build_suppliers_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        self.supplier_search = QLineEdit()
        self.supplier_search.setPlaceholderText(T("Search suppliers..."))
        self.supplier_search.setMinimumHeight(40)
        self.supplier_search.setStyleSheet(input_style())
        self.supplier_search.textChanged.connect(self.refresh_suppliers)
        add = QPushButton(T("+ Add Supplier"))
        add.setMinimumHeight(40)
        add.setStyleSheet(primary_button_style())
        add.clicked.connect(self.add_supplier)
        toolbar.addWidget(self.supplier_search, 1)
        toolbar.addWidget(add)
        layout.addLayout(toolbar)
        self.supplier_table = self.make_table([
            "Supplier", "Contact person", "Phone", "Email", "Address", "Lead time", "Actions",
        ])
        layout.addWidget(self.supplier_table, 1)
        return page

    def make_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels([T(header) for header in headers])
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(44)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setShowGrid(False)
        return table

    def refresh(self):
        self.products = get_purchase_products()
        self.refresh_suppliers()
        self.refresh_orders()
        self.refresh_reorders()
        self.refresh_history()
        if self.items_table.rowCount() == 0:
            self.add_item_row()

    def refresh_supplier_combo(self):
        selected = self.supplier_combo.currentData()
        self.supplier_combo.clear()
        self.supplier_combo.addItem(T("Select supplier"), None)
        for supplier in self.suppliers:
            self.supplier_combo.addItem(supplier["name"], supplier["id"])
        index = self.supplier_combo.findData(selected)
        if index >= 0:
            self.supplier_combo.setCurrentIndex(index)
        if hasattr(self, "reorder_supplier"):
            selected = self.reorder_supplier.currentData()
            self.reorder_supplier.clear()
            self.reorder_supplier.addItem(T("Select supplier"), None)
            for supplier in self.suppliers:
                self.reorder_supplier.addItem(supplier["name"], supplier["id"])
            index = self.reorder_supplier.findData(selected)
            if index >= 0:
                self.reorder_supplier.setCurrentIndex(index)

    def new_purchase_order(self):
        self.open_purchase_order_dialog()

    def open_purchase_order_dialog(self, purchase_order_id=None):
        order, items = None, []
        if purchase_order_id is not None:
            order, items, _ = get_purchase_order(purchase_order_id)
        dialog = PurchaseOrderDialog(self.suppliers, self.products, order, items, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            order_id, number = save_purchase_order(
                **dialog.values(), purchase_order_id=purchase_order_id,
                acting_username=self.current_user.get("username"),
                acting_role=self.current_user.get("role"),
            )
        except Exception as error:
            QMessageBox.warning(self, T("Purchase Orders"), T(str(error)))
            return
        QMessageBox.information(
            self, T("Purchase Orders"),
            TF("Purchase order {number} was saved.", number=number),
        )
        self.refresh_orders()
        self.refresh_reorders()

    def refresh_orders(self, *_):
        if not hasattr(self, "orders_table"):
            return
        rows = get_purchase_orders(
            self.order_search.text(), self.order_status_filter.currentData()
        )
        self.orders_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row["order_number"], row["supplier"], format_date(row["order_date"]),
                format_date(row["expected_date"]), T(row["status"].replace("_", " ").title()),
                format_number(row["ordered_quantity"], 0),
                format_number(row["received_quantity"], 0),
                format_number(row["outstanding_quantity"], 0), format_money(row["total_cost"]),
            )
            for column, value in enumerate(values):
                self.orders_table.setItem(row_index, column, QTableWidgetItem(str(value)))
            actions = QWidget()
            actions.setMinimumWidth(330)
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(1, 1, 1, 1)
            view = QPushButton(T("View"))
            view.setMinimumWidth(62)
            view.setStyleSheet(soft_button_style())
            view.clicked.connect(lambda _=False, item=row: self.view_order(item["id"]))
            action_layout.addWidget(view)
            if row["status"] in ("draft", "pending"):
                edit = QPushButton(T("Edit"))
                edit.setMinimumWidth(62)
                edit.setStyleSheet(soft_button_style())
                edit.clicked.connect(lambda _=False, item=row: self.open_purchase_order_dialog(item["id"]))
                action_layout.addWidget(edit)
            if row["status"] == "draft":
                action_layout.addWidget(self.order_action_button(row, T("Submit"), "pending"))
            elif row["status"] == "pending":
                action_layout.addWidget(self.order_action_button(row, T("Mark Ordered"), "ordered"))
            elif row["status"] in ("ordered", "partially_received"):
                receive = QPushButton(T("Receive"))
                receive.setMinimumWidth(82)
                receive.setStyleSheet(primary_button_style())
                receive.clicked.connect(lambda _=False, item=row: self.receive_order(item["id"]))
                action_layout.addWidget(receive)
            if row["status"] in ("draft", "pending", "ordered"):
                action_layout.addWidget(self.order_action_button(row, T("Cancel"), "cancelled", True))
            self.orders_table.setCellWidget(row_index, 9, actions)
        self.orders_table.resizeRowsToContents()

    def order_action_button(self, order, label, status, danger=False):
        button = QPushButton(label)
        button.setMinimumWidth(72)
        button.setStyleSheet(danger_button_style() if danger else soft_button_style())
        button.clicked.connect(
            lambda _=False, item=order, value=status: self.change_order_status(item, value)
        )
        return button

    def change_order_status(self, order, status):
        if status == "cancelled":
            answer = QMessageBox.question(
                self, T("Cancel Purchase Order"),
                TF("Cancel purchase order {number}?", number=order["order_number"]),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            change_purchase_order_status(
                order["id"], status, self.current_user.get("username"),
                self.current_user.get("role"),
            )
        except Exception as error:
            QMessageBox.warning(self, T("Purchase Orders"), T(str(error)))
            return
        self.refresh_orders()
        self.refresh_reorders()

    def view_order(self, purchase_order_id):
        order, items, receipts = get_purchase_order(purchase_order_id)
        if not order:
            QMessageBox.warning(self, T("Purchase Orders"), T("Purchase order was not found."))
            return
        PurchaseOrderDetailsDialog(order, items, receipts, self).exec()

    def receive_order(self, purchase_order_id):
        order, items, _ = get_purchase_order(purchase_order_id)
        outstanding = [item for item in items if int(item["outstanding_quantity"]) > 0]
        if not order or not outstanding:
            QMessageBox.warning(self, T("Purchase Orders"), T("This order has no outstanding items."))
            return
        if ReceiveOrderDialog(order, outstanding, self.current_user, self).exec():
            self.refresh_orders()
            self.refresh_history()
            self.refresh_reorders()

    def refresh_reorders(self, *_):
        if not hasattr(self, "reorder_table"):
            return
        try:
            rows = get_reorder_suggestions(
                self.reorder_period.currentData(), self.safety_days.value(),
                self.reorder_supplier.currentData(),
            )
        except Exception as error:
            QMessageBox.warning(self, T("Reorder Suggestions"), T(str(error)))
            return
        self.reorder_rows = rows
        self.reorder_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            selected = QCheckBox()
            selected.setChecked(row["suggested_quantity"] > 0)
            selected.setProperty("product_id", row["product_id"])
            self.reorder_table.setCellWidget(row_index, 0, selected)
            values = (
                row["product"], T(row["movement"]), format_number(row["average_daily_sales"], 2),
                format_number(row["usable_stock"], 0), format_number(row["outstanding_order"], 0),
                format_number(row["reorder_point"], 0), format_number(row["suggested_quantity"], 0),
            )
            for column, value in enumerate(values, start=1):
                self.reorder_table.setItem(row_index, column, QTableWidgetItem(str(value)))
            quantity = QSpinBox()
            quantity.setRange(0, 1_000_000)
            quantity.setValue(int(row["suggested_quantity"]))
            self.reorder_table.setCellWidget(row_index, 8, quantity)
            explanation = TF(
                "{sold} sold / {period} days = {daily} per day; lead time {lead} days + safety {safety} days; reorder point {point}; target {target}; usable {usable}; outstanding {outstanding}; suggested {suggested}.",
                sold=row["units_sold"], period=row["period_days"],
                daily=format_number(row["average_daily_sales"], 2),
                lead=row["lead_time_days"], safety=row["safety_days"],
                point=row["reorder_point"], target=row["target_stock"],
                usable=row["usable_stock"], outstanding=row["outstanding_order"],
                suggested=row["suggested_quantity"],
            )
            self.reorder_table.setItem(row_index, 9, QTableWidgetItem(explanation))

    def convert_recommendations(self):
        supplier_id = self.reorder_supplier.currentData()
        selected = []
        for row_index, row in enumerate(getattr(self, "reorder_rows", [])):
            if self.reorder_table.cellWidget(row_index, 0).isChecked():
                selected.append({
                    "product_id": row["product_id"],
                    "quantity": self.reorder_table.cellWidget(row_index, 8).value(),
                    "unit_cost": row["unit_cost"],
                })
        supplier = next((item for item in self.suppliers if item["id"] == supplier_id), None)
        lead_days = int(supplier.get("lead_time_days") or 7) if supplier else 7
        try:
            order_id, number = create_order_from_recommendations(
                supplier_id, selected, QDate.currentDate().toString("yyyy-MM-dd"),
                QDate.currentDate().addDays(lead_days).toString("yyyy-MM-dd"),
                self.current_user.get("username"), self.current_user.get("role"),
            )
        except Exception as error:
            QMessageBox.warning(self, T("Reorder Suggestions"), T(str(error)))
            return
        QMessageBox.information(
            self, T("Reorder Suggestions"),
            TF("Draft purchase order {number} was created.", number=number),
        )
        self.refresh_orders()
        self.refresh_reorders()

    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        product = QComboBox()
        product.setStyleSheet(input_style())
        product.addItem(T("Select product"), None)
        for item in self.products:
            product.addItem(item["name"], item["id"])
        batch = QLineEdit()
        batch.setPlaceholderText(T("Batch number"))
        batch.setStyleSheet(input_style())
        force_ltr(batch)
        expiry = QDateEdit(QDate.currentDate().addYears(1))
        expiry.setCalendarPopup(True)
        expiry.setMinimumDate(QDate.currentDate().addDays(1))
        expiry.setDisplayFormat("yyyy-MM-dd")
        quantity = QSpinBox()
        quantity.setRange(1, 1_000_000)
        cost = QDoubleSpinBox()
        cost.setRange(0.01, 999_999_999)
        cost.setDecimals(2)
        cost.setSuffix(" Ft")
        total = QLabel(format_money(0))
        total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for widget in (expiry, quantity, cost, total):
            force_ltr(widget, right=True)
        remove = QPushButton(T("Remove"))
        remove.setStyleSheet(danger_button_style())
        remove.clicked.connect(lambda _=False, button=remove: self.remove_item_row(button))
        refresh_total = lambda _=0: total.setText(
            format_money(quantity.value() * cost.value())
        )
        quantity.valueChanged.connect(refresh_total)
        cost.valueChanged.connect(refresh_total)
        refresh_total()
        for column, widget in enumerate((product, batch, expiry, quantity, cost, total, remove)):
            self.items_table.setCellWidget(row, column, widget)

    def remove_item_row(self, button):
        for row in range(self.items_table.rowCount()):
            if self.items_table.cellWidget(row, 6) is button:
                self.items_table.removeRow(row)
                break
        if self.items_table.rowCount() == 0:
            self.add_item_row()

    def submit_receipt(self):
        items = []
        for row in range(self.items_table.rowCount()):
            product = self.items_table.cellWidget(row, 0)
            batch = self.items_table.cellWidget(row, 1)
            expiry = self.items_table.cellWidget(row, 2)
            quantity = self.items_table.cellWidget(row, 3)
            cost = self.items_table.cellWidget(row, 4)
            items.append({
                "product_id": product.currentData(),
                "batch_number": batch.text().strip(),
                "expiry_date": expiry.date().toString("yyyy-MM-dd"),
                "quantity": quantity.value(),
                "unit_cost": f"{cost.value():.2f}",
            })
        try:
            receipt_id = receive_purchase(
                self.supplier_combo.currentData(),
                self.reference_input.text(),
                self.received_date.date().toString("yyyy-MM-dd"),
                items,
                self.notes_input.toPlainText(),
                self.current_user.get("username"),
                self.current_user.get("role"),
            )
        except Exception as error:
            QMessageBox.warning(self, T("Purchasing"), T(str(error)))
            return
        QMessageBox.information(
            self, T("Purchasing"),
            TF("Purchase receipt P-{receipt:05d} was saved and stock was updated.", receipt=receipt_id),
        )
        self.reference_input.clear()
        self.notes_input.clear()
        self.items_table.setRowCount(0)
        self.add_item_row()
        self.refresh_history()
        self.refresh_reorders()

    def refresh_history(self, *_):
        if not hasattr(self, "history_table"):
            return
        rows = get_purchase_history(self.history_search.text())
        self.history_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row["reference_number"], row["supplier"], format_date(row["received_date"]),
                format_number(row["line_count"], 0), format_number(row["quantity"], 0),
                format_money(row["total_cost"]), row["received_by"],
            )
            for column, value in enumerate(values):
                self.history_table.setItem(row_index, column, QTableWidgetItem(str(value)))
            view = QPushButton(T("View"))
            view.setStyleSheet(soft_button_style())
            view.clicked.connect(lambda _=False, receipt=row["id"]: self.view_receipt(receipt))
            self.history_table.setCellWidget(row_index, 7, view)

    def view_receipt(self, receipt_id):
        receipt = get_purchase_receipt(receipt_id)
        rows = get_purchase_receipt_items(receipt_id)
        if receipt is None:
            QMessageBox.warning(self, T("Purchase details"), T("Purchase receipt was not found."))
            return
        PurchaseDetailsDialog(receipt, rows, self).exec()

    def refresh_suppliers(self, *_):
        search = self.supplier_search.text() if hasattr(self, "supplier_search") else ""
        table_suppliers = get_suppliers(search)
        self.suppliers = get_suppliers("") if search else table_suppliers
        if hasattr(self, "supplier_combo"):
            self.refresh_supplier_combo()
        if not hasattr(self, "supplier_table"):
            return
        self.supplier_table.setRowCount(len(table_suppliers))
        for row_index, supplier in enumerate(table_suppliers):
            for column, key in enumerate(("name", "contact_person", "phone", "email", "address")):
                self.supplier_table.setItem(
                    row_index, column, QTableWidgetItem(str(supplier.get(key) or ""))
                )
            self.supplier_table.setItem(
                row_index, 5,
                QTableWidgetItem(TF("{days} days", days=supplier.get("lead_time_days", 7))),
            )
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 2, 2, 2)
            edit = QPushButton(T("Edit"))
            delete = QPushButton(T("Delete"))
            edit.setStyleSheet(soft_button_style())
            delete.setStyleSheet(danger_button_style())
            edit.clicked.connect(lambda _=False, item=supplier: self.edit_supplier(item))
            delete.clicked.connect(lambda _=False, item=supplier: self.remove_supplier(item))
            action_layout.addWidget(edit)
            action_layout.addWidget(delete)
            self.supplier_table.setCellWidget(row_index, 6, actions)

    def add_supplier(self):
        self.open_supplier_dialog()

    def edit_supplier(self, supplier):
        self.open_supplier_dialog(supplier)

    def open_supplier_dialog(self, supplier=None):
        dialog = SupplierDialog(supplier, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        success, message = save_supplier(
            **dialog.values(),
            supplier_id=supplier.get("id") if supplier else None,
            acting_username=self.current_user.get("username"),
            acting_role=self.current_user.get("role"),
        )
        if not success:
            QMessageBox.warning(self, T("Suppliers"), T(message))
            return
        self.refresh_suppliers()
        self.refresh_reorders()

    def remove_supplier(self, supplier):
        answer = QMessageBox.question(
            self, T("Delete Supplier"),
            TF("Delete supplier {name}?", name=supplier["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        success, message = delete_supplier(
            supplier["id"], self.current_user.get("username"), self.current_user.get("role")
        )
        if not success:
            QMessageBox.warning(self, T("Suppliers"), T(message))
            return
        self.refresh_suppliers()
        self.refresh_reorders()
