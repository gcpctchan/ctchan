# 🔍 Fact-Checker Engine: Dual-Mode Claims Verification Workspace

Welcome to the **Fact-Checker Engine**, a state-of-the-art automated verification platform powered by the **Gemini API**. Whether you are drafting a new speech or auditing existing publications, this engine validates assertions and parses reference standards instantly.

---

## ✨ Application Features Workspace

| Feature | ✍️ Workbench (Drafter) | 🕵️ Citation Auditor |
| :--- | :--- | :--- |
| **Primary Goal** | Creating new text from scratch | Auditing pre-written papers/articles |
| **Logic Mode** | **Discover & Propose**: Searches the web to find supporting citations for your claims. | **Audit & Validate**: Verifies if your listed URLs are live and truthful. |
| **Visualization** | Highlights unverified vs verified assertions. | Maps direct URL integrity badges (Link Verified / Broken). |
| **Asset Exports** | Generates Claims verification outlines. | Compiles professional compliance Audit PDF reports. |

---

## 🚀 Local Installation Quickstart

### 1. Prerequisites
- **Python 3.9+** installed locally.
- A **Gemini API Key** (obtainable from [Google AI Studio](https://aistudio.google.com/)).

### 2. Setup standard environment
```bash
# Clone repository
git clone <your-repository-url>
cd fact-checker-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 🔑 3. Configure API Credentials
Copy the variables from template and populate them with your real keys:
```bash
cp .env.template .env
```
Open `.env` and configure:
```text
GEMINI_API_KEY=AIzaSy... (Your Key)
MODEL_NAME=gemini-2.5-pro
```

### ⚡ 4. Start Server
```bash
python3 app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser!

---

## ☁️ GCP Cloud Run Production Deployment

Deploy seamlessly onto Google Cloud Run using our containerization profile.

### Build and Package Docker
1. Ensure your `.env` is omitted from Git (checked by default in `.gitignore`).
2. Build Image via Cloud Build:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/fact-checker-engine
   ```
3. Deploy to Cloud Run attaching secrets:
   ```bash
   gcloud run deploy fact-checker-engine \
     --image gcr.io/YOUR_PROJECT_ID/fact-checker-engine \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars MODEL_NAME=gemini-2.1-pro
   ```

> [!IMPORTANT]
> **API Key Safety**: Never bake `GEMINI_API_KEY` into your `Dockerfile`. Always deploy it using `--set-env-vars` toggle during Cloud Runs deployments or use **Google Secret Manager**!

---

💡 *Crafted with ❤️ using Google Deepmind Advanced Agentic Coding profiles.*
