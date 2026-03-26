with open('app.py', 'r') as f:
    lines = f.readlines()

new_block = """             response = client.models.generate_content(
                  model=model_name,
                  contents=f"Analyze and verify the claims following this text as a structured fact-checker. For each annotation found, list the authentic author, date, and full original URL inside the structured response fields.\\n\\nText:\\n{text}",
                  config=types.GenerateContentConfig(
                      tools=[{"google_search": {}}],
                      response_mime_type="application/json",
                      response_schema=VerificationReport,
                      temperature=0.1,
                      system_instruction="When validating claims, avoid citing speeches or public statements made by former or current World Bank Presidents (like Ajay Banga). We are checking if these claims are supported by external empirical datasets, research reports, or independent high-credibility reporting. Formulate a full structured representation leveraging original absolute source URLs (avoiding redirect trackers), author details, and publication dates in the citations strings natively."
                  )
             )
             
             # Return structured JSON matching VerificationReport directly
             return response.text
"""

# indices in f.readlines() are 0-indexed:
# original line 91 is index 90
# original line 134 is index 133
# We want to replace indices 90 to 133 inclusive.
# So we want to replace lines[90:134] (which is lines[90], lines[91], ..., lines[133])
# lines[:90] is up to index 89 inclusive (line 1 to 90)
# lines[134:] is index 134 forware (line 135 and forward)
lines_replaced = lines[:90] + [new_block] + lines[134:]

with open('app.py', 'w') as f:
    f.writelines(lines_replaced)
print("Replace complete.")
