# Project Lab - Pharmacy Management System

A desktop pharmacy management application built with **Python**, **PyQt6**, and **SQLite**.

The system is designed for pharmacy administrators and pharmacists to manage products, batches, prescriptions, sales, returns, and audit logs from a single desktop interface.

## Features

- Role-based login for **Admin** and **Pharmacist**
- Product management with category, dosage form, barcode, pricing, and prescription requirement
- Batch-based inventory management with expiry tracking
- Point of Sale workflow with quantity selection
- Prescription tracking with:
  - customer name
  - customer SSN
  - medicine name
  - quantity
  - purchase date
- Sales history with downloadable receipt documents
- Returned items management with downloadable return reports
- Audit logs for important user actions
- Dashboard with:
  - medicines count
  - sales count
  - returned items count
  - expiration alerts
  - low stock alerts
  - revenue summary

## Tech Stack

- **Python 3**
- **PyQt6** for the desktop UI
- **SQLite** for local data storage

## Project Structure

```text
Project-Lab-Pharmacy-Management-System/
|- assets/                  # Icons and static assets
|- database/
|  |- db.py                 # Main database logic
|  |- pharmacy.db           # SQLite database file
|  |- seed_data.py          # Optional seed data helper
|  `- mark_prescription_products.py
|- pages/
|  |- dashboard.py
|  |- batch_management.py
|  |- pos.py
|  |- product.py
|  |- prescriptions.py
|  |- sales_history.py
|  |- returned_items.py
|  |- audit_logs.py
|  |- settings.py
|  `- reports.py
|- login_window.py          # Login screen
|- main_window.py           # Main application shell
|- main.py                  # Application entry point
|- setup_db.py              # Database initialization helper
`- README.md
```

## Installation

1. Open a terminal in the project folder.

2. Create and activate a virtual environment if needed:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install PyQt6
```

If your environment does not already include SQLite support, use a standard Python installation from python.org.

## Running the Application

Start the app with:

```powershell
python main.py
```

The database is initialized automatically on startup.

## Default Admin Login

On first run, the system creates a default administrator account:

- **Username:** `admin`
- **Password:** `1234`

You should change the default password after logging in.

## Main Modules

### Dashboard
Overview of key pharmacy metrics, low-stock products, and batches expiring soon.

### Batch Management
Manage medicine batches, stock quantities, pricing, and expiry dates.

### Point of Sale
Sell medicines, manage prescription-required items, and capture customer information when required.

### Products
Manage the pharmacy catalog, including barcodes, categories, stock thresholds, and prescription flags.

### Prescriptions
Track sensitive medicine sales and generate prescription reports.

### Sales History
Review completed sales, download receipts, and process returns.

### Returned Items
Track completed returns and download return reports.

### Audit Logs
Review important actions performed by administrators and pharmacists.

### Settings
Manage passwords and account-related administrative actions.

## Notes

- This project uses a **local SQLite database** stored at:

```text
database/pharmacy.db
```

- The application is intended for **desktop use**.
- Most reports are exported as **HTML files** into the user's `Downloads` folder.

## Future Improvements

Possible next improvements include:

- packaged executable build for Windows
- dependency list in `requirements.txt`
- automated tests
- backup/export tools for the SQLite database
- richer reporting and analytics
