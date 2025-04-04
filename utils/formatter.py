"""
Formatting utilities for query results and responses.
"""
import pandas as pd
import re
from typing import Dict, Any, Tuple

class ResponseFormatter:
    """Formats query results and LLM responses for display."""
    
    @staticmethod
    def format_query_results(results: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Format query execution results for display.
        
        Args:
            results: Dictionary containing query results, error, and execution time
            
        Returns:
            Tuple containing:
            - Formatted DataFrame for display
            - Metadata dictionary with error and execution time
        """
        df = results["results"]
        metadata = {
            "error": results["error"],
            "execution_time": f"{results['execution_time']:.4f} seconds"
        }
        
        # If there's no data, return an empty DataFrame with metadata
        if df.empty:
            return df, metadata
        
        # Format the DataFrame for display
        # This includes handling large text fields and numeric formatting
        formatted_df = df.copy()
        
        for col in formatted_df.columns:
            # Format numeric columns
            if pd.api.types.is_numeric_dtype(formatted_df[col]):
                # For integer-like columns, don't show decimals
                if formatted_df[col].dropna().apply(lambda x: x == int(x)).all():
                    formatted_df[col] = formatted_df[col].map(lambda x: int(x) if pd.notnull(x) else x)
            
            # Truncate large text fields
            if pd.api.types.is_string_dtype(formatted_df[col]):
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: f"{x[:100]}..." if isinstance(x, str) and len(x) > 100 else x
                )
        
        return formatted_df, metadata
    
    @staticmethod
    def parse_llm_response(response: str) -> Dict[str, str]:
        """
        Parse and structure the LLM response.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Dictionary containing:
            - sql_query: Extracted SQL query
            - explanation: Explanation part of the response
            - educational_notes: Educational notes (if any)
        """
        # Initialize result structure
        result = {
            "sql_query": "",
            "explanation": "",
            "educational_notes": ""
        }
        
        # Extract SQL query from code blocks
        sql_matches = re.findall(r'```sql\s+(.*?)\s+```', response, re.DOTALL)
        if sql_matches:
            result["sql_query"] = sql_matches[0].strip()
        else:
            # Try to find generic code blocks that might contain SQL
            code_matches = re.findall(r'```\s+(.*?)\s+```', response, re.DOTALL)
            if code_matches:
                result["sql_query"] = code_matches[0].strip()
        
        # Extract explanation (text before the SQL block)
        if "```" in response:
            explanation_part = response.split("```")[0].strip()
            result["explanation"] = explanation_part
        
        # Extract educational notes (typically after the SQL block)
        educational_patterns = [
            r'SQL Concept:',
            r'Educational Note:',
            r'Note:',
            r'SQL Tip:'
        ]
        
        for pattern in educational_patterns:
            if pattern in response:
                parts = response.split(pattern)
                if len(parts) > 1:
                    result["educational_notes"] = pattern + parts[1].strip()
                    break
        
        # If no specific educational section was found, check for text after the SQL block
        if not result["educational_notes"] and "```" in response:
            parts = response.split("```")
            if len(parts) > 2:
                after_sql = parts[2].strip()
                if after_sql:
                    result["educational_notes"] = after_sql
        
        return result