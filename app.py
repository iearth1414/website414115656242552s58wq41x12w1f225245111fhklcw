# -*- coding: utf-8 -*-
import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# ตั้งค่าพื้นฐาน
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
DB_PATH = os.path.join(INSTANCE_DIR, "site.db")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "css"), exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SITE_SECRET_KEY", uuid.uuid4().hex)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12MB ต่อไฟล์อัปโหลด

ADMIN_ROUTE = "/adminearth"
DEFAULT_ADMIN_USER = "earth"
DEFAULT_ADMIN_PASS = "1414"


# ---------------------------------------------------------------------------
# ฐานข้อมูล
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_info (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            site_title TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            bio TEXT NOT NULL,
            avatar TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) AS c FROM site_info")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO site_info (id, site_title, owner_name, bio, avatar) "
            "VALUES (1, ?, ?, ?, ?)",
            ("บ้านของฉัน", "Earth", "แก้ไขคำแนะนำตัวได้ที่หน้าแอดมิน", None)
        )

    cur.execute("SELECT COUNT(*) AS c FROM admin")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO admin (id, username, password_hash) VALUES (1, ?, ?)",
            (DEFAULT_ADMIN_USER, generate_password_hash(DEFAULT_ADMIN_PASS))
        )

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    fname = "{0}.{1}".format(uuid.uuid4().hex, ext)
    file_storage.save(os.path.join(UPLOAD_DIR, fname))
    return fname


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# เทมเพลต (ฝังในไฟล์เดียว, ธีมมืด/นีออน)
# ---------------------------------------------------------------------------
BASE_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0a0a12; --panel:#121220; --panel2:#181828;
    --neon:#7f5cff; --neon2:#00e5ff; --text:#e8e8f5; --muted:#8a8aa3;
    --danger:#ff4d6d;
  }
  *{box-sizing:border-box;}
  body{
    margin:0; font-family:'Prompt',sans-serif; background:
      radial-gradient(circle at 20% 0%, #1a1030 0%, transparent 40%),
      radial-gradient(circle at 80% 10%, #001a2e 0%, transparent 40%),
      var(--bg);
    color:var(--text); min-height:100vh;
  }
  a{color:var(--neon2); text-decoration:none;}
  nav{
    display:flex; justify-content:space-between; align-items:center;
    padding:18px 32px; background:rgba(18,18,32,.85); backdrop-filter:blur(6px);
    border-bottom:1px solid rgba(127,92,255,.25); position:sticky; top:0; z-index:10;
  }
  nav .brand{font-weight:700; font-size:20px; letter-spacing:.5px;
    text-shadow:0 0 12px var(--neon);}
  nav .links a{margin-left:18px; color:var(--muted); font-weight:400;}
  nav .links a:hover{color:var(--neon2);}
  .wrap{max-width:960px; margin:0 auto; padding:32px 20px 80px;}
  .card{
    background:linear-gradient(180deg, var(--panel2), var(--panel));
    border:1px solid rgba(127,92,255,.2); border-radius:16px;
    padding:24px; margin-bottom:24px;
    box-shadow:0 0 30px rgba(127,92,255,.06);
  }
  .profile{display:flex; gap:20px; align-items:center; flex-wrap:wrap;}
  .avatar{
    width:96px; height:96px; border-radius:50%; object-fit:cover;
    border:2px solid var(--neon); box-shadow:0 0 20px rgba(127,92,255,.5);
    background:#1c1c2e;
  }
  .avatar.placeholder{display:flex; align-items:center; justify-content:center;
    font-size:32px; color:var(--neon2);}
  h1,h2,h3{margin:0 0 8px;}
  .muted{color:var(--muted);}
  .btn{
    display:inline-block; padding:10px 18px; border-radius:10px; border:none;
    background:linear-gradient(90deg, var(--neon), var(--neon2)); color:#0a0a12;
    font-weight:600; cursor:pointer; font-family:inherit; font-size:14px;
  }
  .btn:hover{filter:brightness(1.1);}
  .btn.secondary{background:transparent; color:var(--neon2); border:1px solid var(--neon2);}
  .btn.danger{background:var(--danger); color:#fff;}
  .btn.sm{padding:6px 12px; font-size:12px;}
  input,textarea{
    width:100%; padding:12px 14px; border-radius:10px; border:1px solid rgba(127,92,255,.3);
    background:#0d0d18; color:var(--text); font-family:inherit; font-size:14px; margin-bottom:14px;
  }
  textarea{min-height:160px; resize:vertical;}
  label{display:block; margin-bottom:6px; color:var(--muted); font-size:13px;}
  .post-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:18px;}
  .post-card{
    background:var(--panel2); border-radius:14px; overflow:hidden;
    border:1px solid rgba(0,229,255,.15); transition:.2s transform;
  }
  .post-card:hover{transform:translateY(-4px); border-color:var(--neon2);}
  .post-card img{width:100%; height:150px; object-fit:cover; display:block;}
  .post-card .body{padding:14px;}
  .post-card .body h3{font-size:16px;}
  .post-card .body p{color:var(--muted); font-size:13px; margin:6px 0 0;}
  .flash{padding:12px 16px; border-radius:10px; margin-bottom:16px; font-size:14px;}
  .flash.ok{background:rgba(0,255,160,.1); border:1px solid rgba(0,255,160,.4); color:#7effc4;}
  .flash.err{background:rgba(255,77,109,.1); border:1px solid rgba(255,77,109,.4); color:#ff9fb2;}
  table{width:100%; border-collapse:collapse;}
  th,td{padding:10px; text-align:left; border-bottom:1px solid rgba(127,92,255,.15); font-size:14px;}
  .row-actions{display:flex; gap:8px;}
  .dash-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:16px;}
  .dash-tile{padding:22px; border-radius:14px; background:var(--panel2);
    border:1px solid rgba(127,92,255,.25); text-align:center;}
  .dash-tile:hover{border-color:var(--neon2);}
  .dash-tile .n{font-size:26px;}
  .post-content{white-space:pre-wrap; line-height:1.8;}
  footer{text-align:center; color:var(--muted); font-size:12px; padding:30px 0;}
</style>
</head>
<body>
<nav>
  <div class="brand"><a href="{{ url_for('index') }}">{{ site_title }}</a></div>
  <div class="links">
    <a href="{{ url_for('index') }}">หน้าแรก</a>
    {% if session.get('is_admin') %}
      <a href="{{ url_for('admin_dashboard') }}">แดชบอร์ด</a>
      <a href="{{ url_for('admin_logout') }}">ออกจากระบบ</a>
    {% endif %}
  </div>
</nav>
<div class="wrap">
  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in msgs %}
      <div class="flash {{ 'ok' if cat=='ok' else 'err' }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  {{ body|safe }}
</div>
</body>
</html>
"""

INDEX_BODY = """
<div class="card profile">
  {% if info.avatar %}
    <img class="avatar" src="{{ url_for('static', filename='uploads/' + info.avatar) }}">
  {% else %}
    <div class="avatar placeholder">{{ info.owner_name[:1] }}</div>
  {% endif %}
  <div>
    <h1>{{ info.owner_name }}</h1>
    <p class="muted post-content">{{ info.bio }}</p>
  </div>
</div>

<h2>กระทู้ทั้งหมด</h2>
{% if posts %}
<div class="post-grid">
  {% for p in posts %}
  <a class="post-card" href="{{ url_for('view_post', post_id=p['id']) }}">
    {% if p['image'] %}
      <img src="{{ url_for('static', filename='uploads/' + p['image']) }}">
    {% endif %}
    <div class="body">
      <h3>{{ p['title'] }}</h3>
      <p>{{ p['created_at'] }}</p>
    </div>
  </a>
  {% endfor %}
</div>
{% else %}
<p class="muted">ยังไม่มีกระทู้</p>
{% endif %}
"""

POST_DETAIL_BODY = """
<div class="card">
  <h1>{{ post['title'] }}</h1>
  <p class="muted">โพสต์เมื่อ {{ post['created_at'] }}
    {% if post['updated_at'] != post['created_at'] %} ? แก้ไขล่าสุด {{ post['updated_at'] }}{% endif %}
  </p>
  {% if post['image'] %}
    <img src="{{ url_for('static', filename='uploads/' + post['image']) }}"
         style="width:100%;border-radius:12px;margin:16px 0;">
  {% endif %}
  <div class="post-content">{{ post['content'] }}</div>
</div>
<a class="btn secondary" href="{{ url_for('index') }}">&larr; กลับหน้าแรก</a>
"""

LOGIN_BODY = """
<div class="card" style="max-width:380px;margin:60px auto;">
  <h2 style="text-align:center;">เข้าสู่ระบบแอดมิน</h2>
  <form method="post">
    <label>ชื่อผู้ใช้</label>
    <input type="text" name="username" required autofocus>
    <label>รหัสผ่าน</label>
    <input type="password" name="password" required>
    <button class="btn" style="width:100%;" type="submit">เข้าสู่ระบบ</button>
  </form>
</div>
"""

DASHBOARD_BODY = """
<h1>แดชบอร์ด</h1>
<div class="dash-grid">
  <a class="dash-tile" href="{{ url_for('admin_profile') }}">
    <div class="n">??</div><div>แก้ไขคำแนะนำตัว</div>
  </a>
  <a class="dash-tile" href="{{ url_for('admin_posts') }}">
    <div class="n">??</div><div>จัดการกระทู้ ({{ post_count }})</div>
  </a>
  <a class="dash-tile" href="{{ url_for('admin_new_post') }}">
    <div class="n">?</div><div>เพิ่มกระทู้ใหม่</div>
  </a>
  <a class="dash-tile" href="{{ url_for('admin_change_password') }}">
    <div class="n">??</div><div>เปลี่ยนรหัสผ่าน</div>
  </a>
</div>
"""

PROFILE_FORM_BODY = """
<div class="card" style="max-width:560px;">
  <h2>แก้ไขคำแนะนำตัว</h2>
  <form method="post" enctype="multipart/form-data">
    <label>ชื่อเว็บ (แสดงบน Navbar)</label>
    <input type="text" name="site_title" value="{{ info.site_title }}" required>
    <label>ชื่อเจ้าของเว็บ</label>
    <input type="text" name="owner_name" value="{{ info.owner_name }}" required>
    <label>คำแนะนำตัว / bio</label>
    <textarea name="bio" required>{{ info.bio }}</textarea>
    <label>รูปโปรไฟล์ (ไม่บังคับ)</label>
    <input type="file" name="avatar" accept="image/*">
    <button class="btn" type="submit">บันทึก</button>
    <a class="btn secondary" href="{{ url_for('admin_dashboard') }}">ยกเลิก</a>
  </form>
</div>
"""

POSTS_MANAGE_BODY = """
<h1>จัดการกระทู้</h1>
<a class="btn" href="{{ url_for('admin_new_post') }}">? เพิ่มกระทู้ใหม่</a>
<div class="card" style="margin-top:20px;">
  <table>
    <tr><th>หัวข้อ</th><th>วันที่</th><th></th></tr>
    {% for p in posts %}
    <tr>
      <td><a href="{{ url_for('view_post', post_id=p['id']) }}">{{ p['title'] }}</a></td>
      <td class="muted">{{ p['created_at'] }}</td>
      <td class="row-actions">
        <a class="btn sm secondary" href="{{ url_for('admin_edit_post', post_id=p['id']) }}">แก้ไข</a>
        <form method="post" action="{{ url_for('admin_delete_post', post_id=p['id']) }}"
              onsubmit="return confirm('ลบกระทู้นี้ถาวร?');" style="margin:0;">
          <button class="btn sm danger" type="submit">ลบ</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="3" class="muted">ยังไม่มีกระทู้</td></tr>
    {% endfor %}
  </table>
</div>
"""

POST_FORM_BODY = """
<div class="card" style="max-width:640px;">
  <h2>{{ 'แก้ไขกระทู้' if post else 'เพิ่มกระทู้ใหม่' }}</h2>
  <form method="post" enctype="multipart/form-data">
    <label>หัวข้อ</label>
    <input type="text" name="title" value="{{ post['title'] if post else '' }}" required>
    <label>เนื้อหา (เกิดอะไรขึ้น / รายละเอียด)</label>
    <textarea name="content" required>{{ post['content'] if post else '' }}</textarea>
    <label>รูปภาพประกอบ (ไม่บังคับ)</label>
    <input type="file" name="image" accept="image/*">
    {% if post and post['image'] %}
      <p class="muted">รูปปัจจุบัน:</p>
      <img src="{{ url_for('static', filename='uploads/' + post['image']) }}"
           style="max-width:200px;border-radius:10px;margin-bottom:14px;">
    {% endif %}
    <button class="btn" type="submit">บันทึก</button>
    <a class="btn secondary" href="{{ url_for('admin_posts') }}">ยกเลิก</a>
  </form>
</div>
"""

CHANGE_PASSWORD_BODY = """
<div class="card" style="max-width:420px;">
  <h2>เปลี่ยนรหัสผ่านแอดมิน</h2>
  <form method="post">
    <label>รหัสผ่านเดิม</label>
    <input type="password" name="old_password" required>
    <label>รหัสผ่านใหม่</label>
    <input type="password" name="new_password" required minlength="4">
    <button class="btn" type="submit">บันทึก</button>
  </form>
</div>
"""


def render_page(title, body_template, **ctx):
    conn = get_db()
    info = conn.execute("SELECT * FROM site_info WHERE id=1").fetchone()
    conn.close()
    body = render_template_string(body_template, **ctx)
    return render_template_string(
        BASE_HTML, title=title, body=body, site_title=info["site_title"]
    )


# ---------------------------------------------------------------------------
# หน้าเว็บสาธารณะ
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    conn = get_db()
    info = conn.execute("SELECT * FROM site_info WHERE id=1").fetchone()
    posts = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    conn.close()
    return render_page(info["site_title"], INDEX_BODY, info=info, posts=posts)


@app.route("/post/<int:post_id>")
def view_post(post_id):
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    conn.close()
    if not post:
        abort(404)
    return render_page(post["title"], POST_DETAIL_BODY, post=post)


# ---------------------------------------------------------------------------
# ระบบแอดมิน — เข้าถึงได้เฉพาะเจ้าของเว็บผ่าน /adminearth เท่านั้น
# ---------------------------------------------------------------------------
@app.route(ADMIN_ROUTE, methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        row = conn.execute("SELECT * FROM admin WHERE id=1").fetchone()
        conn.close()
        if row and username == row["username"] and check_password_hash(row["password_hash"], password):
            session["is_admin"] = True
            flash("เข้าสู่ระบบสำเร็จ", "ok")
            return redirect(url_for("admin_dashboard"))
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "err")
    return render_page("เข้าสู่ระบบแอดมิน", LOGIN_BODY)


@app.route(ADMIN_ROUTE + "/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("ออกจากระบบแล้ว", "ok")
    return redirect(url_for("index"))


@app.route(ADMIN_ROUTE + "/dashboard")
@login_required
def admin_dashboard():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) c FROM posts").fetchone()["c"]
    conn.close()
    return render_page("แดชบอร์ด", DASHBOARD_BODY, post_count=count)


@app.route(ADMIN_ROUTE + "/profile", methods=["GET", "POST"])
@login_required
def admin_profile():
    conn = get_db()
    if request.method == "POST":
        site_title = request.form["site_title"].strip()
        owner_name = request.form["owner_name"].strip()
        bio = request.form["bio"].strip()
        avatar_file = request.files.get("avatar")
        new_avatar = save_upload(avatar_file)
        if new_avatar:
            conn.execute(
                "UPDATE site_info SET site_title=?, owner_name=?, bio=?, avatar=? WHERE id=1",
                (site_title, owner_name, bio, new_avatar)
            )
        else:
            conn.execute(
                "UPDATE site_info SET site_title=?, owner_name=?, bio=? WHERE id=1",
                (site_title, owner_name, bio)
            )
        conn.commit()
        conn.close()
        flash("บันทึกคำแนะนำตัวแล้ว", "ok")
        return redirect(url_for("admin_dashboard"))
    info = conn.execute("SELECT * FROM site_info WHERE id=1").fetchone()
    conn.close()
    return render_page("แก้ไขคำแนะนำตัว", PROFILE_FORM_BODY, info=info)


@app.route(ADMIN_ROUTE + "/posts")
@login_required
def admin_posts():
    conn = get_db()
    posts = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    conn.close()
    return render_page("จัดการกระทู้", POSTS_MANAGE_BODY, posts=posts)


@app.route(ADMIN_ROUTE + "/posts/new", methods=["GET", "POST"])
@login_required
def admin_new_post():
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        image = save_upload(request.files.get("image"))
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = get_db()
        conn.execute(
            "INSERT INTO posts (title, content, image, created_at, updated_at) VALUES (?,?,?,?,?)",
            (title, content, image, now, now)
        )
        conn.commit()
        conn.close()
        flash("เพิ่มกระทู้แล้ว", "ok")
        return redirect(url_for("admin_posts"))
    return render_page("เพิ่มกระทู้ใหม่", POST_FORM_BODY, post=None)


@app.route(ADMIN_ROUTE + "/posts/edit/<int:post_id>", methods=["GET", "POST"])
@login_required
def admin_edit_post(post_id):
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    if not post:
        conn.close()
        abort(404)
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        new_image = save_upload(request.files.get("image"))
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if new_image:
            conn.execute(
                "UPDATE posts SET title=?, content=?, image=?, updated_at=? WHERE id=?",
                (title, content, new_image, now, post_id)
            )
        else:
            conn.execute(
                "UPDATE posts SET title=?, content=?, updated_at=? WHERE id=?",
                (title, content, now, post_id)
            )
        conn.commit()
        conn.close()
        flash("แก้ไขกระทู้แล้ว", "ok")
        return redirect(url_for("admin_posts"))
    conn.close()
    return render_page("แก้ไขกระทู้", POST_FORM_BODY, post=post)


@app.route(ADMIN_ROUTE + "/posts/delete/<int:post_id>", methods=["POST"])
@login_required
def admin_delete_post(post_id):
    conn = get_db()
    conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    flash("ลบกระทู้แล้ว", "ok")
    return redirect(url_for("admin_posts"))


@app.route(ADMIN_ROUTE + "/change_password", methods=["GET", "POST"])
@login_required
def admin_change_password():
    if request.method == "POST":
        old = request.form["old_password"]
        new = request.form["new_password"]
        conn = get_db()
        row = conn.execute("SELECT * FROM admin WHERE id=1").fetchone()
        if not check_password_hash(row["password_hash"], old):
            conn.close()
            flash("รหัสผ่านเดิมไม่ถูกต้อง", "err")
            return redirect(url_for("admin_change_password"))
        conn.execute(
            "UPDATE admin SET password_hash=? WHERE id=1",
            (generate_password_hash(new),)
        )
        conn.commit()
        conn.close()
        flash("เปลี่ยนรหัสผ่านสำเร็จ", "ok")
        return redirect(url_for("admin_dashboard"))
    return render_page("เปลี่ยนรหัสผ่าน", CHANGE_PASSWORD_BODY)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=False)
