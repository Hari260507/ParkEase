from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, csv, io
from flask import make_response
from datetime import datetime, timezone
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parkease.db")
app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = os.environ.get("PARKEASE_SECRET_KEY", "change-this-demo-secret-before-deployment")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT NOT NULL,
          vehicle TEXT NOT NULL, vehicle_type TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookings (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          slot TEXT NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL, vehicle TEXT NOT NULL,
          date TEXT NOT NULL, time TEXT NOT NULL, duration INTEGER NOT NULL,
          start_time TEXT NOT NULL, end_time TEXT NOT NULL, created_at TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Active'
        );
        CREATE INDEX IF NOT EXISTS idx_bookings_slot_time ON bookings(slot, start_time, end_time);
        CREATE TABLE IF NOT EXISTS sms_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          phone TEXT NOT NULL, message TEXT NOT NULL, type TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def user_dict(row):
    return {"id": row["id"], "name": row["name"], "address": row["address"],
            "vehicle": row["vehicle"], "type": row["vehicle_type"], "phone": row["phone"]}

def booking_dict(row):
    data = {k: row[k] for k in ["id","slot","name","phone","vehicle","date","time","duration",
                                 "start_time","end_time","created_at","status"]}
    # Slot prefixes identify the fixed place: M1-M5 are malls, C1-C6 are cinemas.
    place_id = str(row["slot"]).split("-", 1)[0]
    place = next((p for p in FIXED_PLACES if p["id"] == place_id), None)
    data["place_id"] = place_id if place else ""
    data["place_type"] = place["type"] if place else "Unknown"
    data["place_name"] = place["name"] if place else "Location unavailable"
    data["place_address"] = place["address"] if place else "Location unavailable"
    return data

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error":"Please login first."}), 401
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin login required."}), 401
        return fn(*args, **kwargs)
    return wrapped

@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.get("/<path:path>")
def static_pages(path):
    # Never serve database or source configuration files as public static files.
    if path.endswith((".py", ".db")) or path in ("requirements.txt",):
        return "Not found", 404
    return send_from_directory(BASE_DIR, path)

@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    name, address = str(d.get("name","")).strip(), str(d.get("address","")).strip()
    vehicle = str(d.get("vehicle","")).strip().upper()
    vtype, phone, password = str(d.get("type","")).strip(), str(d.get("phone","")).strip(), str(d.get("password",""))
    if not all([name,address,vehicle,vtype,phone,password]):
        return jsonify(error="Please fill all the details."), 400
    if not __import__("re").fullmatch(r"[6-9][0-9]{9}", phone):
        return jsonify(error="Enter a valid 10-digit mobile number."), 400
    if len(password) < 6:
        return jsonify(error="Password must contain at least 6 characters."), 400
    try:
        with db() as c:
            c.execute("INSERT INTO users(name,address,vehicle,vehicle_type,phone,password_hash,created_at) VALUES(?,?,?,?,?,?,?)",
                      (name,address,vehicle,vtype,phone,generate_password_hash(password),now_iso()))
    except sqlite3.IntegrityError:
        return jsonify(error="This phone number is already registered. Please login."), 409
    return jsonify(message="Account created successfully.")

@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE phone=?", (str(d.get("phone","")).strip(),)).fetchone()
    if not row or not check_password_hash(row["password_hash"], str(d.get("password",""))):
        return jsonify(error="Incorrect mobile number or password."), 401
    session.clear()
    session["user_id"] = row["id"]
    return jsonify(user=user_dict(row))

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(message="Logged out.")

@app.get("/api/me")
@login_required
def me():
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not row:
        session.clear()
        return jsonify(error="Please login again."), 401
    return jsonify(user=user_dict(row))

@app.put("/api/profile")
@login_required
def update_profile():
    d = request.get_json(silent=True) or {}
    name, address = str(d.get("name","")).strip(), str(d.get("address","")).strip()
    vehicle, vtype = str(d.get("vehicle","")).strip().upper(), str(d.get("type","")).strip()
    password = str(d.get("password",""))
    if not all([name,address,vehicle,vtype]):
        return jsonify(error="Please fill all details."), 400
    if password and len(password) < 6:
        return jsonify(error="New password must contain at least 6 characters."), 400
    with db() as c:
        if password:
            c.execute("UPDATE users SET name=?,address=?,vehicle=?,vehicle_type=?,password_hash=? WHERE id=?",
                      (name,address,vehicle,vtype,generate_password_hash(password),session["user_id"]))
        else:
            c.execute("UPDATE users SET name=?,address=?,vehicle=?,vehicle_type=? WHERE id=?",
                      (name,address,vehicle,vtype,session["user_id"]))
        row = c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return jsonify(user=user_dict(row))


