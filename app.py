import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-production")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "raqmyat.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'employee',
        active INTEGER NOT NULL DEFAULT 1)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
        title TEXT NOT NULL, details TEXT DEFAULT '', compatibility TEXT DEFAULT '',
        image_url TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ready_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
        account_password TEXT NOT NULL, notes TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'available',
        claimed_by INTEGER, claimed_at TEXT, completed_at TEXT,
        FOREIGN KEY(claimed_by) REFERENCES users(id))""")
    conn.commit()
    # First run: create the requested default administrator.
    if not conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                     ("admin", generate_password_hash("123123"), "admin"))
        conn.commit()
    conn.close()

init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = db().execute("SELECT * FROM users WHERE id=? AND active=1",
                            (session["user_id"],)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for("login"))
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.current_user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    return {"current_user": getattr(g, "current_user", None)}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE username=? AND active=1",
                            (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("home"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة، أو الحساب غير مفعّل.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    parts = db().execute("SELECT * FROM parts ORDER BY id DESC").fetchall()
    counts = {
        "screens": db().execute("SELECT COUNT(*) FROM parts WHERE kind='screen'").fetchone()[0],
        "protectors": db().execute("SELECT COUNT(*) FROM parts WHERE kind='protector'").fetchone()[0],
        "accounts": db().execute("SELECT COUNT(*) FROM ready_accounts WHERE status='available'").fetchone()[0]
    }
    return render_template("home.html", parts=parts, counts=counts)

@app.route("/parts/<kind>")
@login_required
def parts(kind):
    if kind not in ("screen", "protector"):
        abort(404)
    items = db().execute("SELECT * FROM parts WHERE kind=? ORDER BY id DESC", (kind,)).fetchall()
    return render_template("parts.html", items=items, kind=kind)

@app.route("/accounts")
@login_required
def accounts():
    items = db().execute("""SELECT id, notes FROM ready_accounts
                            WHERE status='available' ORDER BY id DESC""").fetchall()
    return render_template("accounts.html", items=items)

@app.route("/accounts/<int:account_id>/claim", methods=["POST"])
@login_required
def claim_account(account_id):
    conn = db()
    item = conn.execute("SELECT * FROM ready_accounts WHERE id=? AND status='available'",
                        (account_id,)).fetchone()
    if not item:
        flash("هذا الحساب لم يعد متاحاً.", "error")
        return redirect(url_for("accounts"))
    conn.execute("""UPDATE ready_accounts SET status='claimed', claimed_by=?,
                    claimed_at=CURRENT_TIMESTAMP WHERE id=? AND status='available'""",
                 (g.current_user["id"], account_id))
    conn.commit()
    return render_template("account_result.html", item=item)

@app.route("/accounts/<int:account_id>/complete", methods=["POST"])
@login_required
def complete_account(account_id):
    conn = db()
    conn.execute("""UPDATE ready_accounts SET status='completed', completed_at=CURRENT_TIMESTAMP
                    WHERE id=? AND claimed_by=? AND status='claimed'""",
                 (account_id, g.current_user["id"]))
    conn.commit()
    flash("تم تسجيل الدخول. لم يعد هذا الحساب يظهر ضمن الحسابات المتاحة.", "success")
    return redirect(url_for("accounts"))

@app.route("/admin")
@admin_required
def admin():
    users = db().execute("SELECT id,username,role,active FROM users ORDER BY id DESC").fetchall()
    parts_list = db().execute("SELECT * FROM parts ORDER BY id DESC").fetchall()
    accounts_list = db().execute("SELECT * FROM ready_accounts ORDER BY id DESC").fetchall()
    return render_template("admin.html", users=users, parts=parts_list, accounts=accounts_list)

@app.route("/admin/users/add", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "employee")
    if not username or len(password) < 4 or role not in ("employee", "admin"):
        flash("أدخل اسم مستخدم وكلمة مرور من 4 أحرف على الأقل.", "error")
    else:
        try:
            db().execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                         (username, generate_password_hash(password), role))
            db().commit()
            flash("تم إنشاء المستخدم.", "success")
        except sqlite3.IntegrityError:
            flash("اسم المستخدم مستخدم مسبقاً.", "error")
    return redirect(url_for("admin"))

@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    if user_id == g.current_user["id"]:
        flash("لا يمكنك تعطيل حسابك الحالي.", "error")
    else:
        db().execute("UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                     (user_id,))
        db().commit()
    return redirect(url_for("admin"))

@app.route("/admin/parts/add", methods=["POST"])
@admin_required
def add_part():
    kind = request.form.get("kind")
    title = request.form.get("title", "").strip()
    if kind not in ("screen", "protector") or not title:
        flash("اختر النوع واكتب اسم القطعة.", "error")
    else:
        db().execute("""INSERT INTO parts(kind,title,details,compatibility,image_url)
                        VALUES(?,?,?,?,?)""",
                     (kind, title, request.form.get("details","").strip(),
                      request.form.get("compatibility","").strip(),
                      request.form.get("image_url","").strip()))
        db().commit()
        flash("تمت إضافة القطعة.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/parts/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_part(item_id):
    db().execute("DELETE FROM parts WHERE id=?", (item_id,))
    db().commit()
    return redirect(url_for("admin"))

@app.route("/admin/accounts/add", methods=["POST"])
@admin_required
def add_account():
    email = request.form.get("email", "").strip()
    password = request.form.get("account_password", "")
    if not email or not password:
        flash("أدخل البريد وكلمة المرور.", "error")
    else:
        db().execute("INSERT INTO ready_accounts(email,account_password,notes) VALUES(?,?,?)",
                     (email, password, request.form.get("notes","").strip()))
        db().commit()
        flash("تمت إضافة الحساب إلى المخزون.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/accounts/<int:account_id>/delete", methods=["POST"])
@admin_required
def delete_account(account_id):
    db().execute("DELETE FROM ready_accounts WHERE id=?", (account_id,))
    db().commit()
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(error):
    return render_template("message.html", title="غير مسموح", message="هذه الصفحة خاصة بالمدير."), 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
