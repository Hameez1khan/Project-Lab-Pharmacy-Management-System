import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading


def get_log_directory():
    override = os.environ.get("KHALIS_DAWA_LOG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "KhalisDawa"
    return base / "logs"


def configure_logging(level=logging.INFO):
    log_dir = get_log_directory()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "application.log"
    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    root = logging.getLogger()
    root.setLevel(level)
    if not any(
        isinstance(existing, RotatingFileHandler)
        and Path(existing.baseFilename) == log_path
        for existing in root.handlers
    ):
        root.addHandler(handler)
    return log_path


def install_crash_handlers():
    previous_sys_hook = sys.excepthook
    previous_thread_hook = getattr(threading, "excepthook", None)

    def handle_exception(exception_type, exception, traceback):
        if issubclass(exception_type, KeyboardInterrupt):
            previous_sys_hook(exception_type, exception, traceback)
            return
        logging.getLogger("crash").critical(
            "Unhandled application exception",
            exc_info=(exception_type, exception, traceback),
        )

    def handle_thread_exception(args):
        logging.getLogger("crash").critical(
            "Unhandled exception in thread %s",
            getattr(args.thread, "name", "unknown"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        if previous_thread_hook:
            previous_thread_hook(args)

    sys.excepthook = handle_exception
    if previous_thread_hook:
        threading.excepthook = handle_thread_exception
