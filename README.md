# Pharmacy Management System

This is a desktop pharmacy application made for managing daily pharmacy work in one place.

It helps administrators and pharmacists handle:

- medicines and product details
- batch stock and expiry dates
- sales and checkout
- prescription records
- returned items
- audit logs
- dashboard summaries and a 30-day sales chart
- reports and Excel data exchange
- database backup and restore

## What This System Can Do

The application includes:

- separate login access for **Admin** and **Pharmacist**
- product management with barcode, category, price, and dosage form
- batch-based stock tracking
- supplier management, purchase orders, partial/full receiving, and purchase history
- reorder suggestions based on recent sales, usable stock, delivery time, and safety stock
- expiry monitoring
- checkout and cart handling
- prescription tracking for medicines that require it
- sales history and receipt download
- returned items tracking
- audit logs with change history
- dashboard cards and a 30-day net-sales chart
- daily and monthly reports, product movement reports, and Excel export
- safe Excel data merge that skips duplicate records
- exact database backup and restore
- English, Hungarian, and Arabic interface languages
- administrator checkout-performance statistics

## What You Need Before Running It

Install **Python 3.11** before continuing.

## Setup

1. Open a terminal inside the project folder.
2. Create a virtual environment:

```powershell
py -3.11 -m venv .venv
```

3. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

## How to Start the Program

Run:

```powershell
python main.py
```

That is the normal way to start the software.

## First-Time Use

When the program starts for the first time:

- the local database is created automatically
- the required tables are created automatically
- the default admin account is added automatically if it does not already exist

You do **not** need to run any extra setup script before starting the program.

## Default Admin Account

The program creates a default admin account on first startup:

- **Username:** `admin`
- **Password:** `1234`

After logging in, it is a good idea to change the password.

## Optional Scripts

There is also a `scripts/` folder in the project.

These scripts are **optional**. They are mainly for testing, maintenance, or preparing sample data.

Most users do **not** need them.

Normal use only requires:

```powershell
python main.py
```

## Optional Thesis Dataset

Developers and reviewers can generate a separate, realistic thesis dataset. It does not replace or add records to the normal pharmacy database.

```powershell
python scripts\data_tools\generate_demo_database.py --force
powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1
```

The generator is repeatable and supports custom sizes. Run `python scripts\data_tools\generate_demo_database.py --help` to see the options.

Dataset accounts:

- **Administrator:** `admin` / `1234`
- **Pharmacist:** `nora` / `Pharmacy2026!`

The generated database is ignored by Git.

## Project Files

```text
Project-Lab-Pharmacy-Management-System/
|- assets/
|- database/
|- docs/
|- pages/
|- scripts/
|- tests/
|- login_window.py
|- main.py
|- main_window.py
|- requirements.txt
|- ui_theme.py
`- README.md
```

## Documents

The `docs/` folder contains:

- `developer-guide.pdf`
- `user-manual.pdf`
- `presentation-slides.pdf`

## Main Parts of the Program

### Dashboard
Shows medicine count, sales, returned items, low stock, expiry alerts, and the last 30 days of net sales.

### Batch Management
Used for managing medicine batches, stock quantity, and expiry dates.

### Purchasing
Used by administrators to manage suppliers and the full purchasing flow. Staff can create purchase orders, submit or cancel them, record partial or complete deliveries, review delivery notes, and see purchase history. Stock is updated only when a delivery is received.

The reorder page estimates an order quantity from recent sales, current usable stock, open purchase orders, supplier delivery time, safety days, and the product's minimum stock level. The result can be adjusted before creating a draft purchase order.

### Point of Sale
Used for searching products, adding them to the cart, and completing sales.

### Products
Used for adding, editing, and viewing medicine records.

### Prescriptions
Used for viewing medicines that were sold with prescription-related customer information.

### Sales History
Used for viewing completed sales, downloading receipts, and handling returns.

### Returned Items
Used for viewing completed returns and refund records.

### Reports
Used for daily or monthly sales summaries, fast and slow movers, low stock, expiring batches, report export, Excel data exchange, and database backup or restore.

### Audit Logs
Used for checking important actions performed by users.

### POS Performance
Available to administrators for reviewing checkout attempts, success rates, processing times, and measured checkout phases. It stores timing information only, not customer names, SSNs, barcodes, or search text.

### Settings
Used for password, account, and language settings.

## Backup and Data Transfer

The **Reports** page provides two different options:

- **Backup database** creates an exact copy of the pharmacy database. Use this for full recovery.
- **Export data** creates a readable Excel workbook, including suppliers, purchase orders, deliveries, inventory, sales, returns, and audit history. Use **Merge data** to add records from such a workbook while skipping records already present.

Restoring a database replaces the current data. The application creates a safety backup first and then closes so the restored database can be loaded on the next start.

## Run the Tests

Install the development tools:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the backend and interface checks:

```powershell
python -m unittest discover -s tests/backend -v
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests/ui -v
```

Measure local checkout database performance:

```powershell
python scripts\verification\benchmark_checkout.py
```

## Create a Windows Application

After installing the development tools, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\packaging\build_windows.ps1
```

The packaged application is created in `dist\KhalisDawa\`.

## Important Notes

- The program uses a local SQLite database stored in `database\pharmacy.db` when run from source.
- Report summaries and pharmacy data are exported as Excel workbooks.
- Application logs are stored in the current user's local application-data folder.
- This system is designed for desktop use.
