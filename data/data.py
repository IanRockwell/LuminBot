import sqlite3
import json
import os

# Database file
DB_FILE = 'data.db'

def create_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_data(document_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT data FROM documents WHERE document_id = ?', (document_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else {}

def update_data(document_id, new_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO documents (document_id, data) VALUES (?, ?)', (document_id, json.dumps(new_data)))
    conn.commit()
    conn.close()

def delete_data(document_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM documents WHERE document_id = ?', (document_id,))
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    create_table()

else:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    table_exists = c.fetchone()
    conn.close()

    if not table_exists:
        create_table()
