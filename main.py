import sys
from PyQt6.QtWidgets import QApplication
from login_window import LoginWindow
from database.db import initialize_database


if __name__ == "__main__":
    # Initialize DB
    initialize_database()

    # Start app
    app = QApplication(sys.argv)
    from i18n import choose_language
    if not choose_language(app):
        sys.exit(0)

    # Open login screen
    window = LoginWindow()
    window.showMaximized()

    sys.exit(app.exec())
