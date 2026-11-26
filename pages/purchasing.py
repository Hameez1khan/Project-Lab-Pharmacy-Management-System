from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QDoubleSpinBox,
    QFormLayout, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from database.db import (
    delete_supplier,
    get_purchase_history,
    get_purchase_products,
    get_purchase_receipt_items,
    get_suppliers,
    receive_purchase,
    save_supplier,
)
from i18n import T, TF, force_ltr, format_date, format_money, format_number
from ui_theme import (
    BLUE, BORDER, CANVAS, DANGER, SURFACE, SURFACE_SOFT, TEXT, TEXT_MUTED,
    danger_button_style, input_style, page_subtitle_style, page_title_style,
    primary_button_style, soft_button_style,
)


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
        return {key: field.text().strip() for key, field in self.fields.items()}


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
        title.setStyleSheet(page_title_style())
        subtitle = QLabel(T("Receive supplier deliveries and keep their complete history"))
        subtitle.setStyleSheet(page_subtitle_style())
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.build_receive_tab(), T("Receive Stock"))
        self.tabs.addTab(self.build_history_tab(), T("Purchase History"))
        self.tabs.addTab(self.build_suppliers_tab(), T("Suppliers"))
        layout.addWidget(self.tabs, 1)

        self.setStyleSheet(f"""
            QWidget#purchasingPage {{ background: {CANVAS}; }}
            QTabWidget::pane {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; }}
            QTabBar::tab {{ background: {SURFACE_SOFT}; color: {TEXT_MUTED}; padding: 10px 18px;
                           border: 1px solid {BORDER}; border-bottom: none; min-width: 130px; }}
            QTabBar::tab:selected {{ background: {SURFACE}; color: {BLUE}; font-weight: 700; }}
            QTableWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; selection-background-color: #dbeafe; }}
            QTableWidget::item {{ padding: 0 8px; border-bottom: 1px solid {BORDER}; }}
            QHeaderView::section {{ background: {SURFACE_SOFT}; color: {TEXT_MUTED}; padding: 8px;
                                   border: 0; border-bottom: 1px solid {BORDER}; font-weight: 700; }}
            QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{ background: white; color: {TEXT};
                border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px 10px; }}
            QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{ border: 1px solid {BLUE}; }}
        """)
        self.refresh()

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
            "Supplier", "Contact person", "Phone", "Email", "Address", "Actions",
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
        rows = get_purchase_receipt_items(receipt_id)
        lines = [
            f"{row['product']} | {row['batch_number']} | {row['quantity']} x "
            f"{format_money(row['unit_cost'])} = {format_money(row['total_cost'])}"
            for row in rows
        ]
        QMessageBox.information(
            self, T("Purchase details"), "\n".join(lines) or T("No received items found."),
        )

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
            self.supplier_table.setCellWidget(row_index, 5, actions)

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
