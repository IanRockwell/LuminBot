import sqlite3
import json
import os

# Database file
DB_FILE = 'data.db'

def create_table():
    """
    Create the 'documents' table if it doesn't exist in the database.
    """
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
    """
    Retrieve data associated with a specific document_id from the 'documents' table.

    Args:
        document_id (str): The unique identifier for the document.

    Returns:
        dict: The data associated with the document_id, parsed from JSON. If the document_id
        does not exist, an empty dictionary is returned.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT data FROM documents WHERE document_id = ?', (document_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else {}

def update_data(document_id, new_data):
    """
    Update or insert data associated with a specific document_id into the 'documents' table.

    Args:
        document_id (str): The unique identifier for the document.
        new_data (dict): The new data to be associated with the document_id.

    Returns:
        None
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO documents (document_id, data) VALUES (?, ?)', (document_id, json.dumps(new_data)))
    conn.commit()
    conn.close()

def delete_data(document_id):
    """
    Delete data associated with a specific document_id from the 'documents' table.

    Args:
        document_id (str): The unique identifier for the document.

    Returns:
        None
    """
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