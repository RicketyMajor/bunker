import os
from pathlib import Path
from dotenv import load_dotenv

# Try to load .env from the project root if it exists
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

BASE_URL = os.environ.get("BUNKER_API_URL", "http://localhost:8009")
