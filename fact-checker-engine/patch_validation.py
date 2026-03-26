with open('app.py', 'r') as f:
    lines = f.readlines()

# Locate verify_text_chunk
helper_index = -1
for i, line in enumerate(lines):
    if "def verify_text_chunk" in line:
        helper_index = i
        break

if helper_index == -1:
    print("Error: def verify_text_chunk not found")
    exit(1)

# Locate /verify route
verify_index = -1
for i, line in enumerate(lines):
    if "@app.route('/verify'" in line:
        verify_index = i
        break

# We need to replace EVERYTHING from verify_text_chunk up to /upload route!
# To do this safely and cleanly, we re-write from helper_index up to @app.route('/upload')
upload_index = -1
for i, line in enumerate(lines):
    if "@app.route('/upload'" in line:
        upload_index = i
        break

if upload_index == -1:
    print("Error: def upload_file and @app.route('/upload') not found")
    exit(1)

new_helper_and_verify = """def verify_text_chunk(chunk_text, mode):
    model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')
    try:
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
        
        res_json = json.loads(response.text)
        segments = res_json.get('annotated_segments', [])
        
        # --- URL Self-Validation ---
        for claim in segments:
             url = claim.get('url')
             if url:
                  try:
                       # 3-second quick verification
                       res = requests.head(url, timeout=3)
                       if res.status_code >= 400:
                            print(f"[Self-Validate] 404 for {url}")
                            claim['url'] = None
                            if claim.get('apa_citation'):
                                 claim['apa_citation'] = claim['apa_citation'].replace(url, "[Link Unverified]")
                  except Exception as e:
                       print(f"[Self-Validate Error] {url}: {str(e)}")
                       claim['url'] = None
                       if claim.get('apa_citation'):
                            claim['apa_citation'] = claim['apa_citation'].replace(url, "[Link Unverified]")
                            
        return res_json
        
    except Exception as e:
        print(f"[Chunk Error] {str(e)}")
        return {"annotated_segments": []}

@app.route('/verify', methods=['POST'])
def verify():
     req_data = request.get_json()
     text = req_data.get('text', '')
     mode = req_data.get('mode', 'grounding')
     
     if not text.strip():
          return jsonify({"error": "Empty text"}), 400
          
     try:
          paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
          chunks = []
          current_chunk = ""
          for p in paragraphs:
               if len(current_chunk) + len(p) < 2000:
                    current_chunk += p + "\\n\\n"
               else:
                    chunks.append(current_chunk.strip())
                    current_chunk = p + "\\n\\n"
          if current_chunk:
               chunks.append(current_chunk.strip())
          if not chunks:
               chunks = [text]

          print(f"[Backend] Splitting text into {len(chunks)} chunks for mode: {mode}")
          all_segments = []
          
          with ThreadPoolExecutor(max_workers=5) as executor:
               futures = [executor.submit(verify_text_chunk, c, mode) for c in chunks]
               for future in futures:
                    res_json = future.result()
                    # Res json is dict now
                    segments = res_json.get('annotated_segments', [])
                    valid_segments = [s for s in segments if s.get('claimed_text')]
                    all_segments.extend(valid_segments)
                    
          return jsonify({"annotated_segments": all_segments})
          
     except Exception as e:
          print(f"[Verify Error] {str(e)}")
          return jsonify({"error": str(e)}), 500

"""

# Replace lines from helper_index up to upload_index
lines_replaced = lines[:helper_index] + [new_helper_and_verify] + lines[upload_index:]

with open('app.py', 'w') as f:
    f.writelines(lines_replaced)

print("Self-validation patch complete.")
f = open('app.py', 'r')
print(f"Total lines now: {len(f.readlines())}")
f.close()