FIXED_PLACES = [
 {"id":"M1","type":"Mall","name":"Phoenix Marketcity","address":"Velachery Main Road, Velachery, Chennai"},
 {"id":"M2","type":"Mall","name":"Express Avenue Mall","address":"Whites Road, Royapettah, Chennai"},
 {"id":"M3","type":"Mall","name":"VR Chennai","address":"Jawaharlal Nehru Road, Anna Nagar, Chennai"},
 {"id":"M4","type":"Mall","name":"Forum Vijaya Mall","address":"Vadapalani, Chennai"},
 {"id":"M5","type":"Mall","name":"Ampa Skywalk","address":"Poonamallee High Road, Aminjikarai, Chennai"},
 {"id":"C1","type":"Cinema","name":"Sathyam Cinemas","address":"Royapettah, Chennai"},
 {"id":"C2","type":"Cinema","name":"PVR Escape","address":"Express Avenue, Royapettah, Chennai"},
 {"id":"C3","type":"Cinema","name":"INOX National","address":"Arcot Road, Virugambakkam, Chennai"},
 {"id":"C4","type":"Cinema","name":"AGS Cinemas T. Nagar","address":"Ranganathan Street area, T. Nagar, Chennai"},
 {"id":"C5","type":"Cinema","name":"Rohini Silver Screens","address":"Koyambedu, Chennai"},
 {"id":"C6","type":"Cinema","name":"PVR Grand Mall","address":"Velachery, Chennai"},
]

@app.get("/api/places")
def get_places():
    return jsonify(places=[dict(p, car_slots=40, bike_slots=60) for p in FIXED_PLACES])

@app.get("/api/slots")
@login_required
def slots():
    now = datetime.now(timezone.utc).isoformat()
    with db() as c:
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (now,))
        rows = c.execute("SELECT * FROM bookings WHERE status='Active' AND end_time>? ORDER BY start_time", (now,)).fetchall()
    active = [booking_dict(r) for r in rows]
    return jsonify(bookings=active)

