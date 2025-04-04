"""
SQLite AI Chatbot using Gradio interface.
"""
import os
import time
import pandas as pd
import gradio as gr
import config
from typing import Dict, List, Tuple, Any

# Import local modules
from database import DatabaseConnector, SchemaExtractor
from llm import GeminiAPI, PromptBuilder
from utils import QueryProcessor, ResponseFormatter

# Initialize global variables
db_connector = None
schema_info = None
llm_api = GeminiAPI()
temp_file_path = None
chat_history = []

def initialize_db_connection(db_file) -> Tuple[bool, str]:
    """
    Initialize database connection from uploaded file.
    """
    global db_connector, schema_info, temp_file_path
    
    try:
        # Create a temporary file to store the uploaded DB
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        timestamp = int(time.time())
        temp_file_path = os.path.join(temp_dir, f"db_{timestamp}.db")
        
        # Get the file path
        db_path = db_file.name
        
        # Copy the file
        import shutil
        shutil.copy(db_path, temp_file_path)
        
        # Test the connection
        db_connector = DatabaseConnector(temp_file_path)
        
        # Extract schema information
        schema_extractor = SchemaExtractor(db_connector)
        schema_info = schema_extractor.get_schema_for_prompt()
        
        return f"✅ Connected to database: {os.path.basename(db_path)}"
    
    except Exception as e:
        return f"❌ Error connecting to database: {str(e)}"

def execute_sql_directly(query: str):
    """Execute an SQL query directly and return results."""
    global db_connector
    
    if not db_connector:
        return None, "No database connection"
    
    try:
        # Execute the query
        df, error, _ = db_connector.execute_query(query)
        return df, error
    except Exception as e:
        return None, str(e)

def process_query(user_query: str, history: List[List[str]]) -> List[List[str]]:
    """
    Process a user's natural language query and update chat history.
    """
    global db_connector, schema_info, llm_api, chat_history
    
    # Check if database is connected
    if not db_connector:
        return history + [[user_query, "Please connect to a database first."]]
    
    # Initialize LLM components
    prompt_builder = PromptBuilder(schema_info)
    
    # Convert chat history to format expected by LLM
    formatted_history = []
    for i, [user_msg, _] in enumerate(history):
        formatted_history.append(prompt_builder.build_user_message(user_msg))
        if i < len(chat_history) and "raw_content" in chat_history[i]:
            formatted_history.append(prompt_builder.build_assistant_message(chat_history[i]["raw_content"]))
    
    # Build messages with conversation history
    messages = prompt_builder.build_messages(user_query, formatted_history)
    
    # Generate response from LLM
    try:
        response = llm_api.generate_response(
            messages, 
            temperature=0.2,
            max_tokens=2048,
            timeout=300
        )
    except Exception as e:
        error_message = f"Error: {str(e)}"
        return history + [[user_query, error_message]]
    
    if not response:
        return history + [[user_query, "Failed to generate response from LLM."]]
    
    # Parse LLM response
    parsed_response = ResponseFormatter.parse_llm_response(response)
    
    # Extract SQL query from response
    sql_query = llm_api.extract_sql_from_response(response)
    
    # Format the response for display
    display_response = response
    
    # If SQL query was extracted, execute it
    if sql_query:
        # Execute the query directly
        results_df, error = execute_sql_directly(sql_query)
        
        if error:
            display_response += f"\n\n**SQL Error**: {error}"
        else:
            # Store the results in chat history for later reference
            result_info = f"\n\n**Query Results:**\n{len(results_df)} row(s) returned"
            display_response += result_info
            
            # Store the raw content for future context
            chat_entry = {
                "raw_content": response,
                "sql_query": sql_query,
                "results": results_df
            }
            chat_history.append(chat_entry)
    else:
        display_response += "\n\n**Error**: Could not extract SQL query from response."
    
    return history + [[user_query, display_response]]

