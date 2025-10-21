# File Compare Web Application

A web-based application built with Django for comparing the content of two files. The tool provides a user-friendly interface to upload files and visualize the differences between them.

![File Compare App](https://img.shields.io/badge/Django-3.2-green.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Web-based Interface**: Clean and intuitive browser interface for file comparison
- **File Upload Support**: Upload two files of various types for comparison
- **Visual Difference Highlighting**: Clear visualization of differences between files
- **Side-by-Side Comparison**: View both files simultaneously with differences highlighted
- **Django Backend**: Robust and secure Django framework foundation
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtualenv (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kyaw-zaya123/checking.git
   cd checking

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**
   ```bash
   python manage.py migrate

4. **Run migrations**
   ```bash
   Run migrations

5. **Create superuser (optional, for admin access)**
   ```bash
   python manage.py createsuperuser

6. **Start development server**
   ```bash
   python manage.py runserver

7. **Access the application**
   Open your browser and navigate to http://127.0.0.1:8000/

## 🎯 Usage 
- **Access the Application**: Open your web browser and navigate to the application URL
- **Upload Files**: Use the file input fields to select two files you want to compare
- **Initiate Comparison**: Click the "Compare" button to analyze the files
- **Review Results**: View the side-by-side comparison with differences highlighted
- **Download Results**: Option to download the comparison report (if implemented)

## Supported File Types
Text files (.txt, .docx, .pdf)


