from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Database setup
def get_db():
    conn = sqlite3.connect("khata.db")
    conn.row_factory = sqlite3.Row
    return conn

# Home
@app.route("/")
def index():
    conn = get_db()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("index.html", members=members)

# Add Member
@app.route("/add_member", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        name = request.form["name"]
        conn = get_db()
        conn.execute("INSERT INTO members (name, balance) VALUES (?, ?)", (name, 0))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("add_member.html")

# Add Transaction
@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    conn = get_db()
    members = conn.execute("SELECT * FROM members").fetchall()
    if request.method == "POST":
        member_id = request.form["member_id"]
        amount = int(request.form["amount"])
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO transactions (member_id, amount, date) VALUES (?, ?, ?)",
                     (member_id, amount, date))
        conn.execute("UPDATE members SET balance = balance + ? WHERE id = ?", (amount, member_id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    conn.close()
    return render_template("add_transaction.html", members=members)

# View History
@app.route("/history/<int:member_id>")
def history(member_id):
    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    transactions = conn.execute("SELECT * FROM transactions WHERE member_id=?", (member_id,)).fetchall()
    conn.close()
    return render_template("history.html", member=member, transactions=transactions)

# Filter Members (positive/negative balance)
@app.route("/filter")
def filter_members():
    t = request.args.get("type")
    conn = get_db()
    if t == "positive":
        members = conn.execute("SELECT * FROM members WHERE balance >= 0").fetchall()
    elif t == "negative":
        members = conn.execute("SELECT * FROM members WHERE balance < 0").fetchall()
    else:
        members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return render_template("filter.html", members=members)

# Search
@app.route("/search", methods=["GET", "POST"])
def search():
    members = []
    if request.method == "POST":
        query = request.form["query"]
        conn = get_db()
        members = conn.execute("SELECT * FROM members WHERE name LIKE ?", ('%' + query + '%',)).fetchall()
        conn.close()
    return render_template("search.html", members=members)

# Delete Member
@app.route("/delete/<int:member_id>")
def delete_member(member_id):
    conn = get_db()
    # पहले transactions हटाओ
    conn.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
    # फिर member हटाओ
    conn.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# Main entry
if __name__ == "__main__":
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        balance INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        amount INTEGER,
        date TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id)
    )""")
    conn.commit()
    conn.close()
    app.run(debug=True)
