"""
PawAlert — Street Animal Help Platform
Backend API (Flask + MongoDB)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import bcrypt
import jwt as pyjwt
import datetime
import os
import random
from functools import wraps
from dotenv import load_dotenv
from notifications import send_email, send_sms

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── CONFIG ────────────────────────────────────────────────────────────
SECRET_KEY     = os.environ.get("SECRET_KEY",      "pawalert-super-secret-key-2025")
MONGO_URI      = os.environ.get("MONGO_URI",       "mongodb://localhost:27017/")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME",  "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD",  "Admin@123")

# ── DATABASE ──────────────────────────────────────────────────────────
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["pawalert"]
    print("✅  MongoDB connected — database: pawalert")
except Exception as exc:
    print(f"❌  MongoDB connection failed: {exc}")
    print("    Make sure MongoDB is running on localhost:27017")
    exit(1)

users_col      = db.users
reports_col    = db.reports
volunteers_col = db.volunteers

# ── SERIALISER ────────────────────────────────────────────────────────
def to_json(doc):
    """Convert a MongoDB document to a JSON-safe dict."""
    if not doc:
        return None
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime.datetime):
            out[k] = v.strftime("%d %b %Y, %I:%M %p")
        elif isinstance(v, bytes):
            out[k] = v.decode("latin-1")   # bcrypt hash storage
        else:
            out[k] = v
    return out

def api_response(data=None, error=None, message=None, status=200):
    payload = {}
    if data    is not None: payload["data"]    = data
    if error   is not None: payload["error"]   = error
    if message is not None: payload["message"] = message
    return jsonify(payload), status

# ── AUTH DECORATORS ───────────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        raw   = request.headers.get("Authorization", "")
        token = raw.replace("Bearer ", "").strip()
        if not token:
            return api_response(error="Authentication required", status=401)
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.current_user = payload
        except pyjwt.ExpiredSignatureError:
            return api_response(error="Session expired — please log in again", status=401)
        except pyjwt.InvalidTokenError:
            return api_response(error="Invalid token — please log in again", status=401)
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        raw   = request.headers.get("Authorization", "")
        token = raw.replace("Bearer ", "").strip()
        if not token:
            return api_response(error="Admin authentication required", status=401)
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            if not payload.get("is_admin"):
                return api_response(error="Admin privileges required", status=403)
            request.current_user = payload
        except pyjwt.InvalidTokenError:
            return api_response(error="Invalid admin token", status=401)
        return f(*args, **kwargs)
    return wrapper

# ── VALIDATION HELPERS ────────────────────────────────────────────────
def validate_phone(phone: str) -> str | None:
    """Return an error string, or None if valid."""
    if not phone:
        return "Phone number is required"
    if not phone.isdigit():
        return "Phone number must contain digits only"
    if len(phone) != 10:
        return f"Phone number must be exactly 10 digits (got {len(phone)})"
    return None

def validate_password(pw: str) -> str | None:
    if len(pw) < 6:
        return "Password must be at least 6 characters"
    return None

# ══════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "api": "PawAlert v1.0",
                    "db": "connected"})

# ══════════════════════════════════════════════════════════════════════
#  AUTH — REGISTER
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/auth/register", methods=["POST"])
def register():
    body     = request.get_json(silent=True) or {}
    name     = body.get("name",     "").strip()
    phone    = body.get("phone",    "").strip()
    email    = body.get("email",    "").strip().lower()
    password = body.get("password", "")

    # Field presence
    missing = [f for f, v in [("name", name), ("phone", phone),
                               ("email", email), ("password", password)] if not v]
    if missing:
        return api_response(error=f"Missing fields: {', '.join(missing)}", status=400)

    # Phone
    err = validate_phone(phone)
    if err:
        return api_response(error=err, status=400)

    # Email (basic)
    if "@" not in email or "." not in email.split("@")[-1]:
        return api_response(error="Please enter a valid email address", status=400)

    # Password
    err = validate_password(password)
    if err:
        return api_response(error=err, status=400)

    # Duplicate checks
    if users_col.find_one({"phone": phone}):
        return api_response(error="An account with this phone number already exists", status=409)
    if users_col.find_one({"email": email}):
        return api_response(error="An account with this email already exists", status=409)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    doc    = {"name": name, "phone": phone, "email": email,
              "password": hashed, "created_at": datetime.datetime.utcnow()}
    uid    = users_col.insert_one(doc).inserted_id

    token = pyjwt.encode(
        {"user_id": str(uid), "name": name, "phone": phone,
         "email": email, "is_admin": False,
         "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        SECRET_KEY, algorithm="HS256"
    )
    
    # Notify user asynchronously-ish
    send_email(email, "Welcome to PawAlert! 🐾", f"Hi {name},\n\nThank you for joining PawAlert! You can now report injured street animals to seek quick help.")
    send_sms(phone, f"PawAlert: Hi {name}, welcome! Ensure your location is active when reporting an animal emergency.")

    return api_response(
        data={"token": token, "name": name, "phone": phone, "email": email},
        message="Account created successfully!", status=201
    )

# ══════════════════════════════════════════════════════════════════════
#  AUTH — LOGIN
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/auth/login", methods=["POST"])
def login():
    body     = request.get_json(silent=True) or {}
    phone    = body.get("phone",    "").strip()
    password = body.get("password", "")

    if not phone or not password:
        return api_response(error="Phone number and password are required", status=400)

    err = validate_phone(phone)
    if err:
        return api_response(error=err, status=400)

    user = users_col.find_one({"phone": phone})
    if not user:
        return api_response(error="No account found with this phone number", status=404)
    if not bcrypt.checkpw(password.encode(), user["password"]):
        return api_response(error="Incorrect password", status=401)

    token = pyjwt.encode(
        {"user_id": str(user["_id"]), "name": user["name"],
         "phone": user["phone"], "email": user.get("email", ""),
         "is_admin": False,
         "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        SECRET_KEY, algorithm="HS256"
    )
    
    user_email = user.get("email", "")
    if user_email:
        send_email(user_email, "PawAlert - New Login Detected", f"Hi {user['name']},\n\nA new login to your PawAlert account was just detected.")
    send_sms(user["phone"], f"PawAlert: You have successfully logged in. Let's save some animals today!")

    return api_response(data={"token": token, "name": user["name"],
                               "phone": user["phone"], "email": user.get("email", "")})

# ══════════════════════════════════════════════════════════════════════
#  AUTH — DIRECT PASSWORD RESET
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    body = request.get_json(silent=True) or {}
    phone = body.get("phone", "").strip()
    new_password = body.get("new_password", "")
    
    if not phone or not new_password:
        return api_response(error="Phone and New Password are required", status=400)
        
    err = validate_password(new_password)
    if err:
        return api_response(error=err, status=400)
        
    user = users_col.find_one({"phone": phone})
    if not user:
        return api_response(error="Account not found", status=404)
        
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    
    users_col.update_one({"_id": user["_id"]}, {"$set": {"password": hashed}})
    
    return api_response(message="Password reset successfully")

# ══════════════════════════════════════════════════════════════════════
#  AUTH — ADMIN LOGIN
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/auth/admin-login", methods=["POST"])
def admin_login():
    body     = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return api_response(error="Username and password are required", status=400)
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return api_response(error="Invalid admin credentials", status=401)

    token = pyjwt.encode(
        {"username": username, "is_admin": True,
         "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)},
        SECRET_KEY, algorithm="HS256"
    )
    return api_response(data={"token": token, "username": username},
                        message="Admin login successful")

# ══════════════════════════════════════════════════════════════════════
#  REPORTS — GET ALL
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/reports", methods=["GET"])
def get_reports():
    status = request.args.get("status", "")
    query  = {"status": status} if status and status != "all" else {}
    docs   = [to_json(r) for r in reports_col.find(query).sort("created_at", -1)]
    return jsonify(docs)

# ══════════════════════════════════════════════════════════════════════
#  REPORTS — CREATE
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/reports", methods=["POST"])
@token_required
def create_report():
    body     = request.get_json(silent=True) or {}
    name     = body.get("name",     "").strip()
    phone    = body.get("phone",    "").strip()
    location = body.get("location", "").strip()
    animal   = body.get("animal",   "").strip()
    desc     = body.get("desc",     "").strip()
    photo    = body.get("photo",    "")   # base64 string (optional)

    missing = [f for f, v in [("name", name), ("phone", phone),
                               ("location", location), ("animal", animal),
                               ("description", desc)] if not v]
    if missing:
        return api_response(error=f"Missing: {', '.join(missing)}", status=400)

    err = validate_phone(phone)
    if err:
        return api_response(error=err, status=400)

    valid_animals = {"Dog", "Cat", "Cow", "Bird", "Other"}
    if animal not in valid_animals:
        return api_response(error=f"Animal must be one of: {', '.join(valid_animals)}", status=400)

    emoji_map = {"Dog": "🐶", "Cat": "🐱", "Cow": "🐄", "Bird": "🐦", "Other": "🐾"}
    count     = reports_col.count_documents({})
    case_id   = f"PA-{str(count + 1).zfill(4)}"

    doc = {
        "case_id":    case_id,
        "animal":     animal,
        "emoji":      emoji_map[animal],
        "location":   location,
        "reporter":   name,
        "phone":      phone,
        "desc":       desc,
        "photo":      photo,
        "status":     "Pending",
        "assigned":   "",
        "user_id":    request.current_user.get("user_id", ""),
        "created_at": datetime.datetime.utcnow(),
    }
    rid = reports_col.insert_one(doc).inserted_id
    doc["_id"] = str(rid)
    return api_response(data=to_json(doc),
                        message=f"Report {case_id} submitted! Volunteers are being notified.",
                        status=201)

# ══════════════════════════════════════════════════════════════════════
#  REPORTS — UPDATE (admin only)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/reports/<rid>", methods=["PUT"])
@admin_required
def update_report(rid):
    try:
        body   = request.get_json(silent=True) or {}
        update = {k: body[k] for k in ("status", "assigned") if k in body}
        if not update:
            return api_response(error="Nothing to update", status=400)
        res = reports_col.update_one({"_id": ObjectId(rid)}, {"$set": update})
        if res.matched_count == 0:
            return api_response(error="Report not found", status=404)
        return api_response(message="Report updated successfully")
    except InvalidId:
        return api_response(error="Invalid report ID", status=400)

# ══════════════════════════════════════════════════════════════════════
#  REPORTS — DELETE (admin only)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/reports/<rid>", methods=["DELETE"])
@admin_required
def delete_report(rid):
    try:
        res = reports_col.delete_one({"_id": ObjectId(rid)})
        if res.deleted_count == 0:
            return api_response(error="Report not found", status=404)
        return api_response(message="Report deleted")
    except InvalidId:
        return api_response(error="Invalid report ID", status=400)

# ══════════════════════════════════════════════════════════════════════
#  MY REPORTS (logged-in user)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/my-reports", methods=["GET"])
@token_required
def my_reports():
    uid  = request.current_user.get("user_id", "")
    docs = [to_json(r) for r in reports_col.find({"user_id": uid}).sort("created_at", -1)]
    return jsonify(docs)

# ══════════════════════════════════════════════════════════════════════
#  VOLUNTEERS — GET ALL
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/volunteers", methods=["GET"])
def get_volunteers():
    docs = [to_json(v) for v in volunteers_col.find().sort("created_at", -1)]
    return jsonify(docs)

# ══════════════════════════════════════════════════════════════════════
#  VOLUNTEERS — REGISTER
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/volunteers", methods=["POST"])
def register_volunteer():
    body      = request.get_json(silent=True) or {}
    name      = body.get("name",      "").strip()
    phone     = body.get("phone",     "").strip()
    area      = body.get("area",      "").strip()
    help_type = body.get("help_type", "").strip()
    email     = body.get("email",     "").strip()

    missing = [f for f, v in [("name", name), ("phone", phone),
                               ("area", area), ("help type", help_type)] if not v]
    if missing:
        return api_response(error=f"Missing: {', '.join(missing)}", status=400)

    err = validate_phone(phone)
    if err:
        return api_response(error=err, status=400)

    valid_types = {"Rescue", "Medical", "Food"}
    if help_type not in valid_types:
        return api_response(error=f"Help type must be one of: {', '.join(valid_types)}", status=400)

    if volunteers_col.find_one({"phone": phone}):
        return api_response(error="A volunteer with this phone number already exists", status=409)

    doc = {"name": name, "phone": phone, "area": area,
           "help_type": help_type, "email": email, "status": "Active",
           "created_at": datetime.datetime.utcnow()}
    vid = volunteers_col.insert_one(doc).inserted_id
    doc["_id"] = str(vid)
    
    if email:
        send_email(email, "Volunteer Registration Confirmed", f"Hi {name},\n\nThank you for volunteering to provide {help_type} help in {area}. You are a hero!")
    send_sms(phone, f"PawAlert Volunteer: Hi {name}! You're registered. We'll alert you for {help_type} cases in {area}.")

    return api_response(data=to_json(doc), message="Registered as volunteer!", status=201)

# ══════════════════════════════════════════════════════════════════════
#  VOLUNTEERS — DELETE (admin only)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/volunteers/<vid>", methods=["DELETE"])
@admin_required
def delete_volunteer(vid):
    try:
        res = volunteers_col.delete_one({"_id": ObjectId(vid)})
        if res.deleted_count == 0:
            return api_response(error="Volunteer not found", status=404)
        return api_response(message="Volunteer removed")
    except InvalidId:
        return api_response(error="Invalid volunteer ID", status=400)

# ══════════════════════════════════════════════════════════════════════
#  USERS — GET ALL (admin only)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    docs = [to_json(u) for u in users_col.find().sort("created_at", -1)]
    # Strip hashed passwords from payload
    for doc in docs:
        doc.pop("password", None)
    return jsonify(docs)

# ══════════════════════════════════════════════════════════════════════
#  ADMIN — STATS
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    return jsonify({
        "total_reports": reports_col.count_documents({}),
        "pending":       reports_col.count_documents({"status": "Pending"}),
        "in_progress":   reports_col.count_documents({"status": "In Progress"}),
        "resolved":      reports_col.count_documents({"status": "Resolved"}),
        "volunteers":    volunteers_col.count_documents({}),
        "users":         users_col.count_documents({}),
    })

# ══════════════════════════════════════════════════════════════════════
#  AI CHATBOT (Rule-based mockup)
# ══════════════════════════════════════════════════════════════════════
@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "").lower().strip()
    
    if not message:
        return api_response(error="Message cannot be empty", status=400)
    
    reply = "I am the PawAlert AI Assistant. I can help you understand how to report animals, register as a volunteer, or provide emergency contacts."
    
    if "hello" in message or "hi " in message or message == "hi":
        reply = "Hello! 🐾 How can I assist you with PawAlert today?"
    elif "report" in message or "injured" in message:
        reply = "To report an injured animal, click on 'Report' in the navigation bar. Provide the animal's location, type, and ideally a photo. Nearby volunteers will be alerted!"
    elif "volunteer" in message or "join" in message:
        reply = "You can become a volunteer by clicking 'Volunteer' in the top menu. You'll receive instant SMS alerts when an animal needs help in your designated area."
    elif "contact" in message or "emergency" in message:
        reply = "For immediate emergency rescue assistance, please check our emergency helplines on the main page (e.g. Animal Welfare Board: 1800-180-5236)."
    elif "map" in message or "location" in message:
        reply = "You can view active rescue cases on our Live Rescue Map on the Dashboard or Home page."
        
    return api_response(data={"reply": reply})

# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "═" * 50)
    print("  🐾  PawAlert API Server")
    print("═" * 50)
    print(f"  URL    : http://localhost:5000")
    print(f"  Health : http://localhost:5000/api/health")
    print(f"  Admin  : {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print("═" * 50 + "\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
