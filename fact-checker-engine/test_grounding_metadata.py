import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.environ.get('GEMINI_API_KEY')
model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')

print(f"Using Model: {model_name}")
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model=model_name,
        contents="Verify this claim: The GDP of South Africa is 400 billion dollars in 2024.",
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.1,
        )
    )

    metadata = response.candidates[0].grounding_metadata if response.candidates else None
    if metadata:
        print("Chunks:")
        if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
            for i, chunk in enumerate(metadata.grounding_chunks):
                print(f"\nChunk {i}:")
                if chunk.web:
                    print(f"  Title: {chunk.web.title}")
                    print(f"  URI: {chunk.web.uri}")
        else:
            print("No grounding_chunks in metadata attributes")

        print("\nSupports:")
        if hasattr(metadata, 'grounding_supports') and metadata.grounding_supports:
            for support in metadata.grounding_supports:
                 print(f"Segment: {support.segment.text}")
                 print(f"Indices: {getattr(support, 'grounding_chunk_indices', [])}")
    else:
        print("No metadata returned.")
except Exception as e:
    print(f"Error executing GenAI Grounding: {str(e)}")
