"""
Constructs effective prompts for the LLM that include schema context.
"""
from typing import List, Dict, Any
import config

class PromptBuilder:
    """Builds prompts for the LLM that include database schema information."""
    
    def __init__(self, schema: str):
        """
        Initialize the prompt builder.
        
        Args:
            schema: Formatted database schema information
        """
        self.schema = schema
    
    def build_system_message(self) -> Dict[str, str]:
        """
        Create the system message with instructions and schema information.
        
        Returns:
            Dictionary with role and content for the system message
        """
        system_content = f"""You are a specialized SQL assistant that helps users interact with a SQLite database. Your task is to convert natural language questions into correct SQL queries.

DATABASE SCHEMA:
{self.schema}

INSTRUCTIONS:
1. Always respond with a valid SQLite SQL query that answers the user's question
2. Always place your SQL query inside triple backticks with the sql language tag like this: ```sql
3. Always add a brief explanation of what the query does and any important SQL concepts used
4. Be precise and use only tables and columns that exist in the schema
5. Format SQL using proper indentation and line breaks for readability
6. You MUST include the SQL query in your response

EXAMPLE RESPONSE FORMAT:
```sql
SELECT column_name FROM table_name WHERE condition;
```

This query [explanation of what the query does]. It uses [mention any important SQL concepts].
"""
        return {"role": "system", "content": system_content}
    
    def build_user_message(self, query: str) -> Dict[str, str]:
        """
        Create a user message for the given query.
        
        Args:
            query: User's natural language query
            
        Returns:
            Dictionary with role and content for the user message
        """
        return {"role": "user", "content": query}
    
    def build_assistant_message(self, content: str) -> Dict[str, str]:
        """
        Create an assistant message with the given content.
        
        Args:
            content: Assistant's response content
            
        Returns:
            Dictionary with role and content for the assistant message
        """
        return {"role": "assistant", "content": content}
    
    def build_messages(self, query: str, conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Build the complete messages array for the API request, including conversation history.
        
        Args:
            query: User's natural language query
            conversation_history: Previous messages in the conversation
            
        Returns:
            Complete messages array for the API request
        """
        # Start with the system message
        messages = [self.build_system_message()]
        
        # Add conversation history if provided
        if conversation_history:
            # Add only the last MAX_HISTORY_LENGTH turns to avoid token limits
            for msg in conversation_history[-config.MAX_HISTORY_LENGTH*2:]:
                messages.append(msg)
        
        # Add the current user query
        messages.append(self.build_user_message(query))
        
        return messages