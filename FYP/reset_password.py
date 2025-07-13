from flask import Blueprint, request, flash, redirect, url_for, render_template
from werkzeug.security import generate_password_hash
from authentication import get_db_connection  # Make sure this is correct

# Register Blueprint
reset_bp = Blueprint('reset_bp', __name__)

@reset_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate inputs
        if not email or not new_password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for('reset_bp.reset_password'))

        # Validate password match
        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
            return redirect(url_for('reset_bp.reset_password'))

        # Connect to DB
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed.", "error")
            return redirect(url_for('reset_bp.reset_password'))
        
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            flash("Email not found in our system.", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('reset_bp.reset_password'))

        # Hash and update password
        hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE user SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()

        # Close DB
        cursor.close()
        conn.close()

        flash("Password successfully reset. Please log in.", "success")
        return redirect(url_for('login_route'))  # Redirect to login page

    return render_template("reset_password.html")
