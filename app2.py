import uuid
from flask import Flask, request
from flask_smorest import abort

from db2 import students, reports   # both are lists: students = [], reports = []

app = Flask(__name__)


def find_by_id(items, item_id):
    return next((item for item in items if item["id"] == item_id), None)


# ---------------- REPORTS ----------------

@app.get("/report/<string:report_id>")
def get_report(report_id):
    report = find_by_id(reports, report_id)
    if report is None:
        abort(404, message="Report not found")
    return report


@app.post("/report")
def create_report():
    report_data = request.get_json(silent=True)
    if not isinstance(report_data, dict):
        abort(400, message="Request body must be a JSON object")

    for field in ("title", "type", "student_id"):
        if field not in report_data:
            abort(400, message=f"Missing required field: {field}")

    for report in reports:
        if (report["title"] == report_data["title"]
                and report["type"] == report_data["type"]
                and report["student_id"] == report_data["student_id"]):
            abort(400, message="A report with the same title, type, and student already exists")

    report = {**report_data, "id": uuid.uuid4().hex}
    reports.append(report)
    return report, 201


@app.put("/report/<string:report_id>")
def update_report(report_id):
    report_data = request.get_json(silent=True)
    if not isinstance(report_data, dict):
        abort(400, message="Request body must be a JSON object")
    if "title" not in report_data or "type" not in report_data:
        abort(400, message="Missing required fields: title and type")

    report = find_by_id(reports, report_id)
    if report is None:
        abort(404, message="Report not found")

    report_data.pop("id", None) 
    report.update(report_data)    
    return report


@app.delete("/report/<string:report_id>")
def delete_report(report_id):
    report = find_by_id(reports, report_id)
    if report is None:
        abort(404, message="Report not found")
    reports.remove(report)
    return {"message": "Report deleted successfully"}


@app.get("/report")
def get_all_reports():
    return {"reports": reports}



# ---------------- STUDENTS ----------------

@app.get("/student/<string:student_id>")
def get_student(student_id):
    student = find_by_id(students, student_id)
    if student is None:
        abort(404, message="Student not found")
    return student


@app.post("/student")
def add_student():
    student_data = request.get_json(silent=True)
    if not isinstance(student_data, dict):
        abort(400, message="Request body must be a JSON object")

    if "fname" not in student_data or "lname" not in student_data:
        abort(400, message="Missing required fields: fname and lname")

    for student in students:
        if (student["fname"] == student_data["fname"]
                and student["lname"] == student_data["lname"]):
            abort(400, message="Student with the same name already exists")

    student = {**student_data, "id": uuid.uuid4().hex}
    students.append(student)
    return student, 201


@app.get("/student")
def get_students():
    return {"students": students}