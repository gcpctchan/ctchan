import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.environ.get('GEMINI_API_KEY')
model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model=model_name,
        contents="Verify this claim: The GDP of South Africa is 400 billion dollars in 2024. Provide full sources and APA formatted references for the fact check.",
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.1,
            system_instruction="Provide a full detailed analysis and append an explicit **Sources** footer containing clean URLs. Inspect search results accurately."
        )
    )

    print("===== RESPONSE TEXT =====")
    print(response.text)
    print("=========================")

except Exception as e:
    print(f"Error: {str(e)}")
