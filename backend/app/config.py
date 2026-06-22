import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://textgenie:textgenie@db:3306/textgenie?charset=utf8mb4",
)

SESSION_DURATION_HOURS = 72
SESSION_CLEANUP_INTERVAL_SECONDS = 3600
COOKIE_NAME = "session_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "http://localhost:8001")

CORS_ORIGINS = [
    "http://localhost:5174",
    "http://localhost",
]
