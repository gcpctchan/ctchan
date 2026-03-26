import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.environ.get('GEMINI_API_KEY')
model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')

client = genai.Client(api_key=api_key)

class Claim(BaseModel):
    claimed_text: str = Field(description="The claim found in draft text")
    status: str = Field(description="verified, unverified, conflicting, or opinion")
    source: str = Field(description="Author/Organization Name creating the verification")
    pub_date: Optional[str] = Field(None, description="Publication date if found, or 'n.d.'")
    url: Optional[str] = Field(None, description="Direct URL of absolute source")
    detail: str = Field(description="Details verifying accuracy")
    apa_citation: str = Field(description="Formatted full APA Citation including author, date, and raw source link")

class VerificationReport(BaseModel):
    annotated_segments: List[Claim]

try:
    print("Testing Grounding + ResponseSchema...")
    response = client.models.generate_content(
        model=model_name,
        contents="Verify: The GDP of South Africa is 400 billion dollars in 2024.",
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            response_mime_type="application/json",
            response_schema=VerificationReport,
            temperature=0.1,
            system_instruction="Analyze claim statements carefully against grounding sources. For each item list full author and date string buffers accurate to original publication records inside the citation strings."
        )
    )
    print("\n===== RESPONSE TEXT =====")
    print(response.text)
    print("=========================")
except Exception as e:
    print(f"\nError Combining Grounding + Schema: {str(e)}")
