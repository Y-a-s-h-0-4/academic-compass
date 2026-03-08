import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('GEMINI_API_KEY')

try:
    from google import genai
    client = genai.Client(api_key=key)
    
    print("Attempting to list models...")
    models = client.models.list()
    
    print("\nAvailable models:")
    for model in models:
        print(f"  - {model.name}")
        if hasattr(model, 'display_name'):
            print(f"    Display: {model.display_name}")
    
except Exception as e:
    print(f"Error listing models: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Try to make a test request
    try:
        response = client.models.generate_content(
            model="models/gemini-1.5-pro",
            contents="test"
        )
        print("Request successful!")
    except Exception as e2:
        print(f"Test request error: {e2}")
