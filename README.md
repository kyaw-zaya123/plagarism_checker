# Plagiarism Checker System

**Plagiarism Checker System** is a web-based platform for detecting plagiarism in documents. It supports various document formats (DOCX, PDF, TXT, and HTML), generates detailed comparison reports, highlights similarities, and helps users ensure the originality of their content. The system also provides a robust user authentication system, admin roles for managing user data, API access, and secure file handling.

## Project Overview

This project helps individuals and institutions, such as universities and content creators, ensure the originality of their written work. It is designed to identify duplicated or closely matching content between documents, making it particularly useful for:

- **Students**: Checking assignments and research papers for unintentional plagiarism.
- **Content Creators**: Ensuring the originality of articles, blogs, or other written material.
- **Educators**: Analyzing student submissions for copied content from online or offline sources.
- **Businesses**: Verifying the originality of documents like reports, whitepapers, or marketing materials.

### Key Features:
- **Multi-Format Support**: Upload files in DOCX, PDF, TXT, or HTML formats for comparison.
- **Detailed Comparison Reports**: Get a detailed view of text similarities with highlighted sections.
- **User Authentication**: Allows users to create accounts and access their plagiarism check history.
- **Admin Dashboard**: Admins can manage all user data and view comparison history for all users.
- **Privacy and Security**: All user files and history are securely managed, ensuring data protection.

## Installation Instructions

Follow these steps to set up the project on your local machine.

### Prerequisites:
1. **Python 3.12.4** or higher installed.
2. **MySQL** server installed (running on port `3306`).
3. **Flask** (Python web framework).
4. **Other Dependencies** specified in the `requirements.txt` file.

### Step-by-Step Installation:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/kyaw-zaya123/plagarism_checker.git
   cd plagiarism_checker
   ```

2. **Set Up Virtual Environment:**
   Create a virtual environment to install dependencies.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   Install the required packages from `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up MySQL Database:**
   - Open MySQL and create a new database:
     ```sql
     CREATE DATABASE plagiarism_checker;
     ```

5. **Configure the Application:**
   - Update the `config.py` file with your MySQL connection details.
     ```python
     SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://your_username:your_password@localhost/plagiarism_checker'
     ```
   - Set environment variables for any API keys or sensitive information using a `.env` file.

6. **Run the Application:**
   Start the Flask development server:
   ```bash
   flask run
   ```
   The app will be available at `http://localhost:5000`.

## Usage Guide

Once the system is set up, follow these steps to use the plagiarism checker.

### 1. **Register and Login:**
   - Go to `http://localhost:5000/register` to create a new account.
   - After registration, log in to your account.

### 2. **Upload Documents for Plagiarism Check:**
   - Once logged in, navigate to the "File Upload" section.
   - Choose the documents you want to compare. Supported formats include DOCX, PDF, TXT, and HTML.
   - Click the "Compare" button to start the plagiarism check.

### 3. **View Results:**
   - After the plagiarism check is complete, the system will display a detailed comparison report.
   - You will see sections of the document that match any other documents in the database, highlighted for easy review.
   - You can download the report or revisit it later under your history page.

### 4. **Admin Features (For Admin Users):**
   - Admin users can access a dashboard to view all users' comparison history and manage data.
   - Admins have full control over user accounts and file uploads, ensuring system integrity and user security.
