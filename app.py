import os
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
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


def current_user():
    if "user_id" not in session:
        return None

    return {
        "user_id": session.get("user_id"),
        "role": session.get("role"),
        "name": session.get("name"),
    }


@app.context_processor
def inject_user_context():
    user = current_user()
    return {
        "current_user": user,
        "is_logged_in": user is not None,
        "current_role": user["role"] if user else None,
    }


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))

            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("home"))

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def get_project_owner_options():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name
            FROM Users
            WHERE role = 'owner'
            ORDER BY name
            """
        )
        owners = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return owners


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
            WHERE status = 'Open'
            ORDER BY title
            """
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return users_list, projects_list


def get_user_by_id(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name, email, location, experience_level, role
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


def get_user_by_email(email):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name, email, location, experience_level, role
            FROM Users
            WHERE email = %s
            """,
            (email,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return user


def get_project_by_id(project_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                P.description,
                P.difficulty,
                P.status,
                P.owner_id,
                U.name AS owner_name
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            WHERE P.project_id = %s
            """,
            (project_id,),
        )
        project = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return project


def project_access_allowed(project):
    if session.get("role") == "admin":
        return True
    return project and project.get("owner_id") == session.get("user_id")


def user_has_applied(user_id, project_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1
            FROM Application
            WHERE user_id = %s AND project_id = %s
            LIMIT 1
            """,
            (user_id, project_id),
        )
        existing_application = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return existing_application is not None


@app.route("/")
def home():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT project_id, title, description, difficulty, status, owner_id
            FROM Project
            WHERE status = 'Open'
            ORDER BY project_id DESC
            LIMIT 3
            """
        )
        featured_projects = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("home.html", featured_projects=featured_projects)


