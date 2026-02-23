import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NUM_RESULTS = 5

# Chọn LLM: True = Groq (LLaMA 3.3 70B), False = Gemini
USE_GROQ = bool(GROQ_API_KEY)
