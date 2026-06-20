import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://textgenie:textgenie@db:3306/textgenie",
)

SESSION_DURATION_HOURS = 72
SESSION_CLEANUP_INTERVAL_SECONDS = 3600
COOKIE_NAME = "session_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

CORS_ORIGINS = [
    "http://localhost:5174",
    "http://localhost",
]