def view_results(history: List[List[str]]) -> gr.Dataframe:
    """Get the most recent query results as a dataframe."""
    if chat_history and "results" in chat_history[-1]:
        return chat_history[-1]["results"]
    return pd.DataFrame()

def view_schema() -> str:
    """Get and format schema for display."""
    global db_connector
    
    if not db_connector:
        return "Please connect to a database first."
    
    schema_extractor = SchemaExtractor(db_connector)
    schema_summary = schema_extractor.get_schema_summary()
    return schema_summary

def reset_state() -> Tuple[List[List[str]], pd.DataFrame]:
    """Reset the application state."""
    global db_connector, schema_info, llm_api, temp_file_path, chat_history
    
    # Clean up database connection
    if db_connector:
        db_connector.disconnect()
        db_connector = None
    
    # Clean up temporary file
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except OSError:
            pass
    
    # Reset variables
    schema_info = None
    llm_api = GeminiAPI()  # Create new instance
    temp_file_path = None
    chat_history = []
    
    # Return empty history and dataframe
    return [], pd.DataFrame()

# Create Gradio interface
with gr.Blocks(title="SQLite AI Chatbot", css="footer {visibility: hidden}") as app:
    gr.Markdown("# SQLite AI Chatbot")
    gr.Markdown(f"Using model: {config.LLM_MODEL_NAME}")
    
    with gr.Row():
        # Main content area (70%)
        with gr.Column(scale=7):
            chatbot = gr.Chatbot(
                height=500,
                label="Chat",
                show_copy_button=True,
                type="messages"
            )
            
            # Query input
            with gr.Row():
                query_input = gr.Textbox(
                    placeholder="Enter your question about the database...",
                    label="Query",
                    lines=3
                )
                
            # Buttons
            with gr.Row():
                submit_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear Chat")
            
            # Results display
            with gr.Accordion("Query Results", open=False):
                results_df = gr.Dataframe(interactive=False)
        
        # Sidebar (30%)
        with gr.Column(scale=3):
            # Database connection
            with gr.Group():
                gr.Markdown("### Database Connection")
                db_file = gr.File(label="Upload SQLite Database")
                connect_btn = gr.Button("Connect to Database")
                connection_status = gr.Textbox(label="Status", interactive=False)
            
            # View schema
            with gr.Group():
                gr.Markdown("### Database Schema")
                view_schema_btn = gr.Button("View Schema")
                schema_display = gr.Textbox(
                    label="Schema",
                    interactive=False,
                    lines=10
                )
            
            # Example queries
            with gr.Accordion("Example Queries", open=True):
                gr.Markdown("""
                ### Basic Queries:
                - List all tables in the database
                - Show me all fields in the FILM table
                - How many customers are there in total?
                
                ### Intermediate Queries:
                - Find all films in English language
                - List the top 5 customers with the most rentals
                - Find films that cost more than $20 to replace
                
                ### Complex Queries:
                - Which customers have rented films but never made a payment?
                - List films that have been rented more than 5 times, sorted by popularity
                - Find actors who have appeared in films across multiple categories
                """)
            
            # Reset
            reset_btn = gr.Button("Reset All", variant="stop")
    
    # Set up event handlers
    connect_btn.click(initialize_db_connection, inputs=db_file, outputs=connection_status)
    submit_btn.click(process_query, inputs=[query_input, chatbot], outputs=[chatbot])
    submit_btn.click(lambda: "", inputs=None, outputs=query_input)  # Clear input after sending
    submit_btn.click(view_results, inputs=chatbot, outputs=results_df)
    clear_btn.click(lambda: [], inputs=None, outputs=chatbot)
    view_schema_btn.click(view_schema, inputs=None, outputs=schema_display)
    reset_btn.click(reset_state, inputs=None, outputs=[chatbot, results_df])
    reset_btn.click(lambda: "", inputs=None, outputs=[connection_status, schema_display])

# Run the app
if __name__ == "__main__":
    app.launch(share=False)