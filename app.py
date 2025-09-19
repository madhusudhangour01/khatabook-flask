from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_supersecretkey")

# ================== DATABASE ==================
def get_db():
    conn = sqlite3.connect("khata.db")
    conn.row_factory = sqlite3.Row
    return conn

# ================== SIGNUP ==================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("❌ Username and password cannot be empty!", "error")
            return redirect(url_for("signup"))

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user:
            flash("⚠️ Username already exists! Please login.", "error")
            conn.close()
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        flash("✅ Account created successfully! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

# ================== LOGIN ==================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("❌ Fields cannot be empty!", "error")
            return redirect(url_for("login"))

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("✅ Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("❌ Invalid username or password!", "error")

    return render_template("login.html")

# ================== LOGOUT ==================
@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Logged out successfully!", "info")
    return redirect(url_for("login"))

# ================== MAIN APP ==================
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    members = conn.execute("SELECT * FROM members WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("index.html", members=members, username=session["username"])

@app.route("/add_member", methods=["GET", "POST"])
def add_member():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"].strip()
        if not name:
            flash("❌ Member name cannot be empty!", "error")
            return redirect(url_for("add_member"))

        conn = get_db()
        conn.execute("INSERT INTO members (name, balance, user_id) VALUES (?, ?, ?)", (name, 0, session["user_id"]))
        conn.commit()
        conn.close()
        flash("✅ Member added successfully!", "success")
        return redirect(url_for("index"))
    return render_template("add_member.html")

@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    members = conn.execute("SELECT * FROM members WHERE user_id=?", (session["user_id"],)).fetchall()
    if request.method == "POST":
        member_id = request.form["member_id"]
        try:
            amount = int(request.form["amount"])
        except ValueError:
            flash("❌ Amount must be a number!", "error")
            return redirect(url_for("add_transaction"))

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO transactions (member_id, amount, date) VALUES (?, ?, ?)",
                     (member_id, amount, date))
        conn.execute("UPDATE members SET balance = balance + ? WHERE id = ?", (amount, member_id))
        conn.commit()
        conn.close()
        flash("✅ Transaction added!", "success")
        return redirect(url_for("index"))
    conn.close()
    return render_template("add_transaction.html", members=members)

@app.route("/history/<int:member_id>")
def history(member_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id=? AND user_id=?", (member_id, session["user_id"])).fetchone()
    transactions = conn.execute("SELECT * FROM transactions WHERE member_id=?", (member_id,)).fetchall()
    conn.close()
    return render_template("history.html", member=member, transactions=transactions)

@app.route("/delete/<int:member_id>")
def delete_member(member_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
    conn.execute("DELETE FROM members WHERE id=? AND user_id=?", (member_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("🗑️ Member and transactions deleted!", "info")
    return redirect(url_for("index"))

@app.route("/filter/<string:filter_type>")
def filter_members(filter_type):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    if filter_type == "positive":
        members = conn.execute("SELECT * FROM members WHERE user_id=? AND balance >= 0", (session["user_id"],)).fetchall()
    elif filter_type == "negative":
        members = conn.execute("SELECT * FROM members WHERE user_id=? AND balance < 0", (session["user_id"],)).fetchall()
    else:
        members = conn.execute("SELECT * FROM members WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("index.html", members=members, username=session["username"])

@app.route("/search", methods=["GET", "POST"])
def search_member():
    if "user_id" not in session:
        return redirect(url_for("login"))

    members = []
    if request.method == "POST":
        search_name = request.form["search_name"].strip()
        conn = get_db()
        members = conn.execute("SELECT * FROM members WHERE user_id=? AND name LIKE ?", 
                               (session["user_id"], f"%{search_name}%")).fetchall()
        conn.close()

    return render_template("index.html", members=members, username=session["username"])

# ================== DATABASE INIT ==================
if __name__ == "__main__":
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        balance INTEGER DEFAULT 0,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
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
