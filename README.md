# SQLite AI Chatbot

A natural language interface that lets you query SQLite databases using plain English. Powered by Google's Gemini 2.5 Pro, this application translates your questions into SQL, executes queries, and presents the results in an intuitive format.

## Features

- **Natural Language to SQL**: Ask questions about your database in plain English
- **SQL Translation**: See the generated SQL query with educational explanations
- **Support for Complex Queries**: Handles joins, aggregations, subqueries, and complex filters
- **Universal Compatibility**: Works with any SQLite database
- **Educational Tool**: Learn SQL concepts through explanations of generated queries

## Examples

### Basic Queries
- "List all tables in the database"
- "How many customers are there in total?"

### Intermediate Queries
- "Find all films that cost more than $20 to replace"
- "List the top 5 customers with the most rentals"

### Complex Analytical Queries
- "Find customers who have rented 'Action' films but never 'Comedy' films"
- "Which store has generated the most revenue from rentals?"
- "List films rented more than 5 times, sorted by popularity"

## How to Use

1. Upload your SQLite database file (.db, .sqlite, .sqlite3)
2. Type your question in natural language
3. View the SQL query, explanation, and results
4. Continue with follow-up questions

## Local Development

### Prerequisites
- Python 3.8+
- Streamlit

### Setup

1. Clone the repository:
```bash
git clone https://github.com/thenotsotalentedcoder/sqlite-chatbot.git
cd sqlite-chatbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.streamlit/secrets.toml` file with OpenRouter API keys.

4. Run the application:
```bash
streamlit run app.py
```

## Technology

- Frontend: Streamlit
- NLP: Google Gemini 2.5 Pro via OpenRouter
- Database: SQLite
