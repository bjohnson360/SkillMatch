import os

from flask import Flask, flash, redirect, render_template, request, url_for
import mysql.connector
from mysql.connector import Error


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "skillmatch-dev-key")


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("DB_PASSWORD"),
    "database": "skillmatch",
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/users")
def users():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name, email, location, experience_level
            FROM Users
            ORDER BY user_id
            """
        )
        users_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("users/list.html", users=users_list)


@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "location": request.form.get("location", "").strip(),
            "experience_level": request.form.get("experience_level", "").strip(),
        }

        if not form_data["name"] or not form_data["email"] or not form_data["experience_level"]:
            flash("Name, email, and experience level are required.", "danger")
            return render_template(
                "users/form.html",
                title="Add User",
                heading="Add User",
                button_label="Create User",
                user=form_data,
                form_action=url_for("add_user"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Users (name, email, location, experience_level)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    form_data["name"],
                    form_data["email"],
                    form_data["location"] or None,
                    form_data["experience_level"],
                ),
            )
            connection.commit()
            flash("User added successfully.", "success")
            return redirect(url_for("users"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add user: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "users/form.html",
            title="Add User",
            heading="Add User",
            button_label="Create User",
            user=form_data,
            form_action=url_for("add_user"),
        )

    return render_template(
        "users/form.html",
        title="Add User",
        heading="Add User",
        button_label="Create User",
        user={},
        form_action=url_for("add_user"),
    )


def get_user_by_id(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name, email, location, experience_level
            FROM Users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return user


@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users"))

    if request.method == "POST":
        updated_user = {
            "user_id": user_id,
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "location": request.form.get("location", "").strip(),
            "experience_level": request.form.get("experience_level", "").strip(),
        }

        if not updated_user["name"] or not updated_user["email"] or not updated_user["experience_level"]:
            flash("Name, email, and experience level are required.", "danger")
            return render_template(
                "users/form.html",
                title="Edit User",
                heading="Edit User",
                button_label="Update User",
                user=updated_user,
                form_action=url_for("edit_user", user_id=user_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE Users
                SET name = %s, email = %s, location = %s, experience_level = %s
                WHERE user_id = %s
                """,
                (
                    updated_user["name"],
                    updated_user["email"],
                    updated_user["location"] or None,
                    updated_user["experience_level"],
                    user_id,
                ),
            )
            connection.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for("users"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not update user: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "users/form.html",
            title="Edit User",
            heading="Edit User",
            button_label="Update User",
            user=updated_user,
            form_action=url_for("edit_user", user_id=user_id),
        )

    return render_template(
        "users/form.html",
        title="Edit User",
        heading="Edit User",
        button_label="Update User",
        user=user,
        form_action=url_for("edit_user", user_id=user_id),
    )


