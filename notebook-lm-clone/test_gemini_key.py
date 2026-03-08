import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('GEMINI_API_KEY')
print(f'Key loaded: {bool(key)}')
print(f'Key length: {len(key) if key else 0}')
print(f'Key first 20 chars: {key[:20] if key else "NOT FOUND"}')
print(f'Key repr: {repr(key)}')

# Test with google-generativeai
try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('test')
    print('✓ Gemini API key is valid!')
except Exception as e:
    print(f'✗ Error: {e}')
