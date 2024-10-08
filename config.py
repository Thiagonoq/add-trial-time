import dotenv
import os
from pathlib import Path

dotenv.load_dotenv()

DEV_MODE = os.getenv("DEV_MODE") == "true"

ABS_PATH = Path(os.getcwd())

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_NAME = 'videoai'

GPT_API_KEY = os.getenv("GPT_API_KEY")