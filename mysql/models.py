from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str
    password: str
    created_at: datetime

    @classmethod
    def create_table(cls, cursor: Any) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@dataclass
class File:
    id: int
    filename: str
    content: str
    upload_date: datetime

    @classmethod
    def create_table(cls, cursor: Any) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@dataclass
class Comparison:
    id: int
    user_id: Optional[int]
    file1_id: Optional[int]
    file2_id: Optional[int]
    similarity: float
    comparison_date: datetime

    @classmethod
    def create_table(cls, cursor: Any) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparisons (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                file1_id INT,
                file2_id INT,
                similarity FLOAT NOT NULL,
                comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (file1_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (file2_id) REFERENCES files(id) ON DELETE CASCADE,
                INDEX (user_id),
                INDEX (file1_id),
                INDEX (file2_id)
            )
        """)

@dataclass
class ContactMessage:
    id: int
    name: str
    email: str
    message: str
    submitted_at: datetime

    @classmethod
    def create_table(cls, cursor: Any) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@dataclass
class ApiKey:
    id: int
    user_id: Optional[int]
    api_key: str
    created_at: datetime
    expires_at: Optional[datetime]
    active: bool = True

    @classmethod
    def create_table(cls, cursor: Any) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                api_key VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

def initialize_database(cursor: Any) -> None:
    """Create all database tables in the correct order to satisfy foreign key constraints."""
    User.create_table(cursor)
    File.create_table(cursor)
    Comparison.create_table(cursor)
    ContactMessage.create_table(cursor)
    ApiKey.create_table(cursor)

class DatabaseManager:
    def __init__(self, connection: Any):
        self.connection = connection
        self.cursor = connection.cursor(dictionary=True)

    def create_tables(self) -> None:
        """Initialize all tables in the database."""
        initialize_database(self.cursor)
        self.connection.commit()

    def create_database(self, db_name: str) -> None:
        """Create the database if it doesn't exist."""
        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        self.connection.commit()

    def close(self) -> None:
        """Close the connection."""
        self.cursor.close()
        self.connection.close()
