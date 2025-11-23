# Digital Employee: Automated Marketing CLI

This tool automates the "Trend-to-Tweet" pipeline for the agency ecosystem.

## 🚀 Quick Start Guide

### 1. Get Credentials
*   **Gemini API Key**: Get your free API key from [Google AI Studio](https://aistudio.google.com/).
*   **Google Sheets (Optional)**:
    1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
    2.  Enable **Google Sheets API** and **Google Drive API**.
    3.  Create a Service Account, download the JSON key, rename it to `service_account.json`, and put it in the project root.
    4.  **Important**: Share your target Google Sheet with the `client_email` found inside `service_account.json`.

### 2. Setup Environment
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and paste your GEMINI_API_KEY
nano .env
```

### 3. Run the App
**Option A: Using Docker (Recommended)**
```bash
docker-compose up -d  # Runs in background every 3 hours
```

**Option B: Running Locally**
```bash
# Install dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run once immediately
python main.py --mode once
```

## 🐳 Docker Support

You can run the application using Docker to ensure a consistent environment.

### Prerequisites
1. Docker and Docker Compose installed.
2. A `.env` file created from `.env.example`.
3. (Optional) A `service_account.json` file for Google Sheets integration.

### Running with Docker Compose

**Start the scheduler (runs every 3 hours):**
```bash
docker-compose up -d
```

**Run a single cycle immediately:**
```bash
docker-compose run --rm agency-bot python main.py --mode once
```

**View logs:**
```bash
docker-compose logs -f
```

## 📊 Google Sheets Integration
To enable saving generated content to Google Sheets:
1. Create a Project in Google Cloud Console.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Create a Service Account and download the JSON key.
4. Rename the key file to `service_account.json` and place it in the project root.
5. Share your target Google Sheet with the email address found in `service_account.json` (client_email).

## 📂 Project Structure
```text
/agency-bot
├── main.py            # The entry point (CLI interface)
├── core/
│   ├── trends.py      # Google Trends fetcher
│   ├── generator.py   # Gemini API prompt engineering
│   └── sheets_handler.py # Google Sheets saver
├── config/
│   └── personas.py    # Definitions of brand voices
├── drafts/
│   └── review_queue.json # Where posts wait for approval
├── .env               # API Keys (GitIgnored)
├── Dockerfile         # Docker image definition
├── docker-compose.yml # Docker orchestration
└── requirements.txt   # Python dependencies
```
