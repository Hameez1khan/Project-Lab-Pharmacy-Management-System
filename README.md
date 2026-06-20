# Pharmacy Management System

This is a desktop pharmacy application made for managing daily pharmacy work in one place.

It helps administrators and pharmacists handle:

- medicines and product details
- batch stock and expiry dates
- sales and checkout
- prescription records
- returned items
- audit logs
- basic dashboard summaries

## What This System Can Do

The application includes:

- separate login access for **Admin** and **Pharmacist**
- product management with barcode, category, price, and dosage form
- batch-based stock tracking
- expiry monitoring
- checkout and cart handling
- prescription tracking for medicines that require it
- sales history and receipt download
- returned items tracking
- audit logs for important actions
- dashboard cards for quick business overview

## What You Need Before Running It

Make sure you have:

- **Python 3.11** installed
- **PyQt6** installed

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

4. Install the required package:

```powershell
pip install PyQt6
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

## Project Files

```text
Project-Lab-Pharmacy-Management-System/
|- assets/
|- database/
|- docs/
|- pages/
|- scripts/
|- login_window.py
|- main.py
|- main_window.py
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
Shows a quick summary such as medicine count, sales, returned items, low stock, and expiry alerts.

### Batch Management
Used for managing medicine batches, stock quantity, and expiry dates.

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

### Audit Logs
Used for checking important actions performed by users.

### Settings
Used for password and account-related management.

## Important Notes

- The program uses a local database stored inside the project.
- Reports are saved as **HTML files** in the user's **Downloads** folder.
- This system is designed for desktop use.

## Future Improvements

Possible future updates may include:

- easier Windows installation
- automatic dependency installation
- automated tests
- database backup and restore tools
- more advanced reports
