from flask import Flask, request, jsonify, send_file
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
import requests
from docx import Document
from pypdf import PdfReader
import io
import urllib.parse
from dotenv import load_dotenv
import os
import json
from concurrent.futures import ThreadPoolExecutor

# Load Environment variables from .env if present
load_dotenv(override=True)

app = Flask(__name__, static_folder='static', static_url_path='')


# Initialize the Gemini Client
# Assumes GEMINI_API_KEY is in environment
client = genai.Client()

# ---------------------------------------------------------------------------
# Pydantic Models for Structured Output (Function Calling mode)
# ---------------------------------------------------------------------------
class VerificationAnnotation(BaseModel):
    claimed_text: str = Field(description="The claimed text, number, or assertion from user draft.")
    status: str = Field(description="verified, unverified, conflicting, or opinion")
    source: Optional[str] = Field(None, description="Source name (e.g., 'World Bank', 'Google Search').")
    pub_date: Optional[str] = Field(None, description="Publication date of the source if available (e.g. '2024', 'May 2024', or 'n.d.').")
    url: Optional[str] = Field(None, description="Direct URL to the source if available.")
    detail: Optional[str] = Field(None, description="Details supporting the verification or explaining the conflict.")
    suggested_correction: Optional[str] = Field(None, description="Suggested correction if conflict found.")
    apa_citation: Optional[str] = Field(None, description="Formal APA Citation suitable for report (Author. Year. Title. URL).")

class VerificationReport(BaseModel):
    annotated_segments: List[VerificationAnnotation]

