from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
app = Flask(__name__)
app.secret_key = "your_secret_key"
# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------- CREATE TABLES ----------
def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        category TEXT,
        date TEXT,
        payment TEXT,
        note TEXT,
        receipt TEXT
    )
    """)

    conn.commit()
    conn.close()

# ------------------ LOGIN ------------------
import sqlite3

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("loginIdentifier")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE username = ? OR email = ?
        """, (identifier, identifier))

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[4], password):
            session["user"] = user[2] # Store username in session
            session["user_id"] = user[0] # Store user ID in session
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials ❌"

    return render_template("login.html",show_sidebar=False)


# ------------------ REGISTER ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, hashed_password))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html",show_sidebar=False)


# ------------------ ADD EXPENSE ------------------
@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        amount = float(request.form.get("amount"))
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("add_expense"))
        category = request.form.get("category")
        date = request.form.get("date")
        payment = request.form.get('payment') or ''
        note = request.form.get('note') or ''
        # Optional receipt handling
        import os
        import time
        receipt = request.files.get('receipt')
        filepath = None
        if receipt and receipt.filename:
            allowed_extensions = ['png', 'jpg', 'jpeg']

            ext = receipt.filename.split('.')[-1].lower()

            if ext in allowed_extensions:
                filename = str(int(time.time())) + "_" + receipt.filename
                filepath = os.path.join("static/uploads", filename)
                receipt.save(filepath)
            else:
                filepath = None
           
        conn = get_db()
        cursor = conn.cursor()
       
        cursor.execute("""
            INSERT INTO expenses (user_id, title, amount, category, date, payment, note, receipt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], 
            title,
            amount,
            category, 
            date, 
            payment, 
            note, 
            filepath 
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_expense.html",show_sidebar=True)

# ------------------ EXPENSES PAGE ------------------
@app.route('/expenses')
def expenses_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM expenses 
        WHERE user_id = ?
        ORDER BY date DESC
    """, (session["user_id"],))

    expenses = cursor.fetchall()
    conn.close()

    return render_template("view_expenses.html", expenses=expenses)
# ------------------ EDIT EXPENSE ------------------
@app.route('/edit-expense/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("edit_expense", id=id))
        category = request.form['category']
        date = request.form['date']
        payment = request.form['payment']
        note = request.form.get('note')

        # Optional receipt handling
        receipt = request.files.get('receipt')
        # Get old receipt from DB
        cursor.execute("SELECT receipt FROM expenses WHERE id = ?", (id,))
        old_receipt = cursor.fetchone()[0]

        filepath = old_receipt  # default keep old file

        if receipt and receipt.filename:
            import os, time
            filename = str(int(time.time())) + "_" + receipt.filename
            filepath = os.path.join("static/uploads", filename)
            receipt.save(filepath)

        cursor.execute("""
        UPDATE expenses
        SET title=?, amount=?, category=?, date=?, payment=?, note=?, receipt=?
        WHERE id=? AND user_id=?
        """, (title, amount, category, date, payment, note, filepath, id, session["user_id"]))
        conn.commit()
        conn.close()

        return redirect('/expenses')

    # GET request
    cursor.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (id, session["user_id"]))
    expense = cursor.fetchone()

    conn.close()
    categories = [
    "Food", "Travel", "Shopping", "Education",
    "Bills", "Medical", "Entertainment", "Other"
]

    return render_template('edit_expense.html', expense=expense, categories=categories)
