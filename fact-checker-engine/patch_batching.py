with open('app.py', 'r') as f:
    lines = f.readlines()

# 1. Add Imports at the top (around line 12)
imports_block = """import json
from concurrent.futures import ThreadPoolExecutor
"""
lines.insert(12, imports_block)

# 2. Add Helper function above @app.route('/verify')
# Locate @app.route('/verify') which was around line 77 (now shifted +2 lines to 79)
target_index = -1
for i, line in enumerate(lines):
    if "@app.route('/verify'" in line:
        target_index = i
        break

if target_index == -1:
    print("Error: Could not find @app.route('/verify') in app.py")
    exit(1)

helper_function = """def verify_text_chunk(chunk_text, mode):
    model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')
    if mode == 'grounding':
         response = client.models.generate_content(
              model=model_name,
              contents=f"Analyze and verify the claims following this text as a structured fact-checker.\\n\\nText:\\n{chunk_text}",
              config=types.GenerateContentConfig(
                  tools=[{"google_search": {}}],
                  response_mime_type="application/json",
                  response_schema=VerificationReport,
                  temperature=0.1,
                  system_instruction="Identify every claim about numbers, stats, dates, percentages. Return separate individual Claim entries for each unique fact. IMPORTANT: Populate 'claimed_text' with the EXACT word-for-word string substring found in the text so it can be located precisely for highlighting purposes. Avoid citing speeches or statements made by World Bank Presidents (like Ajay Banga); verify against external empirical datasets or independent high-credibility reporting."
              )
         )
         return response.text
    else:
         response = client.models.generate_content(
              model=model_name,
              contents=f"Review stats in this text. Use query_world_bank_stats tool if relevant.\\n\\nText:\\n{chunk_text}",
              config=types.GenerateContentConfig(
                  tools=[query_world_bank_stats],
                  response_mime_type="application/json",
                  response_schema=VerificationReport,
                  temperature=0.1
              )
         )
         return response.text

"""

lines.insert(target_index, helper_function)

# Re-locate @app.route('/verify') since inserting the helper shifted indices
target_index = -1
for i, line in enumerate(lines):
    if "@app.route('/verify'" in line:
        target_index = i
        break

# Now we need to replace the entire def verify(): function block.
# Starts at target_index + 1 ('def verify():')
# Ends at 'return response.text' which was previously at index 124 (shifted forward now).
# Let's find end trigger '@app.route('/upload')' to safely replace until that bound!
end_index = -1
for i, line in enumerate(lines):
    if "@app.route('/upload'" in line:
        end_index = i
        break

if end_index == -1:
    print("Error: Could not find @app.route('/upload') in app.py")
    exit(1)

new_verify_route = """@app.route('/verify', methods=['POST'])
def verify():
     req_data = request.get_json()
     text = req_data.get('text', '')
     mode = req_data.get('mode', 'grounding')
     
     if not text.strip():
          return jsonify({"error": "Empty text"}), 400
          
     try:
          # Split text into chunks to solve dense layouts timeouts
          paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
          chunks = []
          current_chunk = ""
          for p in paragraphs:
               if len(current_chunk) + len(p) < 2000: # 500 words limit optimal threshold
                    current_chunk += p + "\\n\\n"
               else:
                    chunks.append(current_chunk.strip())
                    current_chunk = p + "\\n\\n"
          if current_chunk:
               chunks.append(current_chunk.strip())
               
          if not chunks:
               # Handle if there were no double linebreaks separating chunks
               chunks = [text]

          print(f"[Backend] Splitting text into {len(chunks)} chunks for parallel mode: {mode}")
          
          all_segments = []
          # Default workers pool sizes for fast I/O bound grounded tasks
          with ThreadPoolExecutor(max_workers=5) as executor:
               futures = [executor.submit(verify_text_chunk, c, mode) for c in chunks]
               for future in futures:
                    res_text = future.result()
                    try:
                         res_json = json.loads(res_text)
                         segments = res_json.get('annotated_segments', [])
                         # Clean segments: Ensure claimed_text is present
                         valid_segments = [s for s in segments if s.get('claimed_text')]
                         all_segments.extend(valid_segments)
                    except Exception as parse_e:
                         print(f"[Parse Error] Failed to parse batch JSON response: {str(parse_e)}")
                         
          return jsonify({"annotated_segments": all_segments})
          
     except Exception as e:
          print(f"[Verify Error] {str(e)}")
          return jsonify({"error": str(e)}), 500

"""

# Replace lines from target_index up to end_index (exclusive)
lines_replaced = lines[:target_index] + [new_verify_route] + lines[end_index:]

with open('app.py', 'w') as f:
    f.writelines(lines_replaced)

print("Patching complete.")
f = open('app.py', 'r')
print(f"Total lines now: {len(f.readlines())}")
f.close()
