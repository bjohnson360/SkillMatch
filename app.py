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


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5001")),
    )
