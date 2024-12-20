import os
import docx
import pdfplumber
from html2text import html2text
from flask_bcrypt import Bcrypt
from functools import wraps
from werkzeug.security import generate_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, request, render_template, redirect, flash, url_for, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import mysql.connector
from mysql.connector import Error
import datetime
import json
import uuid
from werkzeug.utils import secure_filename

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')

app = Flask(__name__, template_folder='templates')
app.secret_key = '9393c60074ab53a68d814334382cff7f'
bcrypt = Bcrypt(app)

# Swagger and Marshmallow imports
from flasgger import Swagger
from marshmallow import Schema, fields, validate


# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "title": "Plagiarism Checker API",
    "description": "API for Plagiarism Detection Application",
    "version": "1.0.0"
}
Swagger(app, config=swagger_config)

class UserRegistrationSchema(Schema):
    username = fields.Str(
        required=True, 
        validate=[
            validate.Length(min=3, max=50)
        ]
    )
    email = fields.Email(required=True)  
    password = fields.Str(
        required=True, 
        validate=[
            validate.Length(min=5)  
        ]
    )

# Request Schema for Login
class UserLoginSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Str(required=True)
    password = fields.Str(required=True)

from flask_login import UserMixin
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, is_admin=False):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('russian'))

UPLOAD_FOLDER = 'project-file'

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Kyaw550550#',
    'database': 'plagiarism_checker'
}

RECORDS_PER_PAGE = 10

def create_database_connection():
    """Create a database connection to MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return None

@login_manager.user_loader
def load_user(user_id):
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return User(id=user['id'], username=user['username'], password=user['password'], is_admin=user['is_admin'])
        except Error as e:
            print(f"Error loading user: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None

def alter_comparisons_table():
    """Alter the comparisons table to add AUTO_INCREMENT to the id field"""
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                ALTER TABLE comparisons MODIFY COLUMN id INT AUTO_INCREMENT
            """)
            connection.commit()
            print("Comparisons table altered successfully.")
        except Error as e:
            print(f"Error altering comparisons table: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def ensure_upload_folder_exists():
    """Ensure the upload folder exists."""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

def preprocess_text(text):
    """Preprocess text by tokenizing, removing stop words, and lemmatizing."""
    tokens = word_tokenize(text.lower())
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words and token.isalnum()]
    return ' '.join(tokens)

def convert_file(file_path, skip_first_page=True):
    """Convert file to text based on its type and preprocess the text, optionally skipping the first page."""
    file_extension = file_path.rsplit('.', 1)[-1].lower()
    
    if file_extension == 'docx':
        doc = docx.Document(file_path)
        if skip_first_page:
            second_page_start = 0
            for i, para in enumerate(doc.paragraphs):
                if para.runs and para.runs[0].element.xpath('.//w:br[@w:type="page"]'):
                    second_page_start = i + 1
                    break
            text = '\n'.join([para.text for para in doc.paragraphs[second_page_start:]])
        else:
            text = '\n'.join([para.text for para in doc.paragraphs])
    elif file_extension == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            pages = pdf.pages[1:] if skip_first_page else pdf.pages
            text = '\n'.join([page.extract_text() for page in pages if page.extract_text()])
    elif file_extension == 'html':
        with open(file_path, 'r', encoding='utf-8') as html_file:
            html_content = html_file.read()
            text = html2text(html_content)
            if skip_first_page:
                text = text[1500:]
    else:
        with open(file_path, 'r', encoding='utf-8') as text_file:
            lines = text_file.readlines()
            if skip_first_page:
                text = ''.join(lines[50:])
            else:
                text = ''.join(lines)
    return preprocess_text(text)

def save_file_to_db(filename, content, user_id):
    """Save file information to the database"""
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "INSERT INTO files (filename, content, user_id) VALUES (%s, %s, %s)"
            cursor.execute(query, (filename, content, user_id))
            connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error saving file to database: {e}")
            connection.rollback()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None

