"""
Configuration settings for the SQLite AI Chatbot.
"""
import os
import streamlit as st

# Try to get API keys from Streamlit secrets (for deployment)
# or fall back to environment variables (for local development)
try:
    # When deployed on Streamlit Cloud
    API_KEYS = [
        st.secrets["OPENROUTER_API_KEY_1"],
        st.secrets["OPENROUTER_API_KEY_2"],
        st.secrets["OPENROUTER_API_KEY_3"],
        st.secrets["OPENROUTER_API_KEY_4"]
    ]
except Exception:
    # When running locally - use environment variables or hardcoded keys for development
    # In production, these keys will come from Streamlit secrets
    API_KEYS = [
        os.environ.get("OPENROUTER_API_KEY_1", ""),
        os.environ.get("OPENROUTER_API_KEY_2", ""),
        os.environ.get("OPENROUTER_API_KEY_3", ""),
        os.environ.get("OPENROUTER_API_KEY_4", "")
    ]

# Filter out any empty keys
API_KEYS = [key for key in API_KEYS if key]

# Ensure we have at least one key
if not API_KEYS:
    # Fallback for development - never commit these to GitHub
    API_KEYS = [
        "placeholder-key-will-be-replaced-by-secrets"
    ]

LLM_MODEL_NAME = "google/gemini-2.5-pro-exp-03-25:free"  # Gemini 2.5 Pro model

# Application settings
MAX_HISTORY_LENGTH = 10  # Max number of conversation turns to keep
MAX_SAMPLE_ROWS = 5  # Number of sample rows to include per table
MAX_RESULT_ROWS = 100  # Max number of rows to display in results