@app.route("/users/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
        connection.commit()

        if cursor.rowcount == 0:
            flash("User not found.", "warning")
        else:
            flash("User deleted successfully.", "success")
    except Error as exc:
        connection.rollback()
        flash(f"Could not delete user: {exc.msg}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("users"))


@app.route("/projects")
def projects():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT project_id, title, description, difficulty, status
            FROM Project
            ORDER BY project_id
            """
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("projects/list.html", projects=projects_list)


@app.route("/projects/add", methods=["GET", "POST"])
def add_project():
    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
        }

        if not form_data["title"] or not form_data["difficulty"] or not form_data["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Add Project",
                heading="Add Project",
                button_label="Create Project",
                project=form_data,
                form_action=url_for("add_project"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Project (title, description, difficulty, status)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    form_data["title"],
                    form_data["description"] or None,
                    form_data["difficulty"],
                    form_data["status"],
                ),
            )
            connection.commit()
            flash("Project added successfully.", "success")
            return redirect(url_for("projects"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add project: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "projects/form.html",
            title="Add Project",
            heading="Add Project",
            button_label="Create Project",
            project=form_data,
            form_action=url_for("add_project"),
        )

    return render_template(
        "projects/form.html",
        title="Add Project",
        heading="Add Project",
        button_label="Create Project",
        project={},
        form_action=url_for("add_project"),
    )


def get_project_by_id(project_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT project_id, title, description, difficulty, status
            FROM Project
            WHERE project_id = %s
            """,
            (project_id,),
        )
        project = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return project


@app.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("projects"))

    if request.method == "POST":
        updated_project = {
            "project_id": project_id,
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
        }

        if not updated_project["title"] or not updated_project["difficulty"] or not updated_project["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Edit Project",
                heading="Edit Project",
                button_label="Update Project",
                project=updated_project,
                form_action=url_for("edit_project", project_id=project_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE Project
                SET title = %s, description = %s, difficulty = %s, status = %s
                WHERE project_id = %s
                """,
                (
                    updated_project["title"],
                    updated_project["description"] or None,
                    updated_project["difficulty"],
                    updated_project["status"],
                    project_id,
                ),
            )
            connection.commit()
            flash("Project updated successfully.", "success")
            return redirect(url_for("projects"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not update project: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "projects/form.html",
            title="Edit Project",
            heading="Edit Project",
            button_label="Update Project",
            project=updated_project,
            form_action=url_for("edit_project", project_id=project_id),
        )

    return render_template(
        "projects/form.html",
        title="Edit Project",
        heading="Edit Project",
        button_label="Update Project",
        project=project,
        form_action=url_for("edit_project", project_id=project_id),
    )


@app.route("/projects/delete/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Project WHERE project_id = %s", (project_id,))
        connection.commit()

        if cursor.rowcount == 0:
            flash("Project not found.", "warning")
        else:
            flash("Project deleted successfully.", "success")
    except Error as exc:
        connection.rollback()
        flash(f"Could not delete project: {exc.msg}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("projects"))


def get_application_form_options():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name
            FROM Users
            ORDER BY name
            """
        )
        users_list = cursor.fetchall()

        cursor.execute(
            """
            SELECT project_id, title
            FROM Project
            ORDER BY title
            """
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return users_list, projects_list


@app.route("/applications")
def applications():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                A.application_id,
                U.name AS user_name,
                P.title AS project_title,
                A.application_date,
                A.status
            FROM Application A
            JOIN Users U ON A.user_id = U.user_id
            JOIN Project P ON A.project_id = P.project_id
            ORDER BY A.application_id
            """
        )
        applications_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("applications/list.html", applications=applications_list)


@app.route("/applications/add", methods=["GET", "POST"])
def add_application():
    users_list, projects_list = get_application_form_options()

    if request.method == "POST":
        form_data = {
            "user_id": request.form.get("user_id", "").strip(),
            "project_id": request.form.get("project_id", "").strip(),
            "application_date": request.form.get("application_date", "").strip(),
            "status": request.form.get("status", "").strip(),
        }

        if (
            not form_data["user_id"]
            or not form_data["project_id"]
            or not form_data["application_date"]
            or not form_data["status"]
        ):
            flash("User, project, application date, and status are required.", "danger")
            return render_template(
                "applications/form.html",
                title="Add Application",
                heading="Add Application",
                button_label="Create Application",
                application=form_data,
                users=users_list,
                projects=projects_list,
                form_action=url_for("add_application"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Application (user_id, project_id, application_date, status)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    form_data["user_id"],
                    form_data["project_id"],
                    form_data["application_date"],
                    form_data["status"],
                ),
            )
            connection.commit()
            flash("Application added successfully.", "success")
            return redirect(url_for("applications"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add application: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "applications/form.html",
            title="Add Application",
            heading="Add Application",
            button_label="Create Application",
            application=form_data,
            users=users_list,
            projects=projects_list,
            form_action=url_for("add_application"),
        )

    return render_template(
        "applications/form.html",
        title="Add Application",
        heading="Add Application",
        button_label="Create Application",
        application={},
        users=users_list,
        projects=projects_list,
        form_action=url_for("add_application"),
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5001")),
    )