@app.route("/projects")
def projects():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                P.description,
                P.difficulty,
                P.status,
                P.owner_id,
                U.name AS owner_name
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            WHERE P.status = 'Open'
            ORDER BY P.project_id
            """
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("projects/public_list.html", projects=projects_list)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = get_project_by_id(project_id)

    if not project or project["status"] != "Open":
        flash("Project not found.", "warning")
        return redirect(url_for("projects"))

    has_applied = False
    if session.get("role") == "user":
        has_applied = user_has_applied(session["user_id"], project_id)

    return render_template("projects/detail.html", project=project, has_applied=has_applied)


@app.route("/projects/<int:project_id>/apply", methods=["POST"])
@roles_required("user")
def apply_to_project(project_id):
    project = get_project_by_id(project_id)

    if not project or project["status"] != "Open":
        flash("Project not found.", "warning")
        return redirect(url_for("projects"))

    if user_has_applied(session["user_id"], project_id):
        flash("You have already applied to this project.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO Application (user_id, project_id, application_date, status)
            VALUES (%s, %s, CURDATE(), %s)
            """,
            (session["user_id"], project_id, "Submitted"),
        )
        connection.commit()
        flash("Application submitted successfully.", "success")
        return redirect(url_for("my_applications"))
    except Error as exc:
        connection.rollback()
        flash(f"Could not submit application: {exc.msg}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "location": request.form.get("location", "").strip(),
            "experience_level": request.form.get("experience_level", "").strip(),
            "role": request.form.get("role", "").strip(),
        }

        if (
            not form_data["name"]
            or not form_data["email"]
            or not form_data["experience_level"]
            or form_data["role"] not in {"user", "owner"}
        ):
            flash("Name, email, experience level, and account type are required.", "danger")
            return render_template("signup.html", form_data=form_data)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Users (name, email, location, experience_level, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    form_data["name"],
                    form_data["email"],
                    form_data["location"] or None,
                    form_data["experience_level"],
                    form_data["role"],
                ),
            )
            connection.commit()
            new_user = get_user_by_email(form_data["email"])
            session["user_id"] = new_user["user_id"]
            session["role"] = new_user["role"]
            session["name"] = new_user["name"]
            flash("Account created successfully.", "success")
            return redirect(url_for("home"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not create account: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template("signup.html", form_data=form_data)

    return render_template("signup.html", form_data={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not email:
            flash("Email is required.", "danger")
            return render_template("login.html", form_data={"email": email})

        user = get_user_by_email(email)
        if not user:
            flash("No account was found for that email address.", "danger")
            return render_template("login.html", form_data={"email": email})

        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        flash(f"Welcome back, {user['name']}.", "success")
        return redirect(url_for("home"))

    return render_template("login.html", form_data={})


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/admin/users")
@roles_required("admin")
def admin_users():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT user_id, name, email, location, experience_level, role
            FROM Users
            ORDER BY user_id
            """
        )
        users_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("admin/users/list.html", users=users_list)


@app.route("/admin/users/add", methods=["GET", "POST"])
@roles_required("admin")
def admin_add_user():
    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "location": request.form.get("location", "").strip(),
            "experience_level": request.form.get("experience_level", "").strip(),
            "role": request.form.get("role", "").strip(),
        }

        if (
            not form_data["name"]
            or not form_data["email"]
            or not form_data["experience_level"]
            or not form_data["role"]
        ):
            flash("Name, email, experience level, and role are required.", "danger")
            return render_template(
                "admin/users/form.html",
                title="Add User",
                heading="Add User",
                button_label="Create User",
                user=form_data,
                form_action=url_for("admin_add_user"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Users (name, email, location, experience_level, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    form_data["name"],
                    form_data["email"],
                    form_data["location"] or None,
                    form_data["experience_level"],
                    form_data["role"],
                ),
            )
            connection.commit()
            flash("User added successfully.", "success")
            return redirect(url_for("admin_users"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add user: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "admin/users/form.html",
            title="Add User",
            heading="Add User",
            button_label="Create User",
            user=form_data,
            form_action=url_for("admin_add_user"),
        )

    return render_template(
        "admin/users/form.html",
        title="Add User",
        heading="Add User",
        button_label="Create User",
        user={},
        form_action=url_for("admin_add_user"),
    )


@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@roles_required("admin")
def admin_edit_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        updated_user = {
            "user_id": user_id,
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "location": request.form.get("location", "").strip(),
            "experience_level": request.form.get("experience_level", "").strip(),
            "role": request.form.get("role", "").strip(),
        }

        if (
            not updated_user["name"]
            or not updated_user["email"]
            or not updated_user["experience_level"]
            or not updated_user["role"]
        ):
            flash("Name, email, experience level, and role are required.", "danger")
            return render_template(
                "admin/users/form.html",
                title="Edit User",
                heading="Edit User",
                button_label="Update User",
                user=updated_user,
                form_action=url_for("admin_edit_user", user_id=user_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE Users
                SET name = %s, email = %s, location = %s, experience_level = %s, role = %s
                WHERE user_id = %s
                """,
                (
                    updated_user["name"],
                    updated_user["email"],
                    updated_user["location"] or None,
                    updated_user["experience_level"],
                    updated_user["role"],
                    user_id,
                ),
            )
            connection.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for("admin_users"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not update user: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "admin/users/form.html",
            title="Edit User",
            heading="Edit User",
            button_label="Update User",
            user=updated_user,
            form_action=url_for("admin_edit_user", user_id=user_id),
        )

    return render_template(
        "admin/users/form.html",
        title="Edit User",
        heading="Edit User",
        button_label="Update User",
        user=user,
        form_action=url_for("admin_edit_user", user_id=user_id),
    )


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@roles_required("admin")
def admin_delete_user(user_id):
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

    return redirect(url_for("admin_users"))


@app.route("/admin/projects")
@roles_required("admin")
def admin_projects():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                P.description,
                P.difficulty,
                P.status,
                P.owner_id,
                U.name AS owner_name
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            ORDER BY P.project_id
            """
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("projects/list.html", projects=projects_list)


@app.route("/admin/projects/add", methods=["GET", "POST"])
@roles_required("admin")
def admin_add_project():
    owner_options = get_project_owner_options()

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
            "owner_id": request.form.get("owner_id", "").strip(),
        }

        if not form_data["title"] or not form_data["difficulty"] or not form_data["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Add Project",
                heading="Add Project",
                button_label="Create Project",
                project=form_data,
                owners=owner_options,
                owner_locked=False,
                back_url=url_for("admin_projects"),
                form_action=url_for("admin_add_project"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Project (title, description, difficulty, status, owner_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    form_data["title"],
                    form_data["description"] or None,
                    form_data["difficulty"],
                    form_data["status"],
                    form_data["owner_id"] or None,
                ),
            )
            connection.commit()
            flash("Project added successfully.", "success")
            return redirect(url_for("admin_projects"))
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
            owners=owner_options,
            owner_locked=False,
            back_url=url_for("admin_projects"),
            form_action=url_for("admin_add_project"),
        )

    return render_template(
        "projects/form.html",
        title="Add Project",
        heading="Add Project",
        button_label="Create Project",
        project={},
        owners=owner_options,
        owner_locked=False,
        back_url=url_for("admin_projects"),
        form_action=url_for("admin_add_project"),
    )


@app.route("/admin/projects/edit/<int:project_id>", methods=["GET", "POST"])
@roles_required("admin")
def admin_edit_project(project_id):
    project = get_project_by_id(project_id)
    owner_options = get_project_owner_options()

    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("admin_projects"))

    if request.method == "POST":
        updated_project = {
            "project_id": project_id,
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
            "owner_id": request.form.get("owner_id", "").strip(),
        }

        if not updated_project["title"] or not updated_project["difficulty"] or not updated_project["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Edit Project",
                heading="Edit Project",
                button_label="Update Project",
                project=updated_project,
                owners=owner_options,
                owner_locked=False,
                back_url=url_for("admin_projects"),
                form_action=url_for("admin_edit_project", project_id=project_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE Project
                SET title = %s, description = %s, difficulty = %s, status = %s, owner_id = %s
                WHERE project_id = %s
                """,
                (
                    updated_project["title"],
                    updated_project["description"] or None,
                    updated_project["difficulty"],
                    updated_project["status"],
                    updated_project["owner_id"] or None,
                    project_id,
                ),
            )
            connection.commit()
            flash("Project updated successfully.", "success")
            return redirect(url_for("admin_projects"))
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
            owners=owner_options,
            owner_locked=False,
            back_url=url_for("admin_projects"),
            form_action=url_for("admin_edit_project", project_id=project_id),
        )

    return render_template(
        "projects/form.html",
        title="Edit Project",
        heading="Edit Project",
        button_label="Update Project",
        project=project,
        owners=owner_options,
        owner_locked=False,
        back_url=url_for("admin_projects"),
        form_action=url_for("admin_edit_project", project_id=project_id),
    )


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@roles_required("admin")
def admin_delete_project(project_id):
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

    return redirect(url_for("admin_projects"))


@app.route("/owner/projects")
@roles_required("owner", "admin")
def owner_projects():
    if session.get("role") == "admin":
        return redirect(url_for("admin_projects"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                P.description,
                P.difficulty,
                P.status,
                P.owner_id,
                U.name AS owner_name
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            WHERE P.owner_id = %s
            ORDER BY P.project_id
            """,
            (session["user_id"],),
        )
        projects_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("owner/projects/list.html", projects=projects_list)


@app.route("/owner/projects/add", methods=["GET", "POST"])
@roles_required("owner", "admin")
def owner_add_project():
    if session.get("role") == "admin":
        return redirect(url_for("admin_add_project"))

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
            "owner_id": session["user_id"],
        }

        if not form_data["title"] or not form_data["difficulty"] or not form_data["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Add Project",
                heading="Add Project",
                button_label="Create Project",
                project=form_data,
                owners=[],
                owner_locked=True,
                back_url=url_for("owner_projects"),
                form_action=url_for("owner_add_project"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO Project (title, description, difficulty, status, owner_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    form_data["title"],
                    form_data["description"] or None,
                    form_data["difficulty"],
                    form_data["status"],
                    session["user_id"],
                ),
            )
            connection.commit()
            flash("Project added successfully.", "success")
            return redirect(url_for("owner_projects"))
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
            owners=[],
            owner_locked=True,
            back_url=url_for("owner_projects"),
            form_action=url_for("owner_add_project"),
        )

    return render_template(
        "projects/form.html",
        title="Add Project",
        heading="Add Project",
        button_label="Create Project",
        project={"owner_id": session["user_id"]},
        owners=[],
        owner_locked=True,
        back_url=url_for("owner_projects"),
        form_action=url_for("owner_add_project"),
    )


@app.route("/owner/projects/edit/<int:project_id>", methods=["GET", "POST"])
@roles_required("owner", "admin")
def owner_edit_project(project_id):
    if session.get("role") == "admin":
        return redirect(url_for("admin_edit_project", project_id=project_id))

    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only edit your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    if request.method == "POST":
        updated_project = {
            "project_id": project_id,
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "status": request.form.get("status", "").strip(),
            "owner_id": session["user_id"],
        }

        if not updated_project["title"] or not updated_project["difficulty"] or not updated_project["status"]:
            flash("Title, difficulty, and status are required.", "danger")
            return render_template(
                "projects/form.html",
                title="Edit Project",
                heading="Edit Project",
                button_label="Update Project",
                project=updated_project,
                owners=[],
                owner_locked=True,
                back_url=url_for("owner_projects"),
                form_action=url_for("owner_edit_project", project_id=project_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE Project
                SET title = %s, description = %s, difficulty = %s, status = %s
                WHERE project_id = %s AND owner_id = %s
                """,
                (
                    updated_project["title"],
                    updated_project["description"] or None,
                    updated_project["difficulty"],
                    updated_project["status"],
                    project_id,
                    session["user_id"],
                ),
            )
            connection.commit()
            flash("Project updated successfully.", "success")
            return redirect(url_for("owner_projects"))
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
            owners=[],
            owner_locked=True,
            back_url=url_for("owner_projects"),
            form_action=url_for("owner_edit_project", project_id=project_id),
        )

    return render_template(
        "projects/form.html",
        title="Edit Project",
        heading="Edit Project",
        button_label="Update Project",
        project=project,
        owners=[],
        owner_locked=True,
        back_url=url_for("owner_projects"),
        form_action=url_for("owner_edit_project", project_id=project_id),
    )


@app.route("/owner/projects/<int:project_id>/applicants")
@roles_required("owner", "admin")
def owner_project_applicants(project_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        if session.get("role") == "admin":
            return redirect(url_for("admin_projects"))
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only view applicants for your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                A.application_id,
                U.user_id,
                U.name,
                U.email,
                U.location,
                U.experience_level,
                A.application_date,
                A.status
            FROM Application A
            JOIN Users U ON A.user_id = U.user_id
            WHERE A.project_id = %s
            ORDER BY A.application_date DESC, A.application_id DESC
            """,
            (project_id,),
        )
        applicants = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "owner/projects/applicants.html",
        project=project,
        applicants=applicants,
    )


@app.route("/my-applications")
@roles_required("user")
def my_applications():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                A.application_id,
                P.project_id,
                P.title AS project_title,
                A.application_date,
                A.status
            FROM Application A
            JOIN Project P ON A.project_id = P.project_id
            WHERE A.user_id = %s
            ORDER BY A.application_date DESC, A.application_id DESC
            """,
            (session["user_id"],),
        )
        applications_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("applications/my_list.html", applications=applications_list)


@app.route("/applications")
@roles_required("admin")
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

    return render_template(
        "applications/list.html",
        applications=applications_list,
        page_title="Applications",
        page_description="Review application activity across users and projects.",
        show_add_button=False,
    )


@app.route("/applications/add", methods=["GET", "POST"])
@roles_required("user")
def add_application():
    users_list, projects_list = get_application_form_options()
    users_list = [{"user_id": session["user_id"], "name": session["name"]}]

    if request.method == "POST":
        form_data = {
            "user_id": str(session["user_id"]),
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
                lock_user=True,
                form_action=url_for("add_application"),
            )

        if user_has_applied(session["user_id"], form_data["project_id"]):
            flash("You have already applied to this project.", "warning")
            return render_template(
                "applications/form.html",
                title="Add Application",
                heading="Add Application",
                button_label="Create Application",
                application=form_data,
                users=users_list,
                projects=projects_list,
                lock_user=True,
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
                lock_user=True,
                form_action=url_for("add_application"),
            )

    return render_template(
        "applications/form.html",
        title="Add Application",
        heading="Add Application",
        button_label="Create Application",
        application={
            "user_id": str(session["user_id"]) if session.get("role") == "user" else "",
            "project_id": request.args.get("project_id", "").strip(),
        },
        users=users_list,
        projects=projects_list,
        lock_user=True,
        form_action=url_for("add_application"),
    )


@app.route("/stats")
@roles_required("admin")
def stats():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                COUNT(A.application_id) AS total_applications
            FROM Project P
            LEFT JOIN Application A ON P.project_id = A.project_id
            GROUP BY P.project_id, P.title
            ORDER BY P.project_id
            """
        )
        project_stats = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("stats.html", project_stats=project_stats)


@app.route("/matching")
@roles_required("admin")
def matching():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                U.user_id,
                U.name AS user_name,
                P.project_id,
                P.title AS project_title,
                COUNT(*) AS matching_skills
            FROM Users U
            JOIN UserSkill US ON U.user_id = US.user_id
            JOIN ProjectSkill PS ON US.skill_id = PS.skill_id
            JOIN Project P ON PS.project_id = P.project_id
            GROUP BY U.user_id, U.name, P.project_id, P.title
            ORDER BY matching_skills DESC, U.name, P.title
            """
        )
        matches = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("matching.html", matches=matches)


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5001")),
    )