#------------------ DELETE EXPENSE ------------------
@app.route('/delete-expense/<int:id>', methods=['POST'])
def delete_expense(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Optional: delete receipt file also
    cursor.execute("SELECT receipt FROM expenses WHERE id=?", (id,))
    result = cursor.fetchone()
    if result and result[0]:
        import os
        if os.path.exists(result[0]):
            os.remove(result[0])

    # Delete from DB
    cursor.execute("""
    DELETE FROM expenses 
    WHERE id=? AND user_id=?
    """, (id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect('/expenses')
#------------------ REPORTS ------------------
@app.route('/reports')
def reports():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    user_id = session["user_id"]

    # 🔹 TOTAL
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0] or 0

    # 🔹 HIGHEST
    cursor.execute("SELECT MAX(amount) FROM expenses WHERE user_id=?", (user_id,))
    highest = cursor.fetchone()[0] or 0

    # 🔹 LOWEST
    cursor.execute("SELECT MIN(amount) FROM expenses WHERE user_id=?", (user_id,))
    lowest = cursor.fetchone()[0] or 0

    # 🔹 AVERAGE
    cursor.execute("SELECT AVG(amount) FROM expenses WHERE user_id=?", (user_id,))
    avg = cursor.fetchone()[0] or 0

    # 🔹 CATEGORY DATA
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id=?
        GROUP BY category
    """, (user_id,))
    category_data = cursor.fetchall()

    # 🔹 MONTHLY DATA
    cursor.execute("""
        SELECT substr(date,1,7), SUM(amount)
        FROM expenses
        WHERE user_id=?
        GROUP BY substr(date,1,7)
        ORDER BY substr(date,1,7)
    """, (user_id,))
    monthly_data = cursor.fetchall()
    max_month = max([row[1] for row in monthly_data], default=0)


    conn.close()

    return render_template(
        "reports.html",
        total=total,
        highest=highest,
        lowest=lowest,
        avg=round(avg, 2),
        category_data=category_data,
        monthly_data=monthly_data,
        max_month=max_month
    )

#------------------ PROFILE ------------------
@app.route('/profile')
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    user_id = session["user_id"]

    # 👤 USER DATA
    cursor.execute("""
        SELECT name, username, email FROM users WHERE id=?
    """, (user_id,))

    row = cursor.fetchone()

    user = {
        "name": row[0] if row[0] else row[1],  # 🔥 important fix
        "email": row[2]
    }

    # 📊 STATS
    cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
    count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        total=total,
        count=count
    )
# ------------------ update profile ------------------
@app.route('/update-profile', methods=['POST'])
def update_profile():
    name = request.form['name']
    email = request.form['email']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users SET name=?, email=?
        WHERE id=?
    """, (name, email, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect('/profile')
# ------------------ CHANGE PASSWORD ------------------
from werkzeug.security import generate_password_hash

@app.route('/change-password', methods=['POST'])
def change_password():
    new_pass = request.form['new_password']

    #  hash it
    hashed = generate_password_hash(new_pass)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users SET password=?
        WHERE id=?
    """, (hashed, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect('/profile')
# -------------------------- FORGOT PASSWORD ------------------
from werkzeug.security import generate_password_hash

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()

        # check user exists
        cursor.execute("SELECT id FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return "User not found"

        # hash password
        hashed = generate_password_hash(new_password)

        # update password
        cursor.execute("""
            UPDATE users SET password=?
            WHERE email=?
        """, (hashed, email))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("forgot_password.html")
# ------------------ DASHBOARD ------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    user_id = session["user_id"]

    # FETCH EXPENSES
    cursor.execute("""
        SELECT * FROM expenses
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    expenses = cursor.fetchall()

    # CALCULATIONS
    from datetime import datetime

    today = datetime.today().strftime("%Y-%m-%d")
    current_month = datetime.today().strftime("%Y-%m")

    # TOTAL
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0] or 0

    # TODAY
    cursor.execute("""
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND date = ?
    """, (user_id, today))
    today_total = cursor.fetchone()[0] or 0

    # MONTH
    cursor.execute("""
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND substr(date,1,7) = ?
    """, (user_id, current_month))
    month_total = cursor.fetchone()[0] or 0

    # TOP CATEGORY
    cursor.execute("""
        SELECT category, SUM(amount) as total 
        FROM expenses 
        WHERE user_id = ?
        GROUP BY category 
        ORDER BY total DESC 
        LIMIT 1
    """, (user_id,))
    top = cursor.fetchone()
    top_category = top[0] if top else None

    # CATEGORY DATA (for chart)
    cursor.execute("""
        SELECT category, SUM(amount) 
        FROM expenses 
        WHERE user_id = ?
        GROUP BY category
    """, (user_id,))
    category_data = cursor.fetchall()

    labels = [row[0] for row in category_data]
    values = [row[1] for row in category_data]

    conn.close()

    return render_template(
        "dashboard.html",
        show_sidebar=True,
        user=session.get("user"),  
        expenses=expenses,
        total=total,
        today_total=today_total,
        month_total=month_total,
        top_category=top_category,
        labels=labels,
        values=values
    )        

#------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ------------------ RUN ------------------
if __name__ == "__main__":
    create_tables()
    app.run(debug=True) 