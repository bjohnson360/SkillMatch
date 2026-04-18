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


def get_all_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT skill_id, skill_name, category
            FROM Skill
            ORDER BY skill_name
            """
        )
        skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return skills


def get_available_skills_for_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT S.skill_id, S.skill_name, S.category
            FROM Skill S
            WHERE S.skill_id NOT IN (
                SELECT US.skill_id
                FROM UserSkill US
                WHERE US.user_id = %s
            )
            ORDER BY S.skill_name
            """,
            (user_id,),
        )
        skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return skills


def get_available_skills_for_project(project_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT S.skill_id, S.skill_name, S.category
            FROM Skill S
            WHERE S.skill_id NOT IN (
                SELECT PS.skill_id
                FROM ProjectSkill PS
                WHERE PS.project_id = %s
            )
            ORDER BY S.skill_name
            """,
            (project_id,),
        )
        skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return skills


def get_user_skill(user_id, skill_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                US.user_id,
                US.skill_id,
                US.proficiency_level,
                S.skill_name,
                S.category
            FROM UserSkill US
            JOIN Skill S ON US.skill_id = S.skill_id
            WHERE US.user_id = %s AND US.skill_id = %s
            """,
            (user_id, skill_id),
        )
        user_skill = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return user_skill


def get_project_skill(project_id, skill_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                PS.project_id,
                PS.skill_id,
                PS.required_level,
                S.skill_name,
                S.category
            FROM ProjectSkill PS
            JOIN Skill S ON PS.skill_id = S.skill_id
            WHERE PS.project_id = %s AND PS.skill_id = %s
            """,
            (project_id, skill_id),
        )
        project_skill = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return project_skill


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


@app.route("/my-skills")
@roles_required("user")
def my_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                US.skill_id,
                S.skill_name,
                S.category,
                US.proficiency_level
            FROM UserSkill US
            JOIN Skill S ON US.skill_id = S.skill_id
            WHERE US.user_id = %s
            ORDER BY S.skill_name
            """,
            (session["user_id"],),
        )
        user_skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("skills/my_list.html", user_skills=user_skills)


@app.route("/my-skills/add", methods=["GET", "POST"])
@roles_required("user")
def add_my_skill():
    skill_options = get_available_skills_for_user(session["user_id"])

    if request.method == "POST":
        form_data = {
            "skill_id": request.form.get("skill_id", "").strip(),
            "proficiency_level": request.form.get("proficiency_level", "").strip(),
        }

        if not form_data["skill_id"] or not form_data["proficiency_level"]:
            flash("Skill and proficiency level are required.", "danger")
            return render_template(
                "skills/form.html",
                title="Add Skill",
                heading="Add Skill",
                button_label="Add Skill",
                form_data=form_data,
                skill_options=skill_options,
                is_edit=False,
                form_action=url_for("add_my_skill"),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO UserSkill (user_id, skill_id, proficiency_level)
                VALUES (%s, %s, %s)
                """,
                (session["user_id"], form_data["skill_id"], form_data["proficiency_level"]),
            )
            connection.commit()
            flash("Skill added to your profile.", "success")
            return redirect(url_for("my_skills"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add skill: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "skills/form.html",
            title="Add Skill",
            heading="Add Skill",
            button_label="Add Skill",
            form_data=form_data,
            skill_options=skill_options,
            is_edit=False,
            form_action=url_for("add_my_skill"),
        )

    return render_template(
        "skills/form.html",
        title="Add Skill",
        heading="Add Skill",
        button_label="Add Skill",
        form_data={},
        skill_options=skill_options,
        is_edit=False,
        form_action=url_for("add_my_skill"),
    )


@app.route("/my-skills/edit/<int:skill_id>", methods=["GET", "POST"])
@roles_required("user")
def edit_my_skill(skill_id):
    user_skill = get_user_skill(session["user_id"], skill_id)
    if not user_skill:
        flash("Skill not found on your profile.", "warning")
        return redirect(url_for("my_skills"))

    if request.method == "POST":
        form_data = {
            "skill_id": skill_id,
            "proficiency_level": request.form.get("proficiency_level", "").strip(),
            "skill_name": user_skill["skill_name"],
            "category": user_skill["category"],
        }

        if not form_data["proficiency_level"]:
            flash("Proficiency level is required.", "danger")
            return render_template(
                "skills/form.html",
                title="Edit Skill",
                heading="Edit Skill",
                button_label="Update Skill",
                form_data=form_data,
                skill_options=[],
                is_edit=True,
                form_action=url_for("edit_my_skill", skill_id=skill_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE UserSkill
                SET proficiency_level = %s
                WHERE user_id = %s AND skill_id = %s
                """,
                (form_data["proficiency_level"], session["user_id"], skill_id),
            )
            connection.commit()
            flash("Skill updated successfully.", "success")
            return redirect(url_for("my_skills"))
        except Error as exc:
            connection.rollback()
            flash(f"Could not update skill: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "skills/form.html",
            title="Edit Skill",
            heading="Edit Skill",
            button_label="Update Skill",
            form_data=form_data,
            skill_options=[],
            is_edit=True,
            form_action=url_for("edit_my_skill", skill_id=skill_id),
        )

    return render_template(
        "skills/form.html",
        title="Edit Skill",
        heading="Edit Skill",
        button_label="Update Skill",
        form_data=user_skill,
        skill_options=[],
        is_edit=True,
        form_action=url_for("edit_my_skill", skill_id=skill_id),
    )