def save_comparison_to_db(file1_id, file2_id, similarity, user_id, highlighted_content1, highlighted_content2):
    """Save comparison results to the database"""
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
            INSERT INTO comparisons 
            (file1_id, file2_id, similarity, user_id, highlighted_content1, highlighted_content2) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (file1_id, file2_id, float(similarity), user_id, highlighted_content1, highlighted_content2))
            connection.commit()
            print(f"Comparison saved: file1_id={file1_id}, file2_id={file2_id}, similarity={similarity}, user_id={user_id}")
        except Error as e:
            print(f"Error saving comparison to database: {e}")
            connection.rollback()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def compare_files(file_paths, user_id):
    """Compare files for plagiarism and return results, ignoring the first page of each file."""
    file_contents = [convert_file(file_path, skip_first_page=True) for file_path in file_paths]   
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(file_contents)   
    cosine_sim = cosine_similarity(tfidf_matrix)
    results = []
    file_ids = []
    for file_path, content in zip(file_paths, file_contents):
        file_id = save_file_to_db(os.path.basename(file_path), content, user_id)
        if file_id is not None:
            file_ids.append(file_id)
        else:
            print(f"Error: Could not save file {file_path} to database")
    for i in range(len(file_ids)):
        for j in range(i + 1, len(file_ids)):
            similarity = float(cosine_sim[i][j] * 100)
            file1, file2 = file_paths[i], file_paths[j]
            highlighted_file1 = highlight_similar_parts(file_contents[i], file_contents[j])
            highlighted_file2 = highlight_similar_parts(file_contents[j], file_contents[i])
            save_comparison_to_db(file_ids[i], file_ids[j], similarity, user_id, highlighted_file1, highlighted_file2)
            results.append((file1, file2, similarity, highlighted_file1, highlighted_file2))

    return results

def highlight_similar_parts(text1, text2):
    """Highlight similar parts of two texts."""
    tokens1 = text1.split()
    tokens2 = set(text2.split())
    highlighted_tokens = []
    for token in tokens1:
        if token in tokens2:
            highlighted_tokens.append(f'<span style="background-color: yellow;">{token}</span>')
        else:
            highlighted_tokens.append(token)
    return ' '.join(highlighted_tokens)

