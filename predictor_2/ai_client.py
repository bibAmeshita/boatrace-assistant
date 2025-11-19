# predictor_2/ai_client.py
import os
from google import genai

GOOGLE_API_KEY = "AIzaSyBjt4lnhgXKTvJ7aY0kvMTFeOGS_DHvhMc"

# Google GenAI クライアント初期化
client = genai.Client(api_key=GOOGLE_API_KEY)

def call_ai(prompt: str):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",   # ← 最新の無料モデルでOK
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"[AI Error] {str(e)}"
