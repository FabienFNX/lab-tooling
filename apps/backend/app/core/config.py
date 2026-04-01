import os

# Use a repo-local sqlite file by default so it's writable in dev containers.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/sqlite/app.db")