@app.route("/my-skills/delete/<int:skill_id>", methods=["POST"])
@roles_required("user")
def delete_my_skill(skill_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM UserSkill WHERE user_id = %s AND skill_id = %s",
            (session["user_id"], skill_id),
        )
        connection.commit()

        if cursor.rowcount == 0:
            flash("Skill not found on your profile.", "warning")
        else:
            flash("Skill removed from your profile.", "success")
    except Error as exc:
        connection.rollback()
        flash(f"Could not remove skill: {exc.msg}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("my_skills"))


@app.route("/owner/projects/<int:project_id>/skills")
@roles_required("owner", "admin")
def owner_project_skills(project_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        if session.get("role") == "admin":
            return redirect(url_for("admin_projects"))
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only manage skills for your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                PS.skill_id,
                S.skill_name,
                S.category,
                PS.required_level
            FROM ProjectSkill PS
            JOIN Skill S ON PS.skill_id = S.skill_id
            WHERE PS.project_id = %s
            ORDER BY S.skill_name
            """,
            (project_id,),
        )
        project_skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "owner/projects/skills.html",
        project=project,
        project_skills=project_skills,
    )


@app.route("/owner/projects/<int:project_id>/skills/add", methods=["GET", "POST"])
@roles_required("owner", "admin")
def add_project_skill(project_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        if session.get("role") == "admin":
            return redirect(url_for("admin_projects"))
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only manage skills for your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    skill_options = get_available_skills_for_project(project_id)

    if request.method == "POST":
        form_data = {
            "skill_id": request.form.get("skill_id", "").strip(),
            "required_level": request.form.get("required_level", "").strip(),
        }

        if not form_data["skill_id"] or not form_data["required_level"]:
            flash("Skill and required level are required.", "danger")
            return render_template(
                "owner/projects/skill_form.html",
                title="Add Project Skill",
                heading="Add Project Skill",
                button_label="Add Skill",
                project=project,
                form_data=form_data,
                skill_options=skill_options,
                is_edit=False,
                form_action=url_for("add_project_skill", project_id=project_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO ProjectSkill (project_id, skill_id, required_level)
                VALUES (%s, %s, %s)
                """,
                (project_id, form_data["skill_id"], form_data["required_level"]),
            )
            connection.commit()
            flash("Project skill added successfully.", "success")
            return redirect(url_for("owner_project_skills", project_id=project_id))
        except Error as exc:
            connection.rollback()
            flash(f"Could not add project skill: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "owner/projects/skill_form.html",
            title="Add Project Skill",
            heading="Add Project Skill",
            button_label="Add Skill",
            project=project,
            form_data=form_data,
            skill_options=skill_options,
            is_edit=False,
            form_action=url_for("add_project_skill", project_id=project_id),
        )

    return render_template(
        "owner/projects/skill_form.html",
        title="Add Project Skill",
        heading="Add Project Skill",
        button_label="Add Skill",
        project=project,
        form_data={},
        skill_options=skill_options,
        is_edit=False,
        form_action=url_for("add_project_skill", project_id=project_id),
    )


@app.route("/owner/projects/<int:project_id>/skills/edit/<int:skill_id>", methods=["GET", "POST"])
@roles_required("owner", "admin")
def edit_project_skill(project_id, skill_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        if session.get("role") == "admin":
            return redirect(url_for("admin_projects"))
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only manage skills for your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    project_skill = get_project_skill(project_id, skill_id)
    if not project_skill:
        flash("Project skill not found.", "warning")
        return redirect(url_for("owner_project_skills", project_id=project_id))

    if request.method == "POST":
        form_data = {
            "skill_id": skill_id,
            "required_level": request.form.get("required_level", "").strip(),
            "skill_name": project_skill["skill_name"],
            "category": project_skill["category"],
        }

        if not form_data["required_level"]:
            flash("Required level is required.", "danger")
            return render_template(
                "owner/projects/skill_form.html",
                title="Edit Project Skill",
                heading="Edit Project Skill",
                button_label="Update Skill",
                project=project,
                form_data=form_data,
                skill_options=[],
                is_edit=True,
                form_action=url_for("edit_project_skill", project_id=project_id, skill_id=skill_id),
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE ProjectSkill
                SET required_level = %s
                WHERE project_id = %s AND skill_id = %s
                """,
                (form_data["required_level"], project_id, skill_id),
            )
            connection.commit()
            flash("Project skill updated successfully.", "success")
            return redirect(url_for("owner_project_skills", project_id=project_id))
        except Error as exc:
            connection.rollback()
            flash(f"Could not update project skill: {exc.msg}", "danger")
        finally:
            cursor.close()
            connection.close()

        return render_template(
            "owner/projects/skill_form.html",
            title="Edit Project Skill",
            heading="Edit Project Skill",
            button_label="Update Skill",
            project=project,
            form_data=form_data,
            skill_options=[],
            is_edit=True,
            form_action=url_for("edit_project_skill", project_id=project_id, skill_id=skill_id),
        )

    return render_template(
        "owner/projects/skill_form.html",
        title="Edit Project Skill",
        heading="Edit Project Skill",
        button_label="Update Skill",
        project=project,
        form_data=project_skill,
        skill_options=[],
        is_edit=True,
        form_action=url_for("edit_project_skill", project_id=project_id, skill_id=skill_id),
    )


@app.route("/owner/projects/<int:project_id>/skills/delete/<int:skill_id>", methods=["POST"])
@roles_required("owner", "admin")
def delete_project_skill(project_id, skill_id):
    project = get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "warning")
        if session.get("role") == "admin":
            return redirect(url_for("admin_projects"))
        return redirect(url_for("owner_projects"))

    if not project_access_allowed(project):
        flash("You can only manage skills for your own projects.", "danger")
        return redirect(url_for("owner_projects"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM ProjectSkill WHERE project_id = %s AND skill_id = %s",
            (project_id, skill_id),
        )
        connection.commit()

        if cursor.rowcount == 0:
            flash("Project skill not found.", "warning")
        else:
            flash("Project skill removed successfully.", "success")
    except Error as exc:
        connection.rollback()
        flash(f"Could not remove project skill: {exc.msg}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("owner_project_skills", project_id=project_id))


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


@app.route("/recommendations")
@roles_required("user")
def recommendations():
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
                U.name AS owner_name,
                COUNT(DISTINCT CASE
                    WHEN US.skill_id IS NOT NULL THEN PS.skill_id
                END) AS matching_skills,
                COUNT(DISTINCT PS.skill_id) AS total_required_skills,
                ROUND(
                    (
                        COUNT(DISTINCT CASE
                            WHEN US.skill_id IS NOT NULL THEN PS.skill_id
                        END) / NULLIF(COUNT(DISTINCT PS.skill_id), 0)
                    ) * 100,
                    1
                ) AS match_percentage
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            LEFT JOIN ProjectSkill PS ON P.project_id = PS.project_id
            LEFT JOIN UserSkill US
                ON US.user_id = %s
                AND US.skill_id = PS.skill_id
                AND US.proficiency_level >= PS.required_level
            LEFT JOIN Application A
                ON A.project_id = P.project_id
                AND A.user_id = %s
            WHERE P.status = 'Open'
                AND A.application_id IS NULL
            GROUP BY P.project_id, P.title, P.description, P.difficulty, U.name
            HAVING COUNT(DISTINCT CASE
                WHEN US.skill_id IS NOT NULL THEN PS.skill_id
            END) > 0
            ORDER BY match_percentage DESC, matching_skills DESC, P.title
            """,
            (session["user_id"], session["user_id"]),
        )
        recommended_projects = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "recommendations.html",
        recommended_projects=recommended_projects,
    )


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
            return redirect(url_for("my_applications"))
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


@app.route("/admin/analytics")
@roles_required("admin")
def admin_analytics():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM Users WHERE role = 'user') AS total_users,
                (SELECT COUNT(*) FROM Users WHERE role = 'owner') AS total_owners,
                (SELECT COUNT(*) FROM Project) AS total_projects,
                (SELECT COUNT(*) FROM Application) AS total_applications
            """
        )
        summary = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                S.skill_name,
                S.category,
                COUNT(*) AS project_usage,
                ROUND(AVG(PS.required_level), 1) AS avg_required_level
            FROM ProjectSkill PS
            JOIN Skill S ON PS.skill_id = S.skill_id
            GROUP BY S.skill_id, S.skill_name, S.category
            ORDER BY project_usage DESC, avg_required_level DESC, S.skill_name
            LIMIT 5
            """
        )
        in_demand_skills = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                P.project_id,
                P.title,
                U.name AS owner_name,
                COUNT(A.application_id) AS total_applications
            FROM Project P
            LEFT JOIN Users U ON P.owner_id = U.user_id
            LEFT JOIN Application A ON P.project_id = A.project_id
            GROUP BY P.project_id, P.title, U.name
            ORDER BY total_applications DESC, P.title
            """
        )
        project_application_counts = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                U.experience_level,
                ROUND(AVG(COALESCE(C.compatibility_score, 0)), 1) AS avg_compatibility_score,
                COUNT(A.application_id) AS total_applications
            FROM Application A
            JOIN Users U ON A.user_id = U.user_id
            LEFT JOIN (
                SELECT
                    A2.application_id,
                    ROUND(
                        (
                            COUNT(DISTINCT CASE
                                WHEN US.skill_id IS NOT NULL THEN PS.skill_id
                            END) / NULLIF(COUNT(DISTINCT PS.skill_id), 0)
                        ) * 100,
                        1
                    ) AS compatibility_score
                FROM Application A2
                LEFT JOIN ProjectSkill PS ON A2.project_id = PS.project_id
                LEFT JOIN UserSkill US
                    ON US.user_id = A2.user_id
                    AND US.skill_id = PS.skill_id
                    AND US.proficiency_level >= PS.required_level
                GROUP BY A2.application_id
            ) C ON C.application_id = A.application_id
            GROUP BY U.experience_level
            ORDER BY avg_compatibility_score DESC, U.experience_level
            """
        )
        compatibility_by_experience = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin/analytics.html",
        summary=summary,
        in_demand_skills=in_demand_skills,
        project_application_counts=project_application_counts,
        compatibility_by_experience=compatibility_by_experience,
    )


