"""
Main Streamlit application for the SQLite AI Chatbot.
"""
import os
import time
import streamlit as st
import pandas as pd
import config
from typing import Dict, List, Tuple, Any

# Import local modules
from database import DatabaseConnector, SchemaExtractor
from llm import GeminiAPI, PromptBuilder
from utils import QueryProcessor, ResponseFormatter

# Set page configuration
st.set_page_config(
    page_title="SQLite AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Application styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-text {
        font-size: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #f0f2f6;
    }
    .assistant-message {
        background-color: #e6f3ff;
    }
    .sql-code {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-family: monospace;
    }
    .explanation {
        margin: 1rem 0;
    }
    .educational-notes {
        background-color: #f9f9e0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .results-section {
        background-color: #e8f4ea;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .footer {
        margin-top: 2rem;
        text-align: center;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "db_connected" not in st.session_state:
    st.session_state.db_connected = False

if "schema_info" not in st.session_state:
    st.session_state.schema_info = None

if "temp_file_path" not in st.session_state:
    st.session_state.temp_file_path = None

if "db_connector" not in st.session_state:
    st.session_state.db_connector = None

if "llm_api" not in st.session_state:
    st.session_state.llm_api = GeminiAPI()

if "processing_query" not in st.session_state:
    st.session_state.processing_query = False


def initialize_db_connection(db_file) -> Tuple[bool, str]:
    """
    Initialize database connection.
    
    Args:
        db_file: Uploaded database file
        
    Returns:
        Tuple containing:
        - Boolean indicating if connection was successful
        - Error message if connection failed
    """
    try:
        # Create a temporary file to store the uploaded DB
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        timestamp = int(time.time())
        temp_file_path = os.path.join(temp_dir, f"db_{timestamp}.db")
        
        # Save the uploaded file
        with open(temp_file_path, "wb") as f:
            f.write(db_file.getbuffer())
        
        # Store the file path in session state
        st.session_state.temp_file_path = temp_file_path
        
        # Test the connection
        db_connector = DatabaseConnector(temp_file_path)
        st.session_state.db_connector = db_connector
        
        # Extract schema information
        schema_extractor = SchemaExtractor(db_connector)
        schema_info = schema_extractor.get_schema_for_prompt()
        st.session_state.schema_info = schema_info
        
        return True, "Database connection successful"
    
    except Exception as e:
        return False, f"Error connecting to database: {str(e)}"


def execute_sql_directly(query: str):
    """Execute an SQL query directly and return results."""
    if not st.session_state.db_connector:
        return None, "No database connection"
    
    try:
        # Execute the query
        df, error, _ = st.session_state.db_connector.execute_query(query)
        return df, error
    except Exception as e:
        return None, str(e)


def process_user_query(query: str) -> Dict[str, Any]:
    """
    Process a user's natural language query.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary containing response data
    """
    try:
        # Set processing flag
        st.session_state.processing_query = True
        
        # Initialize LLM components
        llm_api = st.session_state.llm_api
        prompt_builder = PromptBuilder(st.session_state.schema_info)
        
        # Convert chat history to format expected by LLM
        formatted_history = []
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                formatted_history.append(prompt_builder.build_user_message(msg["content"]))
            elif msg["role"] == "assistant" and "raw_content" in msg:
                formatted_history.append(prompt_builder.build_assistant_message(msg["raw_content"]))
        
        # Build messages with conversation history
        messages = prompt_builder.build_messages(query, formatted_history)
        
        # Generate response from LLM with extended timeout
        try:
            with st.spinner("Thinking... (this might take a while for complex queries)"):
                response = llm_api.generate_response(
                    messages, 
                    temperature=0.2,  # Lower temperature for more deterministic SQL generation
                    max_tokens=2048,  # Increased token limit for complex queries
                    timeout=300  # 5 minutes timeout
                )
        except Exception as e:
            print(f"LLM response generation error: {str(e)}")
            st.session_state.processing_query = False
            return {
                "success": False,
                "error": "LLM request timed out. Try a simpler query or break this into smaller steps."
            }
        
        if response:
            # Parse LLM response
            parsed_response = ResponseFormatter.parse_llm_response(response)
            
            # Extract SQL query from response
            sql_query = llm_api.extract_sql_from_response(response)
            
            # If SQL query was extracted, execute it
            if sql_query:
                print(f"Extracted SQL query: {sql_query}")
                
                # Execute the query directly
                results_df, error = execute_sql_directly(sql_query)
                
                if error:
                    st.session_state.processing_query = False
                    return {
                        "success": False,
                        "error": f"SQL execution error: {error}",
                        "llm_response": response,
                        "parsed_response": parsed_response,
                        "sql_query": sql_query
                    }
                
                st.session_state.processing_query = False
                return {
                    "success": True,
                    "llm_response": response,
                    "parsed_response": parsed_response,
                    "query_results": results_df,
                    "sql_query": sql_query
                }
            else:
                st.session_state.processing_query = False
                return {
                    "success": False,
                    "error": "Could not extract SQL query from LLM response",
                    "llm_response": response,
                    "parsed_response": parsed_response
                }
        else:
            st.session_state.processing_query = False
            return {
                "success": False,
                "error": "Failed to generate response from LLM"
            }
    
    except Exception as e:
        print(f"Error in process_user_query: {str(e)}")
        st.session_state.processing_query = False
        return {
            "success": False,
            "error": f"Error processing query: {str(e)}"
        }


def main():
    """Main application function."""
    # Display header
    st.markdown("<h1 class='main-header'>SQLite AI Chatbot</h1>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Chat with your SQLite database using natural language.</p>", unsafe_allow_html=True)
    
    # Sidebar for database connection
    with st.sidebar:
        st.markdown("<h2 class='subheader'>Database Connection</h2>", unsafe_allow_html=True)
        
        # Display LLM model info
        
        if not st.session_state.db_connected:
            st.markdown("<p class='info-text'>Upload a SQLite database file:</p>", unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Choose a SQLite database file", type=["db", "sqlite", "sqlite3"])
            
            if uploaded_file is not None:
                if st.button("Connect to Database"):
                    with st.spinner("Connecting to database..."):
                        success, message = initialize_db_connection(uploaded_file)
                        
                        if success:
                            st.session_state.db_connected = True
                            st.success(message)
                        else:
                            st.error(message)
        else:
            st.success("Database connected!")
            
            # Display schema information
            if st.button("View Database Schema"):
                # Get and format schema for display
                schema_extractor = SchemaExtractor(st.session_state.db_connector)
                schema_summary = schema_extractor.get_schema_summary()
                
                with st.expander("Database Schema", expanded=True):
                    st.text(schema_summary)
            
            # Add reset button for LLM
            if st.button("Reset LLM State"):
                # Cancel any current LLM request
                if st.session_state.llm_api:
                    st.session_state.llm_api.cancel_current_request()
                
                # Reset processing flag
                st.session_state.processing_query = False
                
                # Create a new API instance
                st.session_state.llm_api = GeminiAPI()
                
                st.success("LLM state has been reset. You can try your query again.")
            
            # Option to disconnect
            if st.button("Disconnect Database"):
                # Cancel any pending LLM requests
                if st.session_state.llm_api:
                    st.session_state.llm_api.cancel_current_request()
                
                if st.session_state.db_connector:
                    st.session_state.db_connector.disconnect()
                
                # Clean up the temporary file if it exists
                if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
                    try:
                        os.remove(st.session_state.temp_file_path)
                    except OSError:
                        pass
                
                # Reset session state
                st.session_state.db_connected = False
                st.session_state.schema_info = None
                st.session_state.chat_history = []
                st.session_state.temp_file_path = None
                st.session_state.db_connector = None
                st.session_state.processing_query = False
                st.session_state.llm_api = GeminiAPI()
                
                st.success("Database disconnected!")
                st.rerun()
    
    # Main content area
    if st.session_state.db_connected:
        # Chat interface
        st.markdown("<h2 class='subheader'>Chat with Your Database</h2>", unsafe_allow_html=True)
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div class='chat-message user-message'><strong>You:</strong> {message['content']}</div>", unsafe_allow_html=True)
            else:
                # Extract and display components if available
                explanation = message.get("explanation", "")
                sql_query = message.get("sql_query", "")
                educational_notes = message.get("educational_notes", "")
                
                # Display AI response with structured sections
                st.markdown(f"<div class='chat-message assistant-message'><strong>AI:</strong> {explanation}</div>", unsafe_allow_html=True)
                
                if sql_query:
                    st.markdown("<div class='sql-code'>", unsafe_allow_html=True)
                    st.code(sql_query, language="sql")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                if educational_notes:
                    st.markdown(f"<div class='educational-notes'>{educational_notes}</div>", unsafe_allow_html=True)
                
                # Display query results if available
                if "query_results" in message and not message["query_results"].empty:
                    st.markdown("<div class='results-section'><strong>Query Results:</strong></div>", unsafe_allow_html=True)
                    st.dataframe(message["query_results"])
                    
                    # Show the number of rows
                    row_count = len(message["query_results"])
                    st.markdown(f"<div class='info-text'>{row_count} row(s) returned</div>", unsafe_allow_html=True)
        
        # Show processing indicator
        if st.session_state.processing_query:
            st.warning("Processing previous query... Please wait or click 'Reset LLM State' in the sidebar if it takes too long.")
        
        # Chat input
        user_query = st.text_area("Enter your question about the database:", height=100)
        
        send_button = st.button("Send", disabled=st.session_state.processing_query)
        
        if send_button:
            if user_query:
                # Cancel any existing request
                if st.session_state.llm_api:
                    st.session_state.llm_api.cancel_current_request()
                
                # Add user message to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_query
                })
                
                # Process user query
                response_data = process_user_query(user_query)
                
                # Handle response
                if response_data["success"]:
                    # Parse the response components
                    parsed_response = response_data.get("parsed_response", {})
                    explanation = parsed_response.get("explanation", "")
                    sql_query = response_data.get("sql_query", "")
                    educational_notes = parsed_response.get("educational_notes", "")
                    
                    # Add to chat history with additional metadata
                    assistant_message = {
                        "role": "assistant",
                        "raw_content": response_data["llm_response"],  # Store raw response for context
                        "explanation": explanation,
                        "sql_query": sql_query,
                        "educational_notes": educational_notes
                    }
                    
                    # Add query results if available
                    if "query_results" in response_data:
                        assistant_message["query_results"] = response_data["query_results"]
                    
                    st.session_state.chat_history.append(assistant_message)
                else:
                    # Display error message
                    error_message = response_data.get("error", "An unknown error occurred")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "explanation": f"Error: {error_message}"
                    })
                
                # Rerun to update the display
                st.rerun()
    else:
        # Display instructions if no database is connected
        st.info("Please connect to a database using the sidebar to start chatting.")
        
        # Example queries
        with st.expander("Example Queries for Film Database"):
            st.markdown("""
            This chatbot works with any SQLite database. Here are some example queries for the film database:
            
            ### Basic Queries:
            - List all tables in the database
            - Show me all fields in the FILM table
            - How many customers are there in total?
            - List all film categories
            
            ### Intermediate Queries:
            - Find all films in English language
            - List the top 5 customers with the most rentals
            - Show all staff members and which stores they work at
            - Find films that cost more than $20 to replace
            
            ### Complex Queries:
            - Which customers have rented films but never made a payment?
            - List films that have been rented more than 5 times, sorted by popularity
            - Find the average rental duration by film category
            - Which store has generated the most revenue from rentals?
            """)
    
    # Footer
    st.markdown("<div class='footer'>SQLite AI Chatbot - Streamlit</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()