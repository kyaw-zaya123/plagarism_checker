from flask import Flask
from flask_cors import CORS  # For handling CORS
import os
import logging
from app.api import api_bp  # Import the API blueprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Load configuration from environment variables or a config file
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key')
    app.config['DB_HOST'] = os.getenv('DB_HOST', '127.0.0.1')
    app.config['DB_USER'] = os.getenv('DB_USER', 'root')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', 'your_password')
    app.config['DB_NAME'] = os.getenv('DB_NAME', 'plagiarism_checker')

    # Enable CORS for all routes (or configure it as needed)
    CORS(app)

    # Register the API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error handling example
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"An error occurred: {e}")
        return {"error": str(e)}, 500

    return app