# ---------------------------------------------------------------------------
# Tool: World Bank Open Data API API Definition
# ---------------------------------------------------------------------------
def query_world_bank_stats(indicator: str, country_iso3: str = "WLD") -> str:
    """
    Queries the World Bank Open Data API for economic/statistical indicators.
    
    Args:
        indicator: The indicator code (e.g., 'SP.POP.TOTL' for population, 'NY.GDP.MKTP.CD' for GDP).
        country_iso3: 3-letter country code (e.g., 'WLD' for World, 'USA' for United States). Defaults to 'WLD'.
    Returns:
        A json string containing the requested data.
    """
    # World Bank API v2 URL format
    url = f"http://api.worldbank.org/v2/country/{country_iso3}/indicator/{indicator}?format=json"
    print(f"[Tool Log] Querying World Bank API: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # The World Bank API usually returns a list [metadata, data_items]
            if isinstance(data, list) and len(data) > 1 and data[1]:
                 # Return first data item for simplicity or summary
                 item = data[1][0]
                 return f"Indicator: {item['indicator']['value']}, Country: {item['country']['value']}, Year: {item['date']}, Value: {item['value']}"
            return "World Bank API returned no data for this query."
        return f"World Bank API error: HTTP {response.status_code}"
    except Exception as e:
        return f"Error contacting World Bank API: {str(e)}"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return app.send_static_file('index.html')

def verify_text_chunk(chunk_text, mode):
    model_name = os.environ.get('MODEL_NAME', 'gemini-3.1-pro-preview')
    try:
        if mode == 'grounding':
             response = client.models.generate_content(
                  model=model_name,
                  contents=f"Analyze and verify the claims following this text as a structured fact-checker.\n\nText:\n{chunk_text}",
                  config=types.GenerateContentConfig(
                      tools=[{"google_search": {}}],
                      response_mime_type="application/json",
                      response_schema=VerificationReport,
                      temperature=0.1,
                      system_instruction="Identify every claim about numbers, stats, dates, percentages. Return separate individual Claim entries for each unique fact. IMPORTANT: Populate 'claimed_text' with the EXACT word-for-word string substring found in the text so it can be located precisely for highlighting purposes. Avoid citing speeches or statements made by World Bank Presidents (like Ajay Banga); verify against external empirical datasets or independent high-credibility reporting."
                  )
             )
        elif mode == 'auditor':
             response = client.models.generate_content(
                  model=model_name,
                  contents=f"Find claims where an explicit URL is cited. Verify if that URL content supports it. Use Google Search to check if information at that site confirms the claim.\n\nText:\n{chunk_text}",
                  config=types.GenerateContentConfig(
                      tools=[{"google_search": {}}],
                      response_mime_type="application/json",
                      response_schema=VerificationReport,
                      temperature=0.1,
                      system_instruction="Extract every CITATION (APA, MLA, or raw URL). Populate 'url' with the cited URL if available. IMPORTANT: Populate 'claimed_text' with the EXACT verbatim string of that citation found in the text (leaving protocol http vs https exactly unchanged, e.g., the URL itself or the parenthetical author citation like (Banga, 2024)). Populate 'explanation' with evaluation of whether the cited source validates the text it supports."
                  )
             )
        else:
             # Default to Function Calling or past behavior
             response = client.models.generate_content(
                  model=model_name,
                  contents=f"Review stats in this text. Use query_world_bank_stats tool if relevant.\n\nText:\n{chunk_text}",
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
                            print(f"[Self-Validate] {res.status_code} for {url}")
                            claim['url'] = None
                            claim['url_status_error'] = f"HTTP {res.status_code}"
                            if claim.get('apa_citation'):
                                 claim['apa_citation'] = claim['apa_citation'].replace(url, "[Link Unverified]")
                  except Exception as e:
                       print(f"[Self-Validate Error] {url}: {str(e)}")
                       claim['url'] = None
                       claim['url_status_error'] = str(e)
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
          paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
          chunks = []
          current_chunk = ""
          for p in paragraphs:
               if len(current_chunk) + len(p) < 2000:
                    current_chunk += p + "\n\n"
               else:
                    chunks.append(current_chunk.strip())
                    current_chunk = p + "\n\n"
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

@app.route('/upload', methods=['POST'])
def upload_file():
    print(f"[Upload] Files received: {list(request.files.keys())}")
    if 'file' not in request.files:
        print("[Upload Error] No file part in request")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        print("[Upload Error] No selected file")
        return jsonify({"error": "No selected file"}), 400
        
    extracted_text = ""
    filename_lower = file.filename.lower()
    content_type = file.content_type
    print(f"[Upload] Processing file: {file.filename} (MIME: {content_type})")
    try:
        is_word = (content_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ]) or filename_lower.endswith('.docx')

        is_pdf = (content_type == 'application/pdf') or filename_lower.endswith('.pdf')

        if is_word:
             doc = Document(io.BytesIO(file.read()))
             extracted_text = '\n'.join([para.text for para in doc.paragraphs])
        elif is_pdf:
             reader = PdfReader(io.BytesIO(file.read()))
             for page in reader.pages:
                 text = page.extract_text()
                 if text:
                     extracted_text += text + "\n"
        else:
             print(f"[Upload Error] Unsupported format: {file.filename} (MIME: {content_type})")
             return jsonify({"error": f"Unsupported format: {file.filename} / {content_type}"}), 400
             
        return jsonify({
            "text": extracted_text, 
            "status": "success",
            "filename": file.filename
        })
    except Exception as e:
        print(f"[Upload Exception] {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/export_citations', methods=['POST'])
def export_citations():
     from fpdf import FPDF
     import json
     annotations_str = request.form.get('annotations', '[]')
     mode = request.form.get('mode', 'drafter')
     try:
          annotations = json.loads(annotations_str)
     except:
          annotations = []
     
     pdf = FPDF()
     pdf.add_page()
     
     def sanitize_for_pdf(text):
         if not text: return ""
         # Replace common smart quotes/dashes that break latin-1
         replacements = {
             '\u2019': "'", '\u2018': "'",
             '\u201c': '"', '\u201d': '"',
             '\u2014': '-', '\u2013': '-',
             '\u2022': '*'
         }
         # Cast to str to avoid AttributeError if it's type None or List
         t = str(text)
         for k, v in replacements.items():
             t = t.replace(k, v)
         return t.encode('latin-1', 'ignore').decode('latin-1')

     # Use default Helvetica since Arial maps to it with warning
     pdf.set_font("Helvetica", size=16, style='B')
     pdf.cell(0, 10, text="Formal Claim Citations Report", align='C')
     pdf.ln(15)
     
     pdf.set_font("Helvetica", size=12)
     count = 1
     for item in annotations:
         if mode == 'auditor' or item.get('apa_citation'):
              pdf.set_font("Helvetica", size=12, style='B')
              title_txt = "Citation" if mode == 'auditor' else "Claim"
              claim_txt = sanitize_for_pdf(item.get('claimed_text') or "Unknown Text")
              pdf.multi_cell(pdf.epw, 8, text=f"{count}. {title_txt}: \"{claim_txt}\"")
              pdf.ln(1)
              
              pdf.set_font("Helvetica", size=10)
              reason_txt = sanitize_for_pdf(item.get('explanation') or 'Analysis complete.')
              pdf.multi_cell(pdf.epw, 6, text=f"Reasoning/Verification: {reason_txt}")
              pdf.ln(1)
              
              if item.get('url'):
                   pdf.set_font("Helvetica", size=10, style='I')
                   pdf.multi_cell(pdf.epw, 6, text=f"Source: {item['url']}")
              elif mode == 'auditor':
                   pdf.set_font("Helvetica", size=10, style='I')
                   pdf.multi_cell(pdf.epw, 6, text="Source: [Link Unresolved or Broken]")
              elif item.get('apa_citation'):
                   pdf.set_font("Helvetica", size=10, style='I')
                   pdf.multi_cell(pdf.epw, 6, text=f"APA: {item['apa_citation']}")
              pdf.ln(3)
              count += 1
              
              pdf.set_x(pdf.l_margin)
              pdf.set_font("Helvetica", size=11)
              apa_txt = sanitize_for_pdf(item.get('apa_citation'))
              pdf.multi_cell(pdf.epw, 8, text=f"Citation (APA): {apa_txt}")
              pdf.ln(8)
              count += 1
              
     if count == 1:
          pdf.cell(0, 10, text="No formal citations found or provided.", align='C')

     # Save PDF to BytesIO stream
     pdf_bytes = pdf.output()
     if isinstance(pdf_bytes, bytearray):
          pdf_bytes = bytes(pdf_bytes)

     return send_file(
          io.BytesIO(pdf_bytes),
          mimetype="application/pdf",
          as_attachment=True,
          download_name="citations_report.pdf"
     )

if __name__ == '__main__':
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=True)
