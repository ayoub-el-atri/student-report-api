from flask import Flask, request

app = Flask(__name__)

students=[
    {
        "id": 1,
        "Fname": "Ali",
        "Lname": "Mastouri",
        "reports":[
            {
                "Title": "Bla blab",
                "Type": "Mini Senior Project"
            }
        ]

    }
]


@app.get("/student") #return all students inside your list
def get_students():
    return {"students": students}

@app.post("/student") #add a new student to your list
def add_student():
    request_data = request.get_json()
    new_student = {
        "id": len(students) + 1,
        "Fname": request_data.get("Fname"),
        "Lname": request_data.get("Lname"),
        "reports": request_data.get("reports", [])
    }
    students.append(new_student)
    return {"message": "Student added successfully", "student": new_student}, 201

@app.post("/student/<int:student_id>/report")
def add_report(student_id):
    request_data = request.get_json()
    student = next((s for s in students if s["id"] == student_id),  None)
    if not student:
        return {"message": "Student not found"}, 404
    new_report = {
        "Title": request_data["Title"],
        "Type": request_data["Type"]
    }
    student["reports"].append(new_report)
    return new_report, 201

@app.post("/student/<int:student_id>")
def get_student_by_id(student_id):
    student = next((s for s in students if s["id"] == student_id), None)
    if student is None:
         return {"message": "Student not found"}, 404
    return student, 200