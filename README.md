# PFA 2026 — Steam Review Analyzer

A web application for analyzing Steam game reviews using data visualization and an AI-powered chatbot.

## What It Does

- **Dashboard** — Interactive charts showing review counts, recommendation rates, and key metrics (satisfaction, playtime, helpful votes, etc.) pulled from a Steam reviews database.
- **Game Reviews** — Browse individual games and read their top reviews sorted by helpfulness.
- **AI Chatbot** — Ask questions about the games in the database and get answers powered by a local LLM (Ollama + Gemma 3). The chatbot only uses data from the database — no made-up info.

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite (`steam.db`)
- **Data Analysis:** Pandas
- **AI:** Ollama (Gemma 3 4B)
- **Frontend:** HTML, CSS, JavaScript

## Project Structure

```
pfa/
├── app.py              # Main Flask application (routes, dashboard, chatbot API)
├── Chatbot.py          # AI chatbot class (queries DB, streams responses via Ollama)
├── dashboard.py        # Standalone dashboard data helper
├── requirements.txt    # Python dependencies
├── steam.db            # SQLite database with Steam reviews
├── static/
│   ├── css/            # Stylesheets
│   └── js/             # Frontend JavaScript
└── templates/          # HTML templates (dashboard, reviews, chatbot)
steam.db                # Root copy of the database
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r pfa/requirements.txt
   ```

2. Make sure [Ollama](https://ollama.com) is running locally with the `gemma3:4b` model:
   ```bash
   ollama pull gemma3:4b
   ```

3. Run the app:
   ```bash
   python pfa/app.py
   ```

4. Open `http://localhost:5000` in your browser.

## Notes

- The `steam.db` database contains thousands of Steam game reviews and is required for the app to work.
- The chatbot runs entirely locally through Ollama — no external API keys needed.
