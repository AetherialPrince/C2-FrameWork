import sqlite3
import threading
import os

_db_lock = threading.Lock()
MAX_DB_PATH_LEN = 255
DEFAULT_DB_PATH = "data/c2_logs.sqlite3"

def _connect(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    # Validate path
    if not isinstance(db_path, str) or not db_path.strip():
        db_path = DEFAULT_DB_PATH
    if len(db_path) > MAX_DB_PATH_LEN:
        db_path = DEFAULT_DB_PATH

    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = _connect(db_path)

    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                peer_ip TEXT NOT NULL,
                peer_port INTEGER NOT NULL,
                connected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                disconnected_at TEXT
            );

            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );

            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );

            CREATE TABLE IF NOT EXISTS file_transfers (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                direction TEXT NOT NULL,
                filename TEXT NOT NULL,
                size INTEGER NOT NULL,
                occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_client ON sessions(client_id);
            CREATE INDEX IF NOT EXISTS idx_cmd_client ON commands(client_id);
            CREATE INDEX IF NOT EXISTS idx_resp_client ON responses(client_id);
            CREATE INDEX IF NOT EXISTS idx_ft_client ON file_transfers(client_id);
        """)
    return conn

def record_session_open(conn, client_id, peer_ip, peer_port):
    try:
        client_id = int(client_id)
    except ValueError:
        client_id = -1

    peer_ip = str(peer_ip)[:255]
    try:
        peer_port = int(peer_port)
    except ValueError:
        peer_port = -1

    with _db_lock, conn:
        conn.execute(
            "INSERT INTO sessions (client_id, peer_ip, peer_port) VALUES (?, ?, ?)",
            (client_id, peer_ip, peer_port),
        )

def record_session_close(conn, client_id):
    with _db_lock, conn:
        conn.execute(
            "UPDATE sessions SET disconnected_at = (strftime('%Y-%m-%dT%H:%M:%fZ','now')) "
            "WHERE client_id = ? AND disconnected_at IS NULL",
            (client_id,)
        )

def record_command(conn, client_id, command):
    with _db_lock, conn:
        conn.execute(
            "INSERT INTO commands (client_id, command) VALUES (?, ?)",
            (client_id, command)
        )

def record_response(conn, client_id, data):
    data = str(data)
    with _db_lock, conn:
        conn.execute(
            "INSERT INTO responses (client_id, data) VALUES (?, ?)",
            (client_id, data)
        )

def record_file_transfer(conn, client_id, direction, filename, size):
    direction = str(direction)
    filename = str(filename)
    try:
        size = int(size)
    except ValueError:
        size = -1

    with _db_lock, conn:
        conn.execute(
            "INSERT INTO file_transfers (client_id, direction, filename, size) VALUES (?, ?, ?, ?)",
            (client_id, direction, filename, size)
        )
