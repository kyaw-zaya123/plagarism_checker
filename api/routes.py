from flask import Blueprint, request, jsonify, abort
from app.api.api import create_api_key  # Import the function to create API key
import mysql.connector
from mysql.connector import Error
import os
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """ Utility function to get a database connection """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "Kyaw550550#"),
            database=os.getenv("DB_NAME", "plagiarism_checker")
        )
        return conn
    except Error as e:
        logger.error(f"Error connecting to the database: {e}")
        return None

# Registration route
@api_bp.route('/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # TODO: Hash password before storing it (e.g., bcrypt)
    return jsonify({"message": "User registered successfully"}), 201

# Login route
@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    # TODO: Implement password verification (e.g., bcrypt)
    return jsonify({"message": "Login successful"}), 200

# Generate API Key route
@api_bp.route('/generate_api_key', methods=['POST'])
def generate_api_key_route():
    if not request.json or 'user_id' not in request.json:
        abort(400, {"error": "Missing user_id in the request"})

    user_id = request.json['user_id']

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Validate user existence
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Generate and save API key for the user
        api_key = create_api_key(user_id)
        return jsonify({"message": "API key generated", "api_key": api_key}), 201

    except Error as e:
        logger.error(f"Error while generating API key: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# Retrieve API Key route
@api_bp.route('/get_api_key/<int:user_id>', methods=['GET'])
def get_api_key(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT api_key FROM api_keys WHERE user_id = %s AND active = 1", (user_id,))
        api_key = cursor.fetchone()

        if not api_key:
            return jsonify({"error": "API key not found"}), 404

        return jsonify({"api_key": api_key['api_key']}), 200

    except Error as e:
        logger.error(f"Error while retrieving API key: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# Delete (Deactivate) API Key route
@api_bp.route('/delete_api_key/<int:user_id>', methods=['DELETE'])
def delete_api_key(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT api_key FROM api_keys WHERE user_id = %s AND active = 1", (user_id,))
        api_key = cursor.fetchone()

        if not api_key:
            return jsonify({"error": "API key not found"}), 404

        # Deactivate the API key (soft delete)
        cursor.execute("UPDATE api_keys SET active = 0, deactivated_at = NOW() WHERE user_id = %s AND api_key = %s", (user_id, api_key['api_key']))
        conn.commit()

        return jsonify({"message": "API key deleted successfully"}), 200

    except Error as e:
        logger.error(f"Error while deleting API key: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()
