# Atlas AI Research Agent

Atlas is an autonomous AI agent designed for deep corporate research. It can scrape the web, extract structured data (contacts, tech stack, key people), and generate comprehensive reports in PDF and Excel formats.

## 🚀 New Features (v2.0)

### 1. Bulk Research Pipeline
- **Input**: Upload a CSV with a `domain` column.
- **Process**: The agent sequentially researches every company in the list.
- **Output**: Generates a **multi-tab Excel report** fully populated with:
  - Company Info & Registration (VAT, SIC)
  - Contact Details (Phone, Email, Address)
  - Social Media Links
  - Key People
  - Tech Stack & Services

### 2. "Small Model" Intelligence
Optimized for local LLMs (like Qwen 4B, Llama 3):
- **Smart Prompting**: Uses Chain-of-Thought ("Think step-by-step") to improve extraction accuracy.
- **Clean Data**: Automatically filters out "Not Found", "N/A", or "Unknown" to ensure clean spreadsheets.
- **Deterministic**: Temperature set to 0 to prevent hallucinations.

### 3. Automatic Logo Enrichment
- The agent now attempts to fetch high-quality transparent logos for every company using heuristic APIs, ensuring your reports look professional.

## 🛠️ Setup & Usage

### Prerequisites
- Python 3.10+
- Node.js & pnpm
- Brave Browser (for scraping)
- Ollama (running a local model like `qwen2.5:7b`)

### Running the App

1. **Start the Backend**
   ```bash
   cd atlas_backend
   python server.py
   ```

2. **Start the Frontend**
   ```bash
   cd atlas_frontend
   pnpm run dev
   ```

3. **Open Browser**
   - Go to `http://localhost:5173`
   - Toggle **BULK_UPLOAD** at the top right.
   - Upload your `Topic1_Input_Records(in).csv`.
   - Watch the agent work!

## 📂 Output Format
The generated Excel file strictly follows the `Topic1_Output_Format.xlsx` schema, ensuring compatibility with your existing workflows.
