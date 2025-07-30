from flask import Blueprint, render_template, request, redirect, url_for
from authentication import get_db_connection
from werkzeug.security import generate_password_hash
from send_email import send_password_email 
import secrets

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin():
    message = None
    message_category = None

    conn = get_db_connection()
    if conn is None:
        message = "Database connection failed."
        message_category = "danger"
        return render_template('admin.html', users=[], message=message, category=message_category)

    try:
        if request.method == 'POST':
            form_type = request.form.get('form_type')

            if form_type == 'add_user':
                fullname = request.form['full_name']
                email = request.form['email']
                position = request.form['position']
                level = request.form['level']

                temp_password = secrets.token_urlsafe(10)
                hashed_password = generate_password_hash(temp_password)

                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        message = "This email is already registered."
                        message_category = "warning"
                    else:
                        cursor.execute("""
                            INSERT INTO user (email, password, fullname, position, level)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (email, hashed_password, fullname, position, level))
                        conn.commit()
                        send_password_email(email, temp_password, fullname)
                        message = "New user added successfully!"
                        message_category = "success"

            elif form_type == 'update_user':
                user_id = request.form['user_id']
                fullname = request.form['edit_fullname']
                email = request.form['edit_email']
                position = request.form['edit_position']
                level = request.form['edit_level']

                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE user
                        SET fullname = %s, email = %s, position = %s, level = %s
                        WHERE id = %s
                    """, (fullname, email, position, level, user_id))
                    conn.commit()
                    message = "User updated successfully."
                    message_category = "success"

            elif form_type == 'delete_user':
                user_id = request.form['user_id']

                with conn.cursor() as cursor:
                    # Get user info for confirmation message
                    cursor.execute("SELECT fullname FROM user WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    
                    if user:
                        cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
                        conn.commit()
                        message = f"User have been deleted successfully."
                        message_category = "success"
                    else:
                        message = "User not found."
                        message_category = "warning"

        # ✅ Always fetch updated user list
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, fullname, email, position, level FROM user ORDER BY id ASC")
            rows = cursor.fetchall()
            users = []
            for row in rows:
                users.append({
                    'id': row['id'],
                    'fullname': row['fullname'],
                    'email': row['email'],
                    'position': row['position'],
                    'level': row['level']
                })

    except Exception as e:
        conn.rollback()
        message = f"An error occurred: {str(e)}"
        message_category = "danger"
        users = []
    finally:
        conn.close()

    return render_template('admin.html', users=users, message=message, category=message_category)
