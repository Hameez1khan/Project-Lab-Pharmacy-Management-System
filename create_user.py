from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
INSERT INTO users (username, password, role)
VALUES ('admin', '1234', 'admin')
""")

conn.commit()
conn.close()