import sys
from PyQt6.QtWidgets import QApplication
from login_window import LoginWindow
from database.db import initialize_database


if __name__ == "__main__":
    # Initialize DB
    initialize_database()

    # Start app
    app = QApplication(sys.argv)

    # Open login screen
    window = LoginWindow()
    window.showMaximized()

    sys.exit(app.exec())
