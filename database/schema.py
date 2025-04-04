"""
Schema extraction utilities for SQLite databases.
"""
import pandas as pd
from typing import Dict, List, Any
from .connector import DatabaseConnector
from config import MAX_SAMPLE_ROWS

class SchemaExtractor:
    """Extracts and formats database schema information."""
    
    def __init__(self, db_connector: DatabaseConnector):
        """
        Initialize the schema extractor.
        
        Args:
            db_connector: Database connector instance
        """
        self.db_connector = db_connector
    
    def get_full_schema(self) -> Dict[str, Any]:
        """
        Extract the full database schema including tables, columns, keys and relationships.
        
        Returns:
            Dictionary containing the complete schema information
        """
        tables = self.db_connector.get_table_names()
        schema = {
            "tables": {}
        }
        
        for table in tables:
            # Get table columns
            columns = self.db_connector.get_table_info(table)
            
            # Get foreign keys
            foreign_keys = self.db_connector.get_foreign_keys(table)
            
            # Get sample data
            sample_data = self.db_connector.get_sample_data(table, limit=MAX_SAMPLE_ROWS)
            
            schema["tables"][table] = {
                "columns": columns,
                "foreign_keys": foreign_keys,
                "sample_data": sample_data.to_dict(orient="records") if not sample_data.empty else []
            }
        
        return schema
    
    def get_schema_summary(self) -> str:
        """
        Generate a human-readable summary of the database schema.
        
        Returns:
            String containing the formatted schema summary
        """
        schema = self.get_full_schema()
        summary = "DATABASE SCHEMA:\n\n"
        
        for table_name, table_info in schema["tables"].items():
            summary += f"Table: {table_name}\n"
            
            # Add column information
            summary += "Columns:\n"
            for col in table_info["columns"]:
                pk_marker = "PRIMARY KEY" if col["is_primary_key"] else ""
                null_marker = "NOT NULL" if col["notnull"] else "NULL"
                summary += f"  - {col['name']} ({col['type']}) {pk_marker} {null_marker}\n"
            
            # Add foreign key information
            if table_info["foreign_keys"]:
                summary += "Foreign Keys:\n"
                for fk in table_info["foreign_keys"]:
                    summary += f"  - {fk['from']} -> {fk['table']}.{fk['to']}\n"
            
            # Add sample data preview
            if table_info["sample_data"]:
                summary += "Sample Data:\n"
                
                # Convert to DataFrame for formatting
                df = pd.DataFrame(table_info["sample_data"])
                
                # Format the sample data as a string-based table with limited columns
                # If too many columns, show only the first few
                if len(df.columns) > 5:
                    preview_df = df.iloc[:, :5]
                    col_truncated = True
                else:
                    preview_df = df
                    col_truncated = False
                
                # Format as string table 
                table_str = preview_df.to_string(index=False)
                
                # Add the table string with proper indentation
                for line in table_str.split('\n'):
                    summary += f"  {line}\n"
                
                if col_truncated:
                    summary += "  ... (more columns not shown)\n"
            
            summary += "\n"
        
        return summary
    
    def get_schema_for_prompt(self) -> str:
        """
        Generate a schema representation optimized for LLM prompts.
        
        Returns:
            String containing the schema in a format suitable for LLM context
        """
        schema = self.get_full_schema()
        prompt_schema = "DATABASE SCHEMA:\n\n"
        
        for table_name, table_info in schema["tables"].items():
            prompt_schema += f"Table: {table_name}\n"
            
            # Add CREATE TABLE statement
            prompt_schema += "CREATE TABLE statement:\n"
            create_stmt = "CREATE TABLE " + table_name + " (\n"
            
            # Add columns
            for i, col in enumerate(table_info["columns"]):
                pk_marker = "PRIMARY KEY" if col["is_primary_key"] else ""
                null_marker = "NOT NULL" if col["notnull"] else ""
                
                create_stmt += f"  {col['name']} {col['type']} {pk_marker} {null_marker}"
                
                if i < len(table_info["columns"]) - 1 or table_info["foreign_keys"]:
                    create_stmt += ","
                create_stmt += "\n"
            
            # Add foreign keys
            for i, fk in enumerate(table_info["foreign_keys"]):
                create_stmt += f"  FOREIGN KEY ({fk['from']}) REFERENCES {fk['table']}({fk['to']})"
                if i < len(table_info["foreign_keys"]) - 1:
                    create_stmt += ","
                create_stmt += "\n"
            
            create_stmt += ");\n"
            prompt_schema += create_stmt + "\n"
            
            # Add sample data in INSERT statement format
            if table_info["sample_data"]:
                prompt_schema += "Sample Data:\n"
                
                for row in table_info["sample_data"][:3]:  # Limit to 3 sample rows for prompt
                    col_names = ", ".join(row.keys())
                    col_values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) if v is not None else "NULL" for v in row.values()])
                    prompt_schema += f"INSERT INTO {table_name} ({col_names}) VALUES ({col_values});\n"
                
                if len(table_info["sample_data"]) > 3:
                    prompt_schema += "-- (more rows exist)\n"
            
            prompt_schema += "\n"
        
        # Add relationship descriptions
        prompt_schema += "TABLE RELATIONSHIPS:\n"
        for table_name, table_info in schema["tables"].items():
            for fk in table_info["foreign_keys"]:
                prompt_schema += f"- {table_name}.{fk['from']} references {fk['table']}.{fk['to']}\n"
        
        prompt_schema += "\n"
        return prompt_schema