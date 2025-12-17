from flask import Flask, render_template, jsonify, abort
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.getenv("C2_DB_PATH", "data/c2_logs.sqlite3")

def get_data(table):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"[!] DB error: {e}")
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sessions")
def view_sessions():
    rows = get_data("sessions")
    return render_template("table.html", title="Sessions", rows=rows)

@app.route("/commands")
def view_commands():
    rows = get_data("commands")
    return render_template("table.html", title="Commands", rows=rows)

@app.route("/responses")
def view_responses():
    rows = get_data("responses")
    return render_template("table.html", title="Responses", rows=rows)

@app.route("/file_transfers")
def view_file_transfers():
    rows = get_data("file_transfers")
    return render_template("table.html", title="File Transfers", rows=rows)

# Optional: API access
@app.route("/api/<table>")
def api_table(table):
    if table not in {"sessions", "commands", "responses", "file_transfers"}:
        abort(404)
    rows = get_data(table)
    return jsonify([dict(row) for row in rows])

if __name__ == "__main__":
    app.run(debug=True)
