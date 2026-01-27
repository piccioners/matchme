import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("matchme.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(schema)
