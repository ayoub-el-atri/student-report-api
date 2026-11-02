from flask import Flask, jsonify, request
from functools import wraps
import jwt, datetime, uuid
import mysql.connector
from db import run_query, run_execute

app = Flask(__name__)
SECRET_KEY = "token-key"

USERS = {"admin": "adminpwd"}


def is_valid_uuid(value):
    try:
        return str(uuid.UUID(str(value))) == str(value).lower()
    except ValueError:
        return False




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
    return jsonify(run_query("SELECT * FROM students")), 200

@app.route("/students/<id_s>", methods=["GET"])
@token_required
def get_student(id_s):
    if not is_valid_uuid(id_s):
        return jsonify({"error": "id_s must be a valid UUID"}), 400
    student = run_query("SELECT * FROM students WHERE id_s = %s", (id_s,), one=True)
    if student is None:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student), 200

@app.route("/students", methods=["POST"])
@token_required
def add_student():
    body = request.get_json(silent=True)
    required = ["fname", "lname", "double_major", "level"]
    if not body or any(field not in body for field in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400
    if body["double_major"] not in (0, 1):
        return jsonify({"error": "double_major must be 0 or 1"}), 400

    new_id = str(uuid.uuid4())          
    run_execute(
        "INSERT INTO students (id_s, fname, lname, double_major, level) "
        "VALUES (%s, %s, %s, %s, %s)",
        (new_id, body["fname"], body["lname"], body["double_major"], body["level"]),
    )
    student = run_query("SELECT * FROM students WHERE id_s = %s", (new_id,), one=True)
    return jsonify(student), 201


REPORT_COLS = ("id_r, id_s, title, type, k1, k2, k3")

@app.route("/reports", methods=["GET"])
def get_reports():
    return jsonify(run_query(f"SELECT {REPORT_COLS} FROM reports")), 200

@app.route("/reports/<id_r>", methods=["GET"])
def get_report(id_r):
    if not is_valid_uuid(id_r):
        return jsonify({"error": "id_r must be a valid UUID"}), 400
    report = run_query(f"SELECT {REPORT_COLS} FROM reports WHERE id_r = %s", (id_r,), one=True)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

@app.route("/reports", methods=["POST"])
def add_report():
    body = request.get_json(silent=True)
    required = ["id_s", "title", "type", "k1", "k2", "k3"]
    if not body or any(field not in body for field in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400
    if not is_valid_uuid(body["id_s"]):
        return jsonify({"error": "id_s must be a valid UUID"}), 400

    student = run_query("SELECT * FROM students WHERE id_s = %s", (body["id_s"],), one=True)
    if student is None:
        return jsonify({"error": "Student does not exist"}), 404

    allowed = 2 if student["double_major"] == 1 else 1
    already = run_query("SELECT COUNT(*) AS n FROM reports WHERE id_s = %s",
                        (body["id_s"],), one=True)["n"]
    if already >= allowed:
        return jsonify({"error": f"Student already has {already} report(s); maximum is {allowed}"}), 409

    new_id = str(uuid.uuid4())          
    try:
        run_execute(
            "INSERT INTO reports (id_r, id_s, title, type, k1, k2, k3) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (new_id, body["id_s"], body["title"], body["type"],
             body["k1"], body["k2"], body["k3"]),
        )
    except mysql.connector.Error:
        return jsonify({"error": "Database error, check your data"}), 400

    report = run_query(f"SELECT {REPORT_COLS} FROM reports WHERE id_r = %s", (new_id,), one=True)
    return jsonify(report), 201

@app.route("/reports/<id_r>", methods=["PUT"])
def update_report(id_r):
    if not is_valid_uuid(id_r):
        return jsonify({"error": "id_r must be a valid UUID"}), 400

    body = request.get_json(silent=True)
    required = ["title", "type", "k1", "k2", "k3"]
    if not body or any(field not in body for field in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400

    existing = run_query("SELECT id_r FROM reports WHERE id_r = %s", (id_r,), one=True)
    if existing is None:
        return jsonify({"error": "Report not found"}), 404

    try:
        run_execute(
            "UPDATE reports SET title=%s, type=%s, k1=%s, k2=%s, k3=%s "
            "WHERE id_r=%s",
            (body["title"], body["type"], body["k1"], body["k2"],
             body["k3"], id_r),
        )
    except mysql.connector.Error:
        return jsonify({"error": "Database error, check your data"}), 400

    report = run_query(f"SELECT {REPORT_COLS} FROM reports WHERE id_r = %s", (id_r,), one=True)
    return jsonify(report), 200

@app.route("/reports/<id_r>", methods=["DELETE"])
def delete_report(id_r):
    if not is_valid_uuid(id_r):
        return jsonify({"error": "id_r must be a valid UUID"}), 400

    existing = run_query("SELECT id_r FROM reports WHERE id_r = %s", (id_r,), one=True)
    if existing is None:
        return jsonify({"error": "Report not found"}), 404

    run_execute("DELETE FROM reports WHERE id_r = %s", (id_r,))
    return jsonify({"message": f"Report {id_r} deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)