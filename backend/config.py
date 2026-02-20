import os
from dotenv import load_dotenv

load_dotenv()

# Dùng Groq thay Gemini (miễn phí, nhanh)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
COLLECTION_NAME = "vietnam_history"
NUM_RESULTS = 5
USE_GROQ = True  # True = dùng Groq, False = dùng Gemini