import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.environ.get('GEMINI_API_KEY')
model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')

class Claim(BaseModel):
    claimed_text: str = Field(description="Exact snippet")
    status: str 
    source: str
    url: Optional[str]
    detail: str
    apa_citation: str

class VerificationReport(BaseModel):
    annotated_segments: List[Claim]

client = genai.Client(api_key=api_key)

try:
    print("Testing Grounding + ResponseSchema Candidate Metadata...")
    response = client.models.generate_content(
        model=model_name,
        contents="The GDP of South Africa is 401 billion dollars in 2024 according to World Bank figures.",
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            response_mime_type="application/json",
            response_schema=VerificationReport,
            temperature=0.1,
            system_instruction="Analyze claim statements carefully against grounding sources."
        )
    )
    print("\n===== RESPONSE TEXT =====")
    print(response.text)
    
    metadata = response.candidates[0].grounding_metadata if response.candidates else None
    print("\n===== GROUNDING METADATA ATTACHED =====")
    if metadata:
         print(f"Chunks Count: {len(metadata.grounding_chunks) if metadata.grounding_chunks else 0}")
         if metadata.grounding_chunks:
              for i, chunk in enumerate(metadata.grounding_chunks):
                   print(f"Chunk[{i}]: Title='{chunk.web.title if chunk.web else 'N/A'}', URI='{chunk.web.uri if chunk.web else 'N/A'}'")
    else:
         print("No grounding_metadata found in candidates!")
    print("=========================")
except Exception as e:
    print(f"Error: {str(e)}")
