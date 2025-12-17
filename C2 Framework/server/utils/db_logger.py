import sqlite3
import os

def init_db(db_path):
    """Initialize database with client tracking."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()

    # Clients table for persistent client info
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT UNIQUE,
            hostname TEXT,
            machine TEXT,
            processor TEXT,
            system TEXT,
            release TEXT,
            mac_address TEXT,
            machine_id TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Sessions table references client
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            ip TEXT,
            port INTEGER,
            opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)
    
    # Commands table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            command TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)
    
    # Responses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)
    
    # File transfers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            direction TEXT,
            filename TEXT,
            size INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    conn.commit()
    return conn

def register_or_update_client(conn, fingerprint, fp_data, ip, port):
    """Register new client or update existing one."""
    cur = conn.cursor()
    
    # Check if client exists
    cur.execute(
        "SELECT id FROM clients WHERE fingerprint = ?",
        (fingerprint,)
    )
    result = cur.fetchone()
    
    if result:
        # Update existing client
        client_id = result[0]
        cur.execute("""
            UPDATE clients 
            SET hostname = ?, machine = ?, processor = ?, 
                system = ?, release = ?, mac_address = ?,
                machine_id = ?, last_seen = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            fp_data.get('hostname'), fp_data.get('machine'),
            fp_data.get('processor'), fp_data.get('system'),
            fp_data.get('release'), fp_data.get('mac_address'),
            fp_data.get('machine_id'), client_id
        ))
    else:
        # Insert new client
        cur.execute("""
            INSERT INTO clients 
            (fingerprint, hostname, machine, processor, system, release, mac_address, machine_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fingerprint,
            fp_data.get('hostname'), fp_data.get('machine'),
            fp_data.get('processor'), fp_data.get('system'),
            fp_data.get('release'), fp_data.get('mac_address'),
            fp_data.get('machine_id')
        ))
        client_id = cur.lastrowid
    
    conn.commit()
    return client_id

def record_session_open(conn, client_id, ip, port):
    """Record new session for client."""
    # Close any existing open session for this client
    conn.execute("""
        UPDATE sessions 
        SET closed = CURRENT_TIMESTAMP 
        WHERE client_id = ? AND closed IS NULL
    """, (client_id,))
    
    # Insert new session
    conn.execute("""
        INSERT INTO sessions (client_id, ip, port) 
        VALUES (?, ?, ?)
    """, (client_id, ip, port))
    
    conn.commit()
    return client_id

def record_session_close(conn, client_id):
    """Close session for client."""
    conn.execute("""
        UPDATE sessions 
        SET closed = CURRENT_TIMESTAMP 
        WHERE client_id = ? AND closed IS NULL
    """, (client_id,))
    conn.commit()

def record_command(conn, client_id, cmd):
    conn.execute(
        "INSERT INTO commands (client_id, command) VALUES (?, ?)",
        (client_id, cmd)
    )
    conn.commit()

def record_response(conn, client_id, data):
    conn.execute(
        "INSERT INTO responses (client_id, response) VALUES (?, ?)",
        (client_id, data)
    )
    conn.commit()

def record_file_transfer(conn, client_id, direction, name, size):
    conn.execute(
        "INSERT INTO file_transfers (client_id, direction, filename, size) VALUES (?, ?, ?, ?)",
        (client_id, direction, name, size)
    )
    conn.commit()