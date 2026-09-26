import os

# app.database builds its engine at import time; tests mock every DB call,
# so any well-formed URL works (no connection is opened).
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chrome_history")
