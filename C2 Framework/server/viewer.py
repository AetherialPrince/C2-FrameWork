from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

DB_PATH = "data/c2_logs.sqlite3"

def get_data(table):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/sessions')
def sessions():
    rows = get_data("sessions")
    return render_template("table.html", title="Sessions", rows=rows)

@app.route('/commands')
def commands():
    rows = get_data("commands")
    return render_template("table.html", title="Commands", rows=rows)

@app.route('/responses')
def responses():
    rows = get_data("responses")
    return render_template("table.html", title="Responses", rows=rows)

@app.route('/file_transfers')
def file_transfers():
    rows = get_data("file_transfers")
    return render_template("table.html", title="File Transfers", rows=rows)

if __name__ == "__main__":
    app.run(debug=True)
	