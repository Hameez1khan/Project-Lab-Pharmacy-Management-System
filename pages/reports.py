from PyQt6.QtCore import QDate, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QMessageBox, QPushButton, QStackedWidget,
    QApplication, QProgressDialog, QStyle, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from database.inventory_audit import operator
from database.reporting import report_data
from i18n import T, TF, format_money, format_number
from ui_theme import (
    BLUE, BORDER, CANVAS, PRIMARY, SURFACE, SURFACE_SOFT, TEXT, TEXT_MUTED,
    page_title_style, page_subtitle_style, primary_button_style, soft_button_style,
)


class FileActionThread(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, action, path, identity, parent=None):
        super().__init__(parent)
        self.action = action
        self.path = path
        self.identity = identity

    def run(self):
        token = operator.set(self.identity)
        try:
            self.succeeded.emit(self.action(self.path))
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            operator.reset(token)


class ReportsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.admin = current_user["role"].lower() == "admin"
        self.data = {}
        self.file_jobs = []
        self.setObjectName("reportsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(12)

        title = QLabel(T("Reports"))
        title.setStyleSheet(page_title_style())
        layout.addWidget(title)
        self.period_caption = QLabel()
        self.period_caption.setStyleSheet(page_subtitle_style())
        layout.addWidget(self.period_caption)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        layout.addLayout(toolbar)
        today = QDate.currentDate()
        self.dates = []
        for label, value in (("From", QDate(today.year(), today.month(), 1)), ("To", today)):
            toolbar.addWidget(QLabel(T(label)))
            field = QDateEdit(value)
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd MMM yyyy")
            field.setMinimumWidth(158)
            field.setMinimumHeight(36)
            field.setKeyboardTracking(False)
            toolbar.addWidget(field)
            self.dates.append(field)
        toolbar.addStretch()
        self.export_btn = self.button("Export report", "SP_DialogSaveButton", self.save_report)
        toolbar.addWidget(self.export_btn)

        self.metrics = []
        stats = QGridLayout()
        layout.addLayout(stats)
        for i, (label, color) in enumerate((
            ("Receipts", BLUE), ("Gross sales", TEXT),
            ("Refunds", "#a84418"), ("Net sales", "#147a61"),
        )):
            card = QFrame()
            card.setObjectName("metric")
            box = QVBoxLayout(card)
            box.setContentsMargins(16, 12, 16, 12)
            box.setSpacing(6)
            card.setStyleSheet(
                f"QFrame#metric {{background:white; border:1px solid {BORDER};"
                f"border-top:3px solid {color}; border-radius:6px;}}"
            )
            caption = QLabel(T(label))
            caption.setStyleSheet(page_subtitle_style())
            value = QLabel("0")
            value.setStyleSheet(f"background:transparent;color:{color};font-size:19px;font-weight:700")
            box.addWidget(caption)
            box.addWidget(value)
            stats.addWidget(card, 0, i)
            stats.setColumnStretch(i, 1)
            self.metrics.append(value)

        row = QHBoxLayout()
        row.addWidget(QLabel(T("Report")))
        self.view = QComboBox()
        for key in ("Daily", "Monthly", "Payment", "Products", "Returns",
                    "Low stock now", "Expiry now", "Fast movers", "Slow movers"):
            self.view.addItem(T(key), key)
        row.addWidget(self.view)
        row.addStretch()
        self.count = QLabel()
        row.addWidget(self.count)
        layout.addLayout(row)

        self.stack = QStackedWidget()
        self.table = QTableWidget(0, 0)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.horizontalHeader().setFixedHeight(38)
        self.table.setStyleSheet(f"""
            QTableWidget {{background:white; border:1px solid {BORDER};}}
            QTableWidget::item {{padding:0 10px; border-bottom:1px solid {BORDER};}}
        """)
        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)
        layout.addWidget(self.stack, 1)

        if self.admin:
            footer = QHBoxLayout()
            footer.addWidget(QLabel(T("Pharmacy data")))
            footer.addStretch()
            footer.addWidget(self.button("Backup database", "SP_DialogSaveButton", self.backup_database))
            footer.addWidget(self.button("Restore database", "SP_DialogOpenButton", self.restore_database))
            footer.addWidget(self.button("Export data", "SP_DialogSaveButton", self.save_data))
            footer.addWidget(self.button("Merge data", "SP_DialogOpenButton", self.merge))
            layout.addLayout(footer)

        self.setStyleSheet(f"""
            QWidget#reportsPage {{background:{CANVAS};}}
            QFrame#metric,QTableWidget {{background:{SURFACE};border:1px solid {BORDER};border-radius:6px;}}
            QDateEdit,QComboBox {{background:white;color:{TEXT};border:1px solid {BORDER};padding:5px 9px;border-radius:5px;}}
            QTableWidget {{alternate-background-color:{SURFACE_SOFT};selection-background-color:#d9eee5;selection-color:{TEXT};}}
            QTableWidget::item {{padding:0 8px;}}
            QHeaderView::section {{background:{SURFACE_SOFT};color:{TEXT_MUTED};padding:8px;border:0;border-bottom:1px solid {BORDER};font-weight:600;}}
        """)
        self.view.currentTextChanged.connect(self.render)
        for field in self.dates:
            field.dateChanged.connect(self.refresh)

    def button(self, text, icon, slot):
        b = QPushButton(T(text))
        b.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, icon)))
        b.setStyleSheet(primary_button_style(PRIMARY, "#0f654f")
                       if text == "Export report" else soft_button_style())
        b.setMinimumHeight(34)
        b.clicked.connect(slot)
        return b


    def refresh(self, *_):
        start, end = [f.date().toString("yyyy-MM-dd") for f in self.dates]
        self.period_caption.setText(" – ".join(
            f.locale().toString(f.date(), "dd MMM yyyy") for f in self.dates
        ))
        self.data = {}
        self.problem = T("Choose an end date on or after the start date.")
        if start <= end:
            try:
                self.data = report_data(start, end)
            except Exception as e:
                self.problem = TF("Could not load reports: {error}", error=e)
        daily = self.data.get("Daily", ([], []))[1]
        for ix, label in enumerate(self.metrics, 1):
            n = sum(r[ix] or 0 for r in daily)
            label.setText((format_number(n, 0) if ix == 1 else format_money(n)) if self.data else "-")
        self.export_btn.setEnabled(bool(self.data))
        self.render()

    def render(self, *_):
        report_key = self.view.currentData() or self.view.currentText()
        headers, rows = self.data.get(report_key, ([], []))
        if report_key in ("Daily", "Monthly"):
            rows = rows[::-1]
        self.count.setText(TF("{count} rows", count=len(rows)) if self.data else "")
        if not rows:
            self.empty.setText(T("No matching records.") if self.data else self.problem)
            self.stack.setCurrentWidget(self.empty)
            return
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels([T(h) for h in headers])
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                money = headers[j].endswith("(Ft)")
                item = QTableWidgetItem(format_number(v, 2) if money and v is not None
                                        else str(v if v is not None else ""))
                self.table.setItem(i, j, item)
                align = (Qt.AlignmentFlag.AlignRight if isinstance(v, (int, float))
                         else Qt.AlignmentFlag.AlignLeft)
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        for j, name in enumerate(headers):
            numeric = any(isinstance(r[j], (int, float)) for r in rows)
            self.table.horizontalHeaderItem(j).setTextAlignment(
                (Qt.AlignmentFlag.AlignRight if numeric else Qt.AlignmentFlag.AlignLeft)
                | Qt.AlignmentFlag.AlignVCenter
            )
        self.stack.setCurrentWidget(self.table)

    def file_action(self, title, action, opening=False, background=False,
                    progress_text="Working..."):
        dialog = QFileDialog.getOpenFileName if opening else QFileDialog.getSaveFileName
        path, _ = dialog(self, T(title), "", T("Excel Workbook (*.xlsx)"))
        if not path:
            return
        if not opening and not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        if background:
            self.start_file_job(T(title), T(progress_text), path, action)
            return
        try:
            message = action(path)
        except Exception as e:
            QMessageBox.warning(self, T(title), T(str(e)))
            return
        QMessageBox.information(self, T(title), T(message or "Export complete."))

    def start_file_job(self, title, progress_text, path, action):
        progress = QProgressDialog(progress_text, "", 0, 0, self)
        progress.setWindowTitle(title)
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.show()

        identity = (
            self.current_user.get("username", "System"),
            self.current_user.get("role", ""),
        )
        thread = FileActionThread(action, path, identity, self)
        job = {"thread": thread, "progress": progress, "title": title}
        self.file_jobs.append(job)
        thread.succeeded.connect(
            lambda message, current=job: self.finish_file_job(current, message=message)
        )
        thread.failed.connect(
            lambda error, current=job: self.finish_file_job(current, error=error)
        )
        thread.finished.connect(lambda current=job: self.release_file_job(current))
        thread.start()

    def finish_file_job(self, job, message=None, error=None):
        job["progress"].close()
        if error:
            QMessageBox.warning(self, job["title"], T(str(error)))
        else:
            QMessageBox.information(
                self, job["title"], T(message or "Export complete.")
            )

    def release_file_job(self, job):
        if job in self.file_jobs:
            self.file_jobs.remove(job)
        job["thread"].deleteLater()
        job["progress"].deleteLater()

    def save_report(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from database.workbook import put

        def save(path):
            wb = Workbook()
            wb.active.title = T("Period")
            put(wb.active, [T("From"), T("To"), T("Inventory as of")])
            put(wb.active, [f.date().toString("yyyy-MM-dd") for f in self.dates]
                + [QDate.currentDate().toString("yyyy-MM-dd")])
            for title, (cols, rows) in self.data.items():
                ws = wb.create_sheet(T(title)[:31])
                put(ws, [T(column) for column in cols])
                for row in rows:
                    put(ws, row)
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions
                for cell in ws[1]:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="205449")
                    ws.column_dimensions[cell.column_letter].width = max(18, len(cell.value) + 4)
            wb.save(path)

        self.file_action("Export report", save)

    def save_data(self):
        from database.workbook import export_book
        self.file_action(
            "Export private pharmacy data",
            export_book,
            background=True,
            progress_text="Exporting pharmacy data...",
        )

    def backup_database(self):
        from database.backup import create_database_backup

        path, _ = QFileDialog.getSaveFileName(
            self, T("Backup database"), "", T("SQLite Database (*.db)")
        )
        if not path:
            return
        if not path.lower().endswith(".db"):
            path += ".db"
        try:
            create_database_backup(path)
        except Exception as error:
            QMessageBox.warning(
                self, T("Backup database"),
                TF("Database backup failed: {error}", error=error),
            )
            return
        QMessageBox.information(
            self, T("Backup database"), T("Database backup created successfully."),
        )

    def restore_database(self):
        from database.backup import restore_database

        path, _ = QFileDialog.getOpenFileName(
            self, T("Restore database"), "", T("SQLite Database (*.db)")
        )
        if not path:
            return
        answer = QMessageBox.question(
            self,
            T("Restore database"),
            T("Restoring will replace the current database. A safety backup will be created and the application will close. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            safety_path = restore_database(path)
        except Exception as error:
            QMessageBox.warning(
                self, T("Restore database"),
                TF("Database restore failed: {error}", error=error),
            )
            return
        QMessageBox.information(
            self,
            T("Restore database"),
            TF("Database restored successfully. Safety backup: {path}", path=safety_path),
        )
        QApplication.quit()

    def merge(self):
        from database.workbook import import_book

        def apply(path):
            answer = QMessageBox.question(
                self, T("Merge pharmacy data"),
                T("Add missing records from this workbook? Existing records will not be overwritten."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return T("No changes made.")
            added, skipped = import_book(path)
            self.refresh()
            return TF("Added: {added}\nAlready present: {skipped}", added=added, skipped=skipped)

        self.file_action("Merge pharmacy data", apply, True)
