import pytest
from work_with_db import Database

db = Database()


def test_insert_and_select():
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users;")

    cur.execute("INSERT INTO users (id, name) VALUES (%s, %s);", (1, "Andrii"))
    conn.commit()

    cur.execute("SELECT name FROM users WHERE id = %s;", (1,))
    result = cur.fetchone()

    assert result[0] == "Andrii"

    cur.close()
    conn.close()