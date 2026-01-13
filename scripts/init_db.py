"""
Database initialization script.
Run this to create database tables.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import Config
from app.infrastructure.database.migrations import create_tables

if __name__ == "__main__":
    print("Initializing database tables...")
    config = Config()
    try:
        create_tables(config)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)




