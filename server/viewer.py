from flask import Flask, render_template, jsonify
import sqlite3
import os
from datetime import datetime

# ======================== CONFIGURATION ========================
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "data", "c2_logs.sqlite3")
PORT = 5000
HOST = "127.0.0.1"

# ======================== FLASK APP ========================
app = Flask(__name__)

# ======================== DATABASE FUNCTIONS ========================
def connect_db():
    """Connect to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None

def get_table_data(table_name):
    """Get data from a specific table."""
    conn = connect_db()
    if not conn:
        return []
    
    try:
        if table_name == 'sessions':
            cursor = conn.execute("""
                SELECT 
                    s.id,
                    s.client_id,
                    COALESCE(c.fingerprint, 'Legacy') as fingerprint,
                    s.ip,
                    s.port,
                    s.opened,
                    s.closed,
                    CASE 
                        WHEN s.closed IS NULL THEN 'Active'
                        ELSE 'Closed'
                    END as status
                FROM sessions s
                LEFT JOIN clients c ON s.client_id = c.id
                ORDER BY s.opened DESC
                LIMIT 100
            """)
        else:
            cursor = conn.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 100")
        
        rows = cursor.fetchall()
        return rows
    except:
        return []
    finally:
        conn.close()

def get_counts():
    """Get count for each table."""
    counts = {}
    tables = ['sessions', 'commands', 'responses', 'file_transfers']
    
    conn = connect_db()
    if not conn:
        return counts
    
    try:
        cursor = conn.cursor()
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        
        # Get active session count
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE closed IS NULL")
        counts['active_sessions'] = cursor.fetchone()[0]
            
    except:
        pass
    finally:
        conn.close()
    
    return counts

# ======================== ROUTES ========================
@app.route('/')
def index():
    """Home page with dashboard."""
    counts = get_counts()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template('index.html', 
                          counts=counts,
                          time=current_time)

@app.route('/<table>')
def show_table(table):
    """Show table data."""
    allowed = ['sessions', 'commands', 'responses', 'file_transfers']
    if table not in allowed:
        return "Table not found", 404
    
    rows = get_table_data(table)
    title = table.replace('_', ' ').title()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template('table.html',
                          title=title,
                          rows=rows,
                          time=current_time,
                          table_name=table)

@app.route('/api/<table>')
def api_table(table):
    """API endpoint for table data."""
    allowed = ['sessions', 'commands', 'responses', 'file_transfers']
    if table not in allowed:
        return jsonify({"error": "Table not found"}), 404
    
    rows = get_table_data(table)
    data = [dict(row) for row in rows]
    
    return jsonify({
        "table": table,
        "count": len(data),
        "data": data
    })

# ======================== MAIN ========================
if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    print(f"[+] Starting C2 Dashboard on http://{HOST}:{PORT}")
    print(f"[+] Database: {DB_PATH}")
    print(f"[+] Press Ctrl+C to stop")
    
    app.run(host=HOST, port=PORT, debug=False)