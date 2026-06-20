from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection


def main():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES ('admin', '1234', 'admin')
    """)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    main()
