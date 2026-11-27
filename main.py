import logging
import sys

from app_logging import configure_logging, install_crash_handlers


def main():
    log_path = configure_logging()
    install_crash_handlers()
    logger = logging.getLogger("application")
    logger.info("Starting Khalis Dawa; log file: %s", log_path)

    from PyQt6.QtWidgets import QApplication
    from database.db import initialize_database
    from i18n import initialize_language
    from login_window import LoginWindow
    from ui_theme import app_stylesheet

    initialize_database()
    app = QApplication(sys.argv)
    app.setApplicationName("Khalis Dawa")
    app.setOrganizationName("KhalisDawa")
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())
    initialize_language(app)

    window = LoginWindow()
    window.showMaximized()
    result = app.exec()
    logger.info("Application closed with code %s", result)
    return result


if __name__ == "__main__":
    sys.exit(main())
