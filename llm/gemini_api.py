"""
Gemini API integration via OpenRouter with key rotation.
"""
import requests
import json
import re
import threading
import time
from typing import List, Dict, Any, Optional
import config
import random

class GeminiAPI:
    """Handles communication with the Gemini model via OpenRouter API."""
    
    def __init__(self):
        """Initialize the Gemini API client."""
        self.api_keys = config.API_KEYS
        self.current_key_index = 0
        self.model = config.LLM_MODEL_NAME
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self._local = threading.local()
        self._lock = threading.Lock()
        
        if not self.api_keys:
            raise ValueError("No OpenRouter API keys available. Please configure API keys.")
    
    def _get_next_key(self) -> str:
        """Get the next API key using round-robin rotation."""
        with self._lock:
            key = self.api_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            return key
    
    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.2, 
        max_tokens: int = 2048,
        timeout: int = 300  # 5 minutes timeout for complex queries
    ) -> Optional[str]:
        """
        Send a request to the Gemini model and get a response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            Generated response text or None if request failed
        """
        # Cancel any existing request
        if hasattr(self._local, 'current_request') and self._local.current_request:
            print("Cancelling previous request...")
            self._local.current_request = None
        
        # Try all available keys if needed
        errors = []
        
        for attempt in range(len(self.api_keys)):
            api_key = self._get_next_key()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://sql-ai-chatbot.streamlit.app",  # Update when deployed
                "X-Title": "SQLite AI Chatbot"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "text"}  # Ensure plain text response
            }
            
            try:
                session = requests.Session()
                self._local.current_request = session
                
                print(f"Sending request to Gemini model with API key #{attempt+1}")
                
                response = session.post(self.api_url, headers=headers, data=json.dumps(data), timeout=timeout)
                response.raise_for_status()  # Raise exception for HTTP errors
                
                response_data = response.json()
                
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    content = response_data["choices"][0]["message"]["content"]
                    print(f"Response content length: {len(content)}")
                    return content
                
                print("No content in response choices, trying next key")
                errors.append(f"No content in response (key #{attempt+1})")
                
            except requests.exceptions.RequestException as e:
                error_msg = f"API request error with key #{attempt+1}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                time.sleep(1)  # Brief pause before trying next key
            except (KeyError, json.JSONDecodeError) as e:
                error_msg = f"API response parsing error with key #{attempt+1}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
            finally:
                if hasattr(self._local, 'current_request'):
                    self._local.current_request = None
        
        # If we get here, all keys have failed
        print(f"All API keys failed: {', '.join(errors)}")
        return None
    
    def extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL query from the LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted SQL query or empty string if not found
        """
        # Look for SQL code blocks
        if "```sql" in response:
            parts = response.split("```sql")
            if len(parts) > 1:
                sql_parts = parts[1].split("```")
                if sql_parts:
                    return self._clean_sql_query(sql_parts[0].strip())
        
        # Look for generic code blocks that might contain SQL
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                for i in range(1, len(parts), 2):  # Check odd-indexed parts (inside code blocks)
                    if i < len(parts):
                        potential_sql = parts[i].strip()
                        # Check if it looks like SQL
                        if re.search(r'SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA', potential_sql, re.IGNORECASE):
                            return self._clean_sql_query(potential_sql)
        
        # If no code blocks found, try to extract based on SQL keywords
        sql_keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", 
                        "INSERT INTO", "UPDATE", "DELETE FROM", "PRAGMA"]
        
        lines = response.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            line_upper = line.strip().upper()
            
            # Check if this line starts with SQL keywords
            if any(line_upper.startswith(keyword) for keyword in sql_keywords):
                in_sql = True
                sql_lines.append(line)
            elif in_sql and line.strip():
                sql_lines.append(line)
            elif in_sql and not line.strip():
                in_sql = False
        
        if sql_lines:
            return self._clean_sql_query('\n'.join(sql_lines).strip())
        
        return ""
    
    def _clean_sql_query(self, query: str) -> str:
        """
        Clean and sanitize SQL query to ensure it works with SQLite.
        
        Args:
            query: Raw SQL query
            
        Returns:
            Cleaned SQL query
        """
        # Remove multiple SQL statements if present (keep only the first one)
        # This prevents "You can only execute one statement at a time" errors
        
        # First, remove comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # Check if we have multiple PRAGMA statements
        if query.upper().count("PRAGMA") > 1:
            # For PRAGMA queries, keep only the first one
            pragma_parts = re.split(r'(PRAGMA\s+[^;]+;)', query, flags=re.IGNORECASE)
            non_empty_parts = [p for p in pragma_parts if p.strip()]
            if non_empty_parts:
                return non_empty_parts[0].strip()
        
        # For regular queries, split by semicolons and take first complete statement
        if ";" in query:
            parts = query.split(';')
            if parts[0].strip():
                return parts[0].strip() + ";"
        
        return query
    
    def cancel_current_request(self):
        """Cancel the current API request if one is in progress."""
        if hasattr(self._local, 'current_request') and self._local.current_request:
            self._local.current_request = None
            print("Manually cancelled current request")