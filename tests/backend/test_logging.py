import logging
import os
from pathlib import Path
import tempfile
import unittest

from app_logging import configure_logging


class LoggingTests(unittest.TestCase):
    def test_configure_logging_writes_to_selected_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.get("KHALIS_DAWA_LOG_DIR")
            os.environ["KHALIS_DAWA_LOG_DIR"] = directory
            try:
                path = configure_logging()
                logging.getLogger("backend-test").warning("test warning")
                for handler in list(logging.getLogger().handlers):
                    handler.flush()
                    if getattr(handler, "baseFilename", None) == str(path):
                        logging.getLogger().removeHandler(handler)
                        handler.close()
                self.assertEqual(path, Path(directory) / "application.log")
                self.assertIn("test warning", path.read_text(encoding="utf-8"))
            finally:
                if previous is None:
                    os.environ.pop("KHALIS_DAWA_LOG_DIR", None)
                else:
                    os.environ["KHALIS_DAWA_LOG_DIR"] = previous