@app.route("/owner/analytics")
@app.route("/owner/stats")
@roles_required("owner", "admin")
def owner_analytics():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if session.get("role") == "admin":
        owner_filter_clause = ""
        owner_params = ()
    else:
        owner_filter_clause = "WHERE P.owner_id = %s"
        owner_params = (session["user_id"],)

    try:
        cursor.execute(
            f"""
            SELECT
                COUNT(DISTINCT P.project_id) AS total_projects,
                COUNT(DISTINCT CASE WHEN P.status = 'Open' THEN P.project_id END) AS open_projects,
                COUNT(DISTINCT A.application_id) AS total_applications_received,
                ROUND(AVG(COALESCE(C.compatibility_score, 0)), 1) AS avg_compatibility_score
            FROM Project P
            LEFT JOIN Application A ON P.project_id = A.project_id
            LEFT JOIN (
                SELECT
                    A2.application_id,
                    ROUND(
                        (
                            COUNT(DISTINCT CASE
                                WHEN US.skill_id IS NOT NULL THEN PS.skill_id
                            END) / NULLIF(COUNT(DISTINCT PS.skill_id), 0)
                        ) * 100,
                        1
                    ) AS compatibility_score
                FROM Application A2
                LEFT JOIN ProjectSkill PS ON A2.project_id = PS.project_id
                LEFT JOIN UserSkill US
                    ON US.user_id = A2.user_id
                    AND US.skill_id = PS.skill_id
                    AND US.proficiency_level >= PS.required_level
                GROUP BY A2.application_id
            ) C ON C.application_id = A.application_id
            {owner_filter_clause}
            """,
            owner_params,
        )
        summary = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT
                P.project_id,
                P.title,
                P.status,
                COUNT(DISTINCT A.application_id) AS total_applicants,
                ROUND(AVG(COALESCE(C.compatibility_score, 0)), 1) AS avg_compatibility_score
            FROM Project P
            LEFT JOIN Application A ON P.project_id = A.project_id
            LEFT JOIN (
                SELECT
                    A2.application_id,
                    ROUND(
                        (
                            COUNT(DISTINCT CASE
                                WHEN US.skill_id IS NOT NULL THEN PS.skill_id
                            END) / NULLIF(COUNT(DISTINCT PS.skill_id), 0)
                        ) * 100,
                        1
                    ) AS compatibility_score
                FROM Application A2
                LEFT JOIN ProjectSkill PS ON A2.project_id = PS.project_id
                LEFT JOIN UserSkill US
                    ON US.user_id = A2.user_id
                    AND US.skill_id = PS.skill_id
                    AND US.proficiency_level >= PS.required_level
                GROUP BY A2.application_id
            ) C ON C.application_id = A.application_id
            {owner_filter_clause}
            GROUP BY P.project_id, P.title, P.status
            ORDER BY total_applicants DESC, avg_compatibility_score DESC, P.title
            """,
            owner_params,
        )
        project_analytics = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT
                S.skill_name,
                S.category,
                COUNT(*) AS project_usage,
                ROUND(AVG(PS.required_level), 1) AS avg_required_level
            FROM ProjectSkill PS
            JOIN Skill S ON PS.skill_id = S.skill_id
            JOIN Project P ON PS.project_id = P.project_id
            {owner_filter_clause}
            GROUP BY S.skill_id, S.skill_name, S.category
            ORDER BY project_usage DESC, avg_required_level DESC, S.skill_name
            LIMIT 5
            """,
            owner_params,
        )
        requested_skills = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "owner/analytics.html",
        summary=summary,
        project_analytics=project_analytics,
        requested_skills=requested_skills,
        is_admin_view=session.get("role") == "admin",
    )


@app.route("/stats")
@roles_required("admin")
def stats():
    return redirect(url_for("admin_analytics"))


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
