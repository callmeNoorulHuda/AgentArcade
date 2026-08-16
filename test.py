import os
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GROQ_API_KEY")

print("GROQ KEY:", key[:8] + "..." if key else "NO KEY")