def get_file_icon(filename):
    extension = filename.split('.')[-1].lower()
    icon_map = {
        'pdf': 'fas fa-file-pdf',
        'docx': 'fas fa-file-word',
        'doc': 'fas fa-file-word',
        'txt': 'fas fa-file-alt',
        'html': 'fas fa-file-code',
    }
    return icon_map.get(extension, 'fas fa-file')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    connection = create_database_connection()
    users = []
    comparisons = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, username, email, is_admin FROM users")
            users = cursor.fetchall()
            
            cursor.execute("""
                SELECT c.id, f1.filename AS file1, f2.filename AS file2, c.similarity, c.comparison_date, u.username AS user
                FROM comparisons c
                JOIN files f1 ON c.file1_id = f1.id
                JOIN files f2 ON c.file2_id = f2.id
                JOIN users u ON c.user_id = u.id
                ORDER BY c.comparison_date DESC
                LIMIT 10
            """)
            comparisons = cursor.fetchall()
        except Error as e:
            print(f"Error fetching admin dashboard data: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()   
    return render_template('admin_dashboard.html', users=users, comparisons=comparisons)

@app.route('/dashboard')
@login_required
def dashboard():
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)           
            cursor.execute("SELECT COUNT(*) as total FROM comparisons WHERE user_id = %s", (current_user.id,))
            total_comparisons = cursor.fetchone()['total']
            
            cursor.execute("SELECT AVG(similarity) as avg_similarity FROM comparisons WHERE user_id = %s", (current_user.id,))
            avg_similarity_result = cursor.fetchone()['avg_similarity']
            avg_similarity = float(avg_similarity_result) if avg_similarity_result is not None else 0.0
            
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN similarity <= 30 THEN 'Low'
                        WHEN similarity <= 50 THEN 'Medium'
                        WHEN similarity <= 70 THEN 'High'
                        ELSE 'Vety High'
                    END as category,
                    COUNT(*) as count
                FROM comparisons
                WHERE user_id = %s
                GROUP BY category
            """, (current_user.id,))
            similarity_distribution = {row['category']: row['count'] for row in cursor.fetchall()}           
            cursor.execute("""
                SELECT c.id, f1.filename AS file1, f2.filename AS file2, c.similarity, c.comparison_date
                FROM comparisons c
                JOIN files f1 ON c.file1_id = f1.id
                JOIN files f2 ON c.file2_id = f2.id
                WHERE c.user_id = %s
                ORDER BY c.comparison_date DESC
                LIMIT 10
            """, (current_user.id,))
            recent_comparisons = cursor.fetchall()
            
            return render_template('dashboard.html', 
                                   total_comparisons=total_comparisons,
                                   avg_similarity=avg_similarity,
                                   similarity_distribution=json.dumps(similarity_distribution),
                                   recent_comparisons=recent_comparisons)
        except Error as e:
            print(f"Error fetching dashboard data: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()   
    return render_template('dashboard.html', 
                           total_comparisons=0,
                           avg_similarity=0.0,
                           similarity_distribution=json.dumps({}),
                           recent_comparisons=[])

@app.route('/logout')
def logout():
    logout_user()  
    flash('You have been logged out successfully.', 'success') 
    return redirect(url_for('dashboard'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    ensure_upload_folder_exists()

    if request.method == 'POST':
        num_files = int(request.form['num_files'])
        file_paths = []
        for i in range(1, num_files + 1):
            file = request.files.get(f'file_{i}')
            if file:
                file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(file_path)
                file_paths.append(file_path)

        results = compare_files(file_paths, current_user.id)
        return render_template('results.html', results=results, get_file_icon=get_file_icon)
    
    return render_template('index.html')

@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * RECORDS_PER_PAGE

    connection = create_database_connection()
    history_data = []
    total_records = 0
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            if current_user.is_admin:
                count_query = "SELECT COUNT(*) AS total FROM comparisons"
                cursor.execute(count_query)
                total_records = cursor.fetchone()['total']
                
                data_query = """
                SELECT c.id, f1.filename AS file1, f2.filename AS file2, c.similarity, c.comparison_date,
                       f1.upload_date AS file1_upload_date, f2.upload_date AS file2_upload_date,
                       c.highlighted_content1, c.highlighted_content2,
                       u.username AS user
                FROM comparisons c
                JOIN files f1 ON c.file1_id = f1.id
                JOIN files f2 ON c.file2_id = f2.id
                JOIN users u ON c.user_id = u.id
                ORDER BY c.comparison_date DESC
                LIMIT %s OFFSET %s
                """
                cursor.execute(data_query, (RECORDS_PER_PAGE, offset))
            else:
                count_query = "SELECT COUNT(*) AS total FROM comparisons WHERE user_id = %s"
                cursor.execute(count_query, (current_user.id,))
                total_records = cursor.fetchone()['total']
                
                data_query = """
                SELECT c.id, f1.filename AS file1, f2.filename AS file2, c.similarity, c.comparison_date,
                       f1.upload_date AS file1_upload_date, f2.upload_date AS file2_upload_date,
                       c.highlighted_content1, c.highlighted_content2
                FROM comparisons c
                JOIN files f1 ON c.file1_id = f1.id
                JOIN files f2 ON c.file2_id = f2.id
                WHERE c.user_id = %s
                ORDER BY c.comparison_date DESC
                LIMIT %s OFFSET %s
                """
                cursor.execute(data_query, (current_user.id, RECORDS_PER_PAGE, offset))
            
            history_data = cursor.fetchall()
        except Error as e:
            print(f"Error fetching history: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    total_pages = (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE

    return render_template(
        'history.html', 
        history=history_data, 
        page=page, 
        total_pages=total_pages,
        is_admin=current_user.is_admin
    )

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM comparisons WHERE id = %s AND user_id = %s", (id, current_user.id))
            connection.commit()
            flash('Record deleted successfully', 'success')
        except Error as e:
            print(f"Error deleting history entry: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return redirect(url_for('history'))

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html')

@app.route('/submit_contact', methods=['POST'])
@login_required
def submit_contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']    
    connection = create_database_connection()  
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
                (name, email, message)
            )
            connection.commit()
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            print(f"Error saving contact message: {e}")
            flash('There was an error sending your message. Please try again.', 'error')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return redirect(url_for('contact'))  

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            if request.method == 'POST':
                new_username = request.form['username']
                new_email = request.form['email']
                is_admin = 'is_admin' in request.form                
                cursor.execute("""
                    UPDATE users 
                    SET username = %s, email = %s, is_admin = %s 
                    WHERE id = %s
                """, (new_username, new_email, is_admin, user_id))
                connection.commit()
                
                flash('User updated successfully', 'success')
                return redirect(url_for('admin_dashboard'))
            
            else:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if user:
                    return render_template('edit_user.html', user=user)
                else:
                    flash('User not found', 'danger')
                    return redirect(url_for('admin_dashboard'))
                
        except Error as e:
            print(f"Error in edit_user: {e}")
            flash('An error occurred while editing the user', 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if current_user.id == user_id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM comparisons WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM files WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))            
            connection.commit()
            flash('User and all associated data deleted successfully', 'success')
        
        except Error as e:
            print(f"Error in delete_user: {e}")
            connection.rollback()
            flash('An error occurred while deleting the user', 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/view_comparison/<int:comparison_id>')
@login_required
@admin_required
def view_comparison(comparison_id):
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
            SELECT c.id, f1.filename AS file1, f2.filename AS file2, 
                   c.similarity, c.comparison_date, u.username AS user,
                   f1.content AS content1, f2.content AS content2
            FROM comparisons c
            JOIN files f1 ON c.file1_id = f1.id
            JOIN files f2 ON c.file2_id = f2.id
            JOIN users u ON c.user_id = u.id
            WHERE c.id = %s
            """
            cursor.execute(query, (comparison_id,))
            comparison = cursor.fetchone()
            
            if comparison:
                return render_template('view_comparison.html', comparison=comparison)
            else:
                flash('Comparison not found', 'danger')
        
        except Error as e:
            print(f"Error in view_comparison: {e}")
            flash('An error occurred while retrieving the comparison', 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_comparison/<int:comparison_id>', methods=['POST'])
@login_required
@admin_required
def delete_comparison(comparison_id):
    connection = create_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM comparisons WHERE id = %s", (comparison_id,))           
            connection.commit()
            flash('Comparison deleted successfully', 'success')
        
        except Error as e:
            print(f"Error in delete_comparison: {e}")
            connection.rollback()
            flash('An error occurred while deleting the comparison', 'danger')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              description: Username for the new user
              minLength: 3
              maxLength: 50
            email:
              type: string
              format: email
            password:
              type: string
              minLength: 5
    responses:
      200:
        description: User registered successfully
      400:
        description: Registration error
    """
    if request.method == 'POST':
        # Check if the request is in JSON format
        if not request.is_json:
            return jsonify({"error": "Request must be in JSON format"}), 400
        
        try:
            # Get the JSON data from the request
            data = request.get_json()

            # Extract the username, email, and password from the request data
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')

            # Validate the data
            if not username or not password or not email:
                return jsonify({"error": "Username, email, and password are required"}), 400

            if len(username) < 3 or len(username) > 50:
                return jsonify({"error": "Username must be between 3 and 50 characters"}), 400

            if len(password) < 5:
                return jsonify({"error": "Password must be at least 5 characters long"}), 400

            # Connect to the database and check if the username already exists
            connection = create_database_connection()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)

                    # Check if the username already exists
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        return jsonify({"error": "Username already exists"}), 400

                    # Hash the password before storing it
                    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

                    # Insert the new user into the database
                    cursor.execute("INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)", 
                                   (username, email, hashed_password, False))
                    connection.commit()

                    return jsonify({"message": "Account created successfully"}), 201

                except Error as e:
                    print(f"Error during registration: {e}")
                    connection.rollback()
                    return jsonify({"error": "Error during registration"}), 500
                finally:
                    if connection.is_connected():
                        cursor.close()
                        connection.close()

        except Exception as e:
            return jsonify({"error": f"Error: {str(e)}"}), 400

    # For GET request, return registration form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              description: Username of the user
            password:
              type: string
              description: Password of the user
    responses:
      200:
        description: User logged in successfully
      401:
        description: Invalid credentials
    """
    if request.method == 'POST':
        # Check if the request is in JSON format
        if not request.is_json:
            return jsonify({"error": "Request must be in JSON format"}), 400

        try:
            data = request.get_json()
            username = data['username']
            password = data['password']
        except KeyError:
            return jsonify({"error": "Missing required fields: username or password"}), 400

        # Validate if the fields are provided
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        # Connect to the database and authenticate the user
        connection = create_database_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()

                if user and bcrypt.check_password_hash(user['password'], password):
                    user_obj = User(id=user['id'], username=user['username'], 
                                    password=user['password'], is_admin=user['is_admin'])
                    login_user(user_obj)
                    return jsonify({
                        "message": "Logged in successfully", 
                        "is_admin": user['is_admin']
                    }), 200
                else:
                    return jsonify({"error": "Invalid username or password"}), 401

            except Error as e:
                print(f"Error during login: {e}")
                return jsonify({"error": "Server error during login"}), 500
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

    # For GET request, return the login form
    return render_template('login.html')

UPLOAD_FOLDER = r'C:\Users\kyawz\Desktop\plagarism_checker-1\uploads'

@app.route('/compare-files', methods=['POST'])
@login_required
def compare_files_api():
    """
    Compare uploaded files for plagiarism
    ---
    tags:
      - Plagiarism Checking
    parameters:
      - in: formData
        name: files
        required: true
        type: array
        items:
          type: file
        description: List of files to compare. At least two files are required for comparison.
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              files:
                type: array
                items:
                  type: string
                  format: binary
                description: List of files to compare (at least 2 files required)
                minItems: 2
                maxItems: 10
    responses:
      200:
        description: File comparison results
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                results:
                  type: array
                  items:
                    type: object
                    properties:
                      file1:
                        type: string
                        description: First file name
                      file2:
                        type: string
                        description: Second file name
                      similarity:
                        type: number
                        format: float
      400:
        description: Invalid input (e.g., fewer than 2 files)
      500:
        description: Internal server error
    """
    # Validate upload folder exists
    ensure_upload_folder_exists()
    
    # Check if files are present in the request
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    uploaded_files = request.files.getlist('files')
    
    # Validate number of files
    if len(uploaded_files) < 2:
        return jsonify({"error": "At least two files are required for comparison"}), 400
    
    # Validate maximum number of files
    if len(uploaded_files) > 10:
        return jsonify({"error": "Maximum of 10 files allowed for comparison"}), 400
    
    # Validate file types and sizes if needed
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'rtf'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    
    file_paths = []
    try:
        # Process and validate each uploaded file
        for file in uploaded_files:
            if not file or not file.filename:
                continue
            
            # Check file extension
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in ALLOWED_EXTENSIONS:
                return jsonify({
                    "error": f"Invalid file type. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}"
                }), 400
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_FILE_SIZE:
                return jsonify({
                    "error": f"File {filename} exceeds maximum size of 10 MB"
                }), 400
            
            # Save file
            file_path = os.path.join(UPLOAD_FOLDER, f"{current_user.id}_{filename}")
            file.save(file_path)
            file_paths.append(file_path)
        
        # Perform file comparison
        results = compare_files(file_paths, current_user.id)
        
        # Return results as JSON
        return jsonify({
            "message": "Files compared successfully",
            "results": [
                {
                    "file1": os.path.basename(result[0]),
                    "file2": os.path.basename(result[1]),
                    "similarity": round(result[2], 2)
                } for result in results
            ]
        }), 200
    
    except Exception as e:
        # Log the error for server-side tracking
        app.logger.error(f"File comparison error: {str(e)}")
        return jsonify({
            "error": "An error occurred during file comparison", 
            "details": str(e)
        }), 500
    
    finally:
        # Clean up temporary files
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as cleanup_error:
                app.logger.warning(f"Error during file cleanup: {cleanup_error}")

if __name__ == '__main__':
    ensure_upload_folder_exists()
    app.run(debug=True)
