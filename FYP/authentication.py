import pymysql
import os
from werkzeug.security import check_password_hash
from pymysql.cursors import DictCursor



def get_db_connection():
    try:
        # Use environment variables for Railway deployment
        host = os.getenv('DB_HOST', 'localhost')
        user = os.getenv('DB_USER', 'root')
        password = os.getenv('DB_PASSWORD', 'Ma@461398') 
        database = os.getenv('DB_NAME', 'fyp')
        
        if password is None:
            raise ValueError("Database password not set. Please set the DB_PASSWORD environment variable.")
        
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            cursorclass=DictCursor  # For dictionary cursor
        )
        return conn
    except Exception as err:
        print(f"Error while connecting to database: {err}")
        return None

        

def check_credentials(email, password):
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM user WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):
                return user['level'] # Return user level
            return None
    except Exception as e:
        print(f"Exception during query execution: {e}")
        return None
    finally:
        conn.close()


