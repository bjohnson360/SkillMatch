from flask import Flask
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=getenv("DB_PASSWORD"),
        database="skillmatch"
    )

@app.route("/")
def home():
    return """
    <h1>SkillMatch Pro</h1>
    <ul>
        <li><a href='/users'>Users</a></li>
        <li><a href='/projects'>Projects</a></li>
        <li><a href='/applications'>Applications</a></li>
    </ul>
    """

@app.route("/users")
def users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users")
    rows = cursor.fetchall()
    conn.close()

    return "<br>".join([str(row) for row in rows])

@app.route("/projects")
def projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Project")
    rows = cursor.fetchall()
    conn.close()

    return "<br>".join([str(row) for row in rows])

@app.route("/applications")
def applications():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT U.name, P.title, A.status, A.application_date
        FROM Application A
        JOIN Users U ON A.user_id = U.user_id
        JOIN Project P ON A.project_id = P.project_id
    """)
    rows = cursor.fetchall()
    conn.close()

    return "<br>".join([str(row) for row in rows])

if __name__ == "__main__":
    app.run(debug=True)