@app.get("/api/bookings")
@login_required
def bookings():
    with db() as c:
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (datetime.now(timezone.utc).isoformat(),))
        rows = c.execute("SELECT * FROM bookings WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    return jsonify(bookings=[booking_dict(r) for r in rows])

@app.post("/api/bookings")
@login_required
def create_booking():
    d = request.get_json(silent=True) or {}
    slot = str(d.get("slot",""))
    vehicle = str(d.get("vehicle","")).strip().upper()
    date, time = str(d.get("date","")), str(d.get("time",""))
    try:
        duration = int(d.get("duration", 0))
        start = datetime.fromisoformat(date + "T" + time).astimezone()
    except (ValueError, TypeError):
        return jsonify(error="Enter a valid date, time and duration."), 400
    if not __import__("re").fullmatch(r"(?:M[1-5]|C[1-6])-([AB])(?:[1-9]|[1-9][0-9]|100)", slot):
        return jsonify(error="Please select a valid parking slot."), 400
    if not __import__("re").fullmatch(r"[A-Z0-9 -]{3,20}", vehicle):
        return jsonify(error="Please enter a valid vehicle number."), 400
    if duration < 1 or duration > 1440:
        return jsonify(error="Parking duration must be between 1 minute and 24 hours."), 400
    if start <= datetime.now().astimezone():
        return jsonify(error="Please select a future date and time."), 400
    end = start.fromtimestamp(start.timestamp() + duration * 60, start.tzinfo)
    start_iso, end_iso = start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (datetime.now(timezone.utc).isoformat(),))
        overlap = c.execute("""SELECT id FROM bookings WHERE slot=? AND status='Active'
            AND start_time < ? AND end_time > ?""", (slot,end_iso,start_iso)).fetchone()
        if overlap:
            return jsonify(error="Sorry! This slot is already booked for that time."), 409
        cur = c.execute("""INSERT INTO bookings(user_id,slot,name,phone,vehicle,date,time,duration,start_time,end_time,created_at,status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,'Active')""",
            (session["user_id"],slot,user["name"],user["phone"],vehicle,date,time,duration,start_iso,end_iso,now_iso()))
        c.execute("UPDATE users SET vehicle=? WHERE id=?", (vehicle,session["user_id"]))
        msg = f"ParkEase: Booking confirmed! Slot: {slot}, Vehicle: {vehicle}, Date: {date}, Time: {time}."
        c.execute("INSERT INTO sms_history(user_id,phone,message,type,created_at) VALUES(?,?,?,?,?)",
                  (session["user_id"],user["phone"],msg,"Booking Confirmation",now_iso()))
        row = c.execute("SELECT * FROM bookings WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(booking=booking_dict(row)), 201

@app.post("/api/bookings/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    with db() as c:
        cur = c.execute("UPDATE bookings SET status='Cancelled' WHERE id=? AND user_id=? AND status='Active'",
                        (booking_id,session["user_id"]))
        if cur.rowcount == 0:
            return jsonify(error="Active booking not found."), 404
        row = c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    return jsonify(booking=booking_dict(row))

@app.get("/api/sms")
@login_required
def sms_history():
    with db() as c:
        rows = c.execute("SELECT * FROM sms_history WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    return jsonify(messages=[dict(r) for r in rows])

@app.delete("/api/sms")
@login_required
def clear_sms():
    with db() as c:
        c.execute("DELETE FROM sms_history WHERE user_id=?", (session["user_id"],))
    return jsonify(message="SMS history cleared.")

@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    expected_username = os.environ.get("PARKEASE_ADMIN_USERNAME", "admin")
    expected_password = os.environ.get("PARKEASE_ADMIN_PASSWORD", "ParkEase@123")
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if username != expected_username or password != expected_password:
        return jsonify(error="Incorrect admin username or password."), 401
    session.clear()
    session["is_admin"] = True
    session["admin_username"] = username
    return jsonify(message="Admin login successful.", username=username)


@app.post("/api/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return jsonify(message="Admin logged out.")


@app.get("/api/admin/summary")
@admin_required
def admin_summary():
    current_time = datetime.now(timezone.utc).isoformat()
    with db() as c:
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (current_time,))
        users_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_count = c.execute("SELECT COUNT(*) FROM bookings WHERE status='Active'").fetchone()[0]
        completed_count = c.execute("SELECT COUNT(*) FROM bookings WHERE status='Completed'").fetchone()[0]
        cancelled_count = c.execute("SELECT COUNT(*) FROM bookings WHERE status='Cancelled'").fetchone()[0]
        occupied_count = c.execute("SELECT COUNT(DISTINCT slot) FROM bookings WHERE status='Active' AND start_time<=? AND end_time>?", (current_time, current_time)).fetchone()[0]
    return jsonify({
        "users": users_count,
        "active_bookings": active_count,
        "completed_bookings": completed_count,
        "cancelled_bookings": cancelled_count,
        "occupied_slots": occupied_count,
        "available_slots": max(0, 100 - occupied_count),
        "total_slots": 100
    })


@app.get("/api/admin/bookings")
@admin_required
def admin_bookings():
    with db() as c:
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (datetime.now(timezone.utc).isoformat(),))
        rows = c.execute("""SELECT b.*, u.address AS user_address FROM bookings b
            JOIN users u ON u.id=b.user_id ORDER BY b.created_at DESC LIMIT 200""").fetchall()
    return jsonify(bookings=[dict(r) for r in rows])


@app.get("/api/admin/users")
@admin_required
def admin_users():
    with db() as c:
        rows = c.execute("""SELECT u.id, u.name, u.address, u.vehicle, u.vehicle_type,
            u.phone, u.created_at, COUNT(b.id) AS booking_count
            FROM users u LEFT JOIN bookings b ON b.user_id=u.id
            GROUP BY u.id ORDER BY u.created_at DESC LIMIT 200""").fetchall()
    return jsonify(users=[dict(r) for r in rows])


def csv_response(filename, headers, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        safe_row = []
        for value in row:
            value = "" if value is None else str(value)
            # Prevent spreadsheet formula execution when opening exported data.
            if value.startswith(("=", "+", "-", "@", "\t", "\r")):
                value = "'" + value
            safe_row.append(value)
        writer.writerow(safe_row)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/admin/export/bookings.csv")
@admin_required
def export_bookings_csv():
    current_time = datetime.now(timezone.utc).isoformat()
    with db() as c:
        c.execute("UPDATE bookings SET status='Completed' WHERE status='Active' AND end_time<=?", (current_time,))
        rows = c.execute("""SELECT b.id, b.name, b.phone, b.slot, b.vehicle, b.date, b.time,
            b.duration, b.status, b.start_time, b.end_time, b.created_at, u.address
            FROM bookings b JOIN users u ON u.id=b.user_id ORDER BY b.created_at DESC""").fetchall()
    headers = ["Booking ID", "Name", "Phone", "Slot", "Vehicle", "Date", "Time",
               "Duration (minutes)", "Status", "Start Time", "End Time", "Created At", "Address"]
    return csv_response("parkease_bookings.csv", headers, [[r[k] for k in [
        "id", "name", "phone", "slot", "vehicle", "date", "time", "duration", "status",
        "start_time", "end_time", "created_at", "address"]] for r in rows])


@app.get("/api/admin/export/users.csv")
@admin_required
def export_users_csv():
    with db() as c:
        rows = c.execute("""SELECT u.id, u.name, u.phone, u.address, u.vehicle, u.vehicle_type,
            u.created_at, COUNT(b.id) AS booking_count
            FROM users u LEFT JOIN bookings b ON b.user_id=u.id
            GROUP BY u.id ORDER BY u.created_at DESC""").fetchall()
    headers = ["User ID", "Name", "Phone", "Address", "Vehicle", "Vehicle Type", "Registered At", "Booking Count"]
    return csv_response("parkease_users.csv", headers, [[r[k] for k in [
        "id", "name", "phone", "address", "vehicle", "vehicle_type", "created_at", "booking_count"]] for r in rows])


if __name__ == "__main__":
    init_db()
    print("ParkEase backend running at http://127.0.0.1:5000")
    app.run(debug=True)
