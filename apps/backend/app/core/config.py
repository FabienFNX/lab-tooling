import os

# Use a repo-local sqlite file by default so it's writable in dev containers.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/sqlite/app.db")

# OpenAI API key — required for transcription (Whisper) and processing (GPT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Notion API key — optional, only required when pushing summaries to Notion
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")

# Root directory where recording session folders are stored
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "data/recordings")
