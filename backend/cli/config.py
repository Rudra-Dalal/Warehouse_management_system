import os

# Default base URL pointing to the FastAPI backend development server
API_BASE_URL = os.getenv("WMS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
