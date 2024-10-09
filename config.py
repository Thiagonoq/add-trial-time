import sys
import dotenv
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent

dotenv_file = base_path / '.env'
dotenv.load_dotenv(dotenv_path=dotenv_file, override=True)

ABS_PATH = Path(os.getcwd())

DEV_MODE = os.getenv("DEV_MODE") == "true"

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_NAME = 'videoai'

GPT_API_KEY = os.getenv("GPT_API_KEY")