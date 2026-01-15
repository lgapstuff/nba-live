"""
MySQL database connection manager.
"""
import pymysql
from typing import Optional

from app.config.settings import Config


class DatabaseConnection:
    """
    Manages MySQL database connections.
    """
    
    def __init__(self, config: Config):
        """
        Initialize database connection.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._connection: Optional[pymysql.Connection] = None
    
    def get_connection(self) -> pymysql.Connection:
        """
        Get or create a database connection.
        
        Returns:
            MySQL connection object
        """
        # Always create a fresh connection to avoid cross-request reuse
        self._connection = pymysql.connect(
            host=self.config.MYSQL_HOST,
            port=self.config.MYSQL_PORT,
            user=self.config.MYSQL_USER,
            password=self.config.MYSQL_PASSWORD,
            database=self.config.MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return self._connection
    
    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            try:
                if self._connection.open:
                    self._connection.close()
            finally:
                self._connection = None
    
    def __enter__(self):
        """Context manager entry."""
        return self.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        # Don't close connection, just commit/rollback
        return False




