"""
Database connection and query execution module.
"""
import sqlite3
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
import threading
import re

class DatabaseConnector:
    """Handles SQLite database connections and query execution."""
    
    def __init__(self, db_path: str):
        """
        Initialize the database connector.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._local.conn = None
        self.connect()
    
    def connect(self) -> None:
        """Establish connection to the SQLite database."""
        try:
            self._local.conn = sqlite3.connect(self.db_path)
            # Enable foreign key constraints
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            print(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            print(f"Database connection error: {str(e)}")
            raise Exception(f"Database connection error: {str(e)}")
    
    def disconnect(self) -> None:
        """Close the database connection if it exists."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    @property
    def conn(self):
        """Get the thread-local connection, creating it if necessary."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self.connect()
        return self._local.conn
    
    def execute_query(self, query: str) -> Tuple[pd.DataFrame, Optional[str], float]:
        """
        Execute an SQL query and return the results as a DataFrame.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Tuple containing:
            - DataFrame with query results
            - Error message (if any)
            - Execution time in seconds
        """
        import time
        
        error = None
        df = pd.DataFrame()
        start_time = time.time()
        
        # Clean up the query and split if multiple statements
        # Remove comments and extra whitespace
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        query = query.strip()
        
        # Split by semicolons and take only the first statement
        query_parts = query.split(';')
        if len(query_parts) > 1:
            # If multiple statements, use only the first one
            query = query_parts[0].strip() + ";"
            print(f"Multiple statements detected. Using only: {query}")
        
        try:
            # Check if it's a PRAGMA query
            is_pragma = query.lower().strip().startswith("pragma")
            # Check if it's a SELECT query (read operation)
            is_select = query.lower().strip().startswith("select") or query.lower().strip().startswith("with")
            
            print(f"Executing query: {query}")
            
            if is_pragma:
                # Special handling for PRAGMA queries
                cursor = self.conn.cursor()
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=columns)
                print(f"PRAGMA query returned {len(df)} rows")
            elif is_select:
                df = pd.read_sql_query(query, self.conn)
                print(f"SELECT query returned {len(df)} rows")
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                cursor = self.conn.cursor()
                cursor.execute(query)
                self.conn.commit()
                
                # Get affected row count
                row_count = cursor.rowcount
                df = pd.DataFrame([{"message": f"Query executed successfully. {row_count} row(s) affected."}])
                print(f"Non-SELECT query affected {row_count} rows")
                
        except sqlite3.Error as e:
            error = str(e)
            print(f"Query execution error: {error}")
        
        execution_time = time.time() - start_time
        
        return df, error, execution_time
    
    def get_table_names(self) -> List[str]:
        """
        Get a list of all table names in the database.
        
        Returns:
            List of table names
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {tables}")
        return tables
    
    def get_table_info(self, table_name: str) -> List[Dict]:
        """
        Get column information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries containing column information
        """
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        
        columns = []
        for row in cursor.fetchall():
            column = {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": row[3],
                "default_value": row[4],
                "is_primary_key": row[5] == 1
            }
            columns.append(column)
            
        return columns
    
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        Get foreign key information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries containing foreign key information
        """
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        
        foreign_keys = []
        for row in cursor.fetchall():
            fk = {
                "id": row[0],
                "seq": row[1],
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_update": row[5],
                "on_delete": row[6],
                "match": row[7]
            }
            foreign_keys.append(fk)
            
        return foreign_keys
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """
        Get sample data from a table.
        
        Args:
            table_name: Name of the table
            limit: Maximum number of rows to return
            
        Returns:
            DataFrame containing sample data
        """
        try:
            return pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {limit}", self.conn)
        except sqlite3.Error:
            return pd.DataFrame()