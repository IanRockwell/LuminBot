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

def get_sorted_document_ids(sort_key):
    """
    Get a sorted list of document IDs based on a specified nested JSON value.

    Args:
        sort_key (str): The nested key within the JSON data to be used for sorting.

    Returns:
        list: A sorted list of document IDs.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Select document_id and data columns from the 'documents' table
    c.execute('SELECT document_id, data FROM documents')

    # Fetch all rows from the cursor
    rows = c.fetchall()

    # Create a list to store tuples of document_id and the corresponding JSON value for sorting
    sortable_list = []

    for row in rows:
        document_id, data = row
        # Load JSON data
        json_data = json.loads(data)

        # Check if the sort_key exists in the nested structure of JSON data
        nested_keys = sort_key.split('.')
        current_value = json_data

        for nested_key in nested_keys:
            if nested_key in current_value:
                current_value = current_value[nested_key]
            else:
                current_value = None
                break

        if current_value is not None:
            sortable_list.append((document_id, current_value))

    # Sort the list based on the specified nested JSON value in descending order
    sortable_list.sort(key=lambda x: x[1], reverse=True)

    # Extract and return the sorted document IDs
    sorted_document_ids = [item[0] for item in sortable_list]

    conn.close()
    return sorted_document_ids


def get_documents_with_key(search_key):
    """
    Get a list of document IDs that contain a specific key within their JSON data.

    Args:
        search_key (str): The key to search for within the JSON data.

    Returns:
        list: A list of document IDs that contain the specified key.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Select document_id and data columns from the 'documents' table
    c.execute('SELECT document_id, data FROM documents')

    # Fetch all rows from the cursor
    rows = c.fetchall()

    # Create a list to store tuples of document_id and the corresponding JSON value for sorting
    sortable_list = []

    for row in rows:
        document_id, data = row
        # Load JSON data
        json_data = json.loads(data)

        # Check if the sort_key exists in the nested structure of JSON data
        nested_keys = search_key.split('.')
        current_value = json_data

        for nested_key in nested_keys:
            if nested_key in current_value:
                current_value = current_value[nested_key]
            else:
                current_value = None
                break

        if current_value is not None:
            sortable_list.append((document_id, current_value))

    list_of_ids = [item[0] for item in sortable_list]

    conn.close()
    return list_of_ids


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