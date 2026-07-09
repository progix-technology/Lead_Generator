# LeadGen Pro: AI Cold Outreach & Lead Generator 🤖💼

LeadGen Pro is an advanced, fully automated lead generation and cold outreach application. It targets local businesses that **do not have a website**, extracts their contact emails safely from their verified social profiles (Facebook, Instagram, LinkedIn), validates them using SMTP checks, and drafts personalized email pitches using AI to schedule client calls.

---

## 🛠️ Technology Stack

- **Frontend:** React, Vite, TailwindCSS (for responsive utility layouts), Vanilla CSS, React-Icons.
- **Backend:** Python FastAPI, Uvicorn, Motor (Async MongoDB Driver).
- **Scraper / Scorer Engine:** Playwright, WHOIS lookup registry, SMTP socket verifier.
- **AI Personalization:** OpenRouter AI integration (Gemini 2.5 Flash / Llama 3).

---

## ✨ Key Features

1. **Company Search:** 
   - Uses a live scraper search to find local businesses.
   - Automatically filters out businesses with existing websites.
   - Targets only high-potential leads that need website design services.
2. **My Companies (Lead Manager):**
   - Save high-quality leads, track email scrape progress, and verify mailboxes.
   - Dispatch manual single/bulk outreach templates.
3. **Autopilot Outreach (Fully Automated):**
   - Runs every 30 minutes in the background rotating categories and locations.
   - Executes outreach cycles **only between 10:00 AM and 12:00 PM local time**.
   - Capped at **20 sent emails per day** to protect SMTP IP reputation.
   - Real-time hacking-style dark logs console terminal.
4. **Outreach Reports:**
   - Filter outreach logs day-wise using presets or a custom calendar date picker.
   - Active counter stats (Sent, Failed, Success Rate %).
   - Categories/locations breakdown performance bar graphs.
   - Email pitch modal to preview exact sent body templates.
   - Direct CSV downloader.
5. **Interactive Dashboard:**
   - Dynamic real-time counters, interactive filters, and outreach activity streams.
6. **Dynamic Credentials Settings:**
   - Configure SMTP server details (Host, Port, Email, App Password) and custom OpenRouter keys directly from the UI.
   - System automatically switches to custom credentials if present in the database.

---

## ⚙️ Configuration Setup

Create a `.env` file inside the `backend` directory:

```env
# MongoDB Connection
MONGO_URI="mongodb://localhost:27017"
DATABASE_NAME="leadgenerator"

# App Config
ENVIRONMENT="development"
DEBUG=True

# Google Places / Fallback Scraper API (Optional)
GOOGLE_PLACES_API_KEY="your-google-places-key"

# Default SMTP Configurations (Fallback if DB Settings are Empty)
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-default-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_FROM_EMAIL="your-default-email@gmail.com"

# Default AI OpenRouter Configuration (Fallback if DB Settings are Empty)
OPENROUTER_API_KEY="your-openrouter-api-key"
```

---

## 🚀 How to Run Locally

### 1. Prerequisite
Ensure **MongoDB** is running on your machine:
```bash
# Windows
net start MongoDB
```

### 2. Startup Backend
Navigate to the `backend` directory, install requirements, and run the server:
```bash
cd backend
pip install -r requirements.txt
python run.py
```
*The FastAPI backend will start at `http://127.0.0.1:8000`.*

### 3. Startup Frontend
Navigate to the root directory, install npm packages, and start Vite dev server:
```bash
# In project root
npm install
npm run dev
```
*The React frontend will start at `http://localhost:5173`.*

---

## 🔒 Credential Security (Git Ignore)

All credentials, `.env` configuration files, Python virtual environments, and build caches are securely ignored in `.gitignore` to prevent leakage on GitHub.

```gitignore
.env
*.env
backend/.env
venv/
.venv/
__pycache__/
```
