from datetime import datetime
from contextlib import closing
from pathlib import Path
import sqlite3

from database.db import get_connection, get_database_path


REQUIRED_TABLES = {
    "users", "products", "batches", "sales", "sale_items",
    "sale_batch_allocations", "returns", "return_items", "prescriptions",
}


def validate_database_file(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("The selected database file does not exist.")
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"Database integrity check failed: {integrity}")
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
    except sqlite3.DatabaseError as error:
        raise ValueError("The selected file is not a valid SQLite database.") from error
    missing = REQUIRED_TABLES - tables
    if missing:
        raise ValueError("The database is missing required tables: " + ", ".join(sorted(missing)))
    return {"path": path, "tables": tables, "integrity": integrity}


def create_database_backup(destination):
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination == get_database_path().resolve():
        raise ValueError("Choose a different file for the backup.")
    with closing(get_connection("Database backup")) as source, \
            closing(sqlite3.connect(destination)) as target:
        source.backup(target)
    validate_database_file(destination)
    return destination


def restore_database(source_path, safety_backup_dir=None):
    source_path = validate_database_file(source_path)["path"]
    active_path = get_database_path().resolve()
    if source_path == active_path:
        raise ValueError("The selected file is already the active database.")

    safety_dir = Path(safety_backup_dir or active_path.parent).expanduser().resolve()
    safety_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safety_path = safety_dir / f"pharmacy-before-restore-{stamp}.db"
    counter = 1
    while safety_path.exists():
        safety_path = safety_dir / f"pharmacy-before-restore-{stamp}-{counter}.db"
        counter += 1
    create_database_backup(safety_path)

    try:
        with closing(sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)) as source, \
                closing(sqlite3.connect(active_path)) as target:
            source.backup(target)
        validate_database_file(active_path)
    except Exception:
        with closing(sqlite3.connect(f"file:{safety_path.as_posix()}?mode=ro", uri=True)) as source, \
                closing(sqlite3.connect(active_path)) as target:
            source.backup(target)
        raise
    return safety_path
