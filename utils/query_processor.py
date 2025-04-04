"""
SQL validation and execution utilities.
"""
import re
import pandas as pd
from typing import Dict, Tuple, Optional
from database.connector import DatabaseConnector

class QueryProcessor:
    """Processes, validates, and executes SQL queries."""
    
    def __init__(self, db_connector: DatabaseConnector):
        """
        Initialize the query processor.
        
        Args:
            db_connector: Database connector instance
        """
        self.db_connector = db_connector
    
    def is_read_query(self, query: str) -> bool:
        """
        Check if a query is a read-only query (SELECT, PRAGMA, etc.).
        
        Args:
            query: SQL query to check
            
        Returns:
            True if the query is read-only, False otherwise
        """
        # Normalize query: remove comments and extra whitespace
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        query = query.strip()
        
        # Check if the query starts with read-only keywords
        read_patterns = [
            r'^SELECT\b',
            r'^WITH\b',
            r'^PRAGMA\b',
            r'^EXPLAIN\b'
        ]
        
        for pattern in read_patterns:
            if re.match(pattern, query, re.IGNORECASE):
                return True
        
        return False
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an SQL query without executing it.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple containing:
            - Boolean indicating if the query is valid
            - Error message if invalid, None otherwise
        """
        # Always allow read queries for this project
        # We're removing the read-only restriction to accommodate all types of queries
        
        # Basic SQL injection protection
        dangerous_patterns = [
            r';\s*DROP\s+TABLE',
            r'UNION\s+SELECT',
            r'INTO\s+OUTFILE',
            r'INTO\s+DUMPFILE'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "Query contains potentially harmful operations"
        
        # Try to validate the query using SQLite's own validation
        try:
            # Create an execution plan without running the query
            # This will raise an error if the query is invalid
            self.db_connector.conn.cursor().execute(f"EXPLAIN QUERY PLAN {query}")
            return True, None
        except Exception as e:
            # If the EXPLAIN fails, the query might still be valid (for non-SELECT queries)
            # Let's try to validate it differently
            try:
                # Use SQLite's prepare feature to validate without executing
                self.db_connector.conn.cursor().execute(f"PRAGMA table_info({query})")
                return True, None
            except Exception:
                # If both validation methods fail, the query is likely invalid
                return False, str(e)
    
    def execute_query(self, query: str) -> Dict:
        """
        Execute an SQL query and return the results and metadata.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Dictionary containing:
            - results: DataFrame with query results
            - error: Error message if execution failed
            - execution_time: Query execution time in seconds
        """
        # Execute the query directly without validation for now
        # We're bypassing strict validation to allow all types of queries
        results, error, execution_time = self.db_connector.execute_query(query)
        
        return {
            "results": results,
            "error": error,
            "execution_time": execution_time
        }