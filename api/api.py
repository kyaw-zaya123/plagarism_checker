import secrets
import mysql.connector
import os

def generate_api_key():
    """Generate a secure 64-character API key."""
    return secrets.token_hex(32)

def save_api_key_to_db(user_id, api_key):
    """Save the API key to the database for a given user."""
    try:
        # Secure database connection using environment variables
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "Kyaw550550#"),  # Use environment variables for security
            database=os.getenv("DB_NAME", "plagiarism_checker")
        )
        cursor = conn.cursor()

        sql = "INSERT INTO api_keys (user_id, api_key) VALUES (%s, %s)"
        val = (user_id, api_key)
        cursor.execute(sql, val)

        conn.commit()
        print(f"API key for user {user_id} saved successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        # Ensure the connection is closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_api_key(user_id):
    """Generate and save a new API key for the specified user."""
    new_api_key = generate_api_key()
    save_api_key_to_db(user_id, new_api_key)
    return new_api_key
