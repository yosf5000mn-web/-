from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, secrets, time
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "raqmiat.db")
app = Flask(__name__)
app.secret_key = os.environ.get("RAQMIAT_SECRET", "change-this-secret-before-sharing")
ADMIN_PASSWORD_HASH = generate_password_hash("123123")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS screens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL, kind TEXT NOT NULL, part_name TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL, password TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            claim_token TEXT DEFAULT NULL, claimed_at INTEGER DEFAULT NULL
        );
        """)
init_db()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", admin=session.get("admin", False))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if check_password_hash(ADMIN_PASSWORD_HASH, request.form.get("password", "")):
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("كلمة المرور غير صحيحة")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    with db() as con:
        screens = con.execute("SELECT * FROM screens ORDER BY phone, kind, part_name").fetchall()
        accounts = con.execute("SELECT * FROM accounts ORDER BY id DESC").fetchall()
    return render_template("admin.html", screens=screens, accounts=accounts)

@app.route("/admin/screen", methods=["POST"])
@admin_required
def add_screen():
    phone = request.form.get("phone","").strip()
    kind = request.form.get("kind","screen")
    part = request.form.get("part_name","").strip()
    notes = request.form.get("notes","").strip()
    if phone and part:
        with db() as con:
            con.execute("INSERT INTO screens(phone,kind,part_name,notes) VALUES(?,?,?,?)", (phone,kind,part,notes))
        flash("تمت إضافة القطعة والتوافق")
    else:
        flash("اكتب اسم الجهاز واسم القطعة")
    return redirect(url_for("admin"))

@app.route("/admin/screen/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_screen(item_id):
    with db() as con:
        con.execute("DELETE FROM screens WHERE id=?", (item_id,))
    return redirect(url_for("admin"))

@app.route("/admin/account", methods=["POST"])
@admin_required
def add_account():
    email = request.form.get("email","").strip()
    password = request.form.get("password","").strip()
    if email and password:
        with db() as con:
            con.execute("INSERT INTO accounts(email,password) VALUES(?,?)", (email,password))
        flash("تمت إضافة الحساب إلى المخزون")
    else:
        flash("أدخل البريد وكلمة المرور")
    return redirect(url_for("admin"))

@app.route("/admin/account/<int:item_id>/reset", methods=["POST"])
@admin_required
def reset_account(item_id):
    with db() as con:
        con.execute("UPDATE accounts SET status='available', claim_token=NULL, claimed_at=NULL WHERE id=?", (item_id,))
    return redirect(url_for("admin"))

@app.route("/admin/account/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_account(item_id):
    with db() as con:
        con.execute("DELETE FROM accounts WHERE id=?", (item_id,))
    return redirect(url_for("admin"))

@app.route("/api/screens")
def api_screens():
    q = request.args.get("q","").strip()
    kind = request.args.get("kind","all")
    with db() as con:
        sql = "SELECT * FROM screens WHERE phone LIKE ?"
        params = [f"%{q}%"]
        if kind in ("screen","protector"):
            sql += " AND kind=?"
            params.append(kind)
        sql += " ORDER BY phone, part_name"
        rows = con.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/claim", methods=["POST"])
def claim_account():
    token = secrets.token_urlsafe(24)
    with db() as con:
        row = con.execute("SELECT id,email,password FROM accounts WHERE status='available' ORDER BY id LIMIT 1").fetchone()
        if not row:
            return jsonify({"ok":False,"message":"لا توجد حسابات متاحة حالياً. راجع المحل."}), 404
        cur = con.execute("UPDATE accounts SET status='reserved',claim_token=?,claimed_at=? WHERE id=? AND status='available'",
                          (token, int(time.time()), row["id"]))
        if cur.rowcount != 1:
            return jsonify({"ok":False,"message":"تم حجز الحساب من مستخدم آخر، حاول مرة ثانية."}), 409
    return jsonify({"ok":True,"email":row["email"],"password":row["password"],"token":token})

@app.route("/api/complete", methods=["POST"])
def complete_account():
    token = (request.json or {}).get("token","")
    with db() as con:
        cur = con.execute("UPDATE accounts SET status='used',claim_token=NULL WHERE claim_token=? AND status='reserved'", (token,))
    if cur.rowcount:
        return jsonify({"ok":True})
    return jsonify({"ok":False,"message":"تعذر تأكيد الحساب. تواصل مع المدير."}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
