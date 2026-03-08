import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('GEMINI_API_KEY')

try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    
    print("Available models:")
    for model in genai.list_models():
        print(f"  - {model.name}")
except ImportError:
    print("google.generativeai not installed, trying google-genai...")
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=key)
        print("google-genai client configured successfully")
    except Exception as e:
        print(f"Error: {e}")
except Exception as e:
    print(f"Error: {e}")
