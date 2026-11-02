import os
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "adminpwd"),
        database=os.environ.get("DB_NAME", "student_db"),
    )

def run_query(sql, params=(), one=False):
    """SELECT: returns one row (dict) or a list of rows."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close()
        conn.close()

def run_execute(sql, params=()):
    """INSERT / UPDATE / DELETE: commits the change."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
    finally:
        cur.close()
        conn.close()