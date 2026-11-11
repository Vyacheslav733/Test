import os

BASE_URL = os.getenv("DEMOQA_BASE_URL", "https://demoqa.com").rstrip("/")
TIMEOUT_MS = int(os.getenv("UI_TIMEOUT_MS", "25000"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "25"))
