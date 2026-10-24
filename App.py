from flask import Flask, jsonify, request
from functools import wraps
import jwt, datetime

app = Flask(__name__)
SECRET_KEY = "token-key"

students = [
    {"id_s": 1, "first_name": "Amine",   "last_name": "Ben Salah", "double_major": 0, "level": "Senior"},
    {"id_s": 2, "first_name": "Amira",   "last_name": "Trabelsi",  "double_major": 1, "level": "Senior"},
    {"id_s": 3, "first_name": "Yassine", "last_name": "Mejri",     "double_major": 0, "level": "Senior"},
]

reports = [
    {"id_r": 1, "id_s": 1, "title": "Stock Price Prediction", "type": "PFE",
     "k1": "Finance", "k2": "Time Series", "k3": "Python", "release_date": "2026-06-15"},
    {"id_r": 2, "id_s": 2, "title": "Defect Recognition System", "type": "Senior Project",
     "k1": "Computer Vision", "k2": "Machine Learning", "k3": "Python", "release_date": "2026-06-20"},
]

USERS = {"admin": "adminpwd"}

def make_token(username, token_type, minutes):
    payload = {
        "sub": username,
        "type": token_type,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token is missing"}), 401
        try:
            data = jwt.decode(auth.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            if data["type"] != "access":
                return jsonify({"error": "Wrong token type"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    if USERS.get(body.get("username")) != body.get("password"):
        return jsonify({"error": "Bad credentials"}), 401
    return jsonify({
        "access_token": make_token(body["username"], "access", 5),
        "refresh_token": make_token(body["username"], "refresh", 60 * 24 * 7),
    }), 200

@app.route("/refresh", methods=["POST"])
def refresh():
    body = request.get_json(silent=True) or {}
    try:
        data = jwt.decode(body.get("refresh_token", ""), SECRET_KEY, algorithms=["HS256"])
        if data["type"] != "refresh":
            raise jwt.InvalidTokenError
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expired, log in again"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid refresh token"}), 401
    return jsonify({"access_token": make_token(data["sub"], "access", 15)}), 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Student & Reports API is running"}), 200

@app.route("/students", methods=["GET"])
@token_required
def get_students():
    return jsonify(students), 200

@app.route("/students/<int:id_s>", methods=["GET"])
@token_required
def get_student(id_s):
    student = next((s for s in students if s["id_s"] == id_s), None)
    if student is None:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student), 200

@app.route("/students", methods=["POST"])
@token_required
def add_student():
    body = request.get_json(silent=True)
    required = ["first_name", "last_name", "double_major", "level"]
    if not body or any(field not in body for field in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400
    if body["double_major"] not in (0, 1):
        return jsonify({"error": "double_major must be 0 or 1"}), 400

    new_student = {
        "id_s": max((s["id_s"] for s in students), default=0) + 1,
        "first_name": body["first_name"],
        "last_name": body["last_name"],
        "double_major": body["double_major"],
        "level": body["level"],
    }
    students.append(new_student)
    return jsonify(new_student), 201

@app.route("/reports", methods=["GET"])
def get_reports():
    return jsonify(reports), 200

@app.route("/reports/<int:id_r>", methods=["GET"])
def get_report(id_r):
    report = next((r for r in reports if r["id_r"] == id_r), None)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

@app.route("/reports", methods=["POST"])
def add_report():
    body = request.get_json(silent=True)
    required = ["id_s", "title", "type", "k1", "k2", "k3", "release_date"]
    if not body or any(field not in body for field in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400

    student = next((s for s in students if s["id_s"] == body["id_s"]), None)
    if student is None:
        return jsonify({"error": "Student does not exist"}), 404

    allowed = 2 if student["double_major"] == 1 else 1
    already = sum(1 for r in reports if r["id_s"] == student["id_s"])
    if already >= allowed:
        return jsonify({"error": f"Student already has {already} report(s); maximum is {allowed}"}), 409

    new_report = {
        "id_r": max((r["id_r"] for r in reports), default=0) + 1,
        "id_s": body["id_s"],
        "title": body["title"],
        "type": body["type"],
        "k1": body["k1"],
        "k2": body["k2"],
        "k3": body["k3"],
        "release_date": body["release_date"],
    }
    reports.append(new_report)
    return jsonify(new_report), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,debug=True)