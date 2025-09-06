<h1 align="center">TRAVELMATE</h1>
<h2 align="center">AI-Powered Travel Planning Assistant</h2>
<p align="center">An intelligent multi-agent travel assistant that helps you plan trips with personalized recommendations, itineraries, budgets, and more.</p>

---

## 🧳 About the Project

This repository contains the **backend and AI components** for an AI-powered travel planner.  
The application leverages **CrewAI multi-agent orchestration** with LLMs, real-time weather and image APIs, and a wizard-style frontend.  

Users can interact via:  
- A **Streamlit Wizard UI** to explore destinations step by step.  
- A **FastAPI backend** providing REST APIs for integration with web or mobile apps.  

The system generates complete trip packages — including **destinations, itineraries, safety guidance, budget allocation, transport, accommodation, and reviews**.

---

## ✨ Key Features

- **Destination Suggestions**: Personalized recommendations with photos, weather, cost, and safety data.  
- **Local Insights**: AI-curated attractions, cuisines, and cultural experiences.  
- **Day-wise Itinerary**: Automatically built schedules balancing activities, food, and breaks.  
- **Safety Guidance**: Alerts for scams, local laws, health notes, and emergency contacts.  
- **Packing List Generator**: Season-aware recommendations tailored to trip style.  
- **Budget Breakdown**: Auto-splits or validates budgets into categories with per-day estimates.  
- **Transport Options**: Intercity and in-city travel suggestions with costs and pro tips.  
- **Accommodation Suggestions**: Stay options by vibe, neighborhood, and price tier.  
- **Review Summaries**: Aggregated pros/cons and ratings for attractions & restaurants.  

---

## 💻 Technical Stack

| Category           | Technology                               |
|--------------------|-------------------------------------------|
| Backend (UI)       | Streamlit                                 |
| Backend (API)      | FastAPI, Uvicorn                          |
| Multi-Agent System | CrewAI                                    |
| LLM                | Google Gemini API                         |
| Data Models        | Pydantic                                  |
| APIs               | OpenWeather, Unsplash                     |
| Utilities          | Requests, dotenv                          |

---

## 📂 Repository Structure

```plaintext
.
├── 🤖 agents.py        — Core AI logic: CrewAI agents, tools, tasks, orchestration
├── 🖥️ main.py          — Streamlit frontend (wizard-style trip planner)
├── 🔌 main-two.py      — FastAPI backend (REST endpoints)
├── 📦 requirements.txt — Python dependencies
└── 📝 README.md        — Project documentation
```

## 🚀 Getting Started

✅ Prerequisites
Python 3.9+

API keys for Gemini, OpenWeather, Unsplash

(Optional) React frontend to consume FastAPI endpoints

🔧 Installation
bash
Copy code
### Clone the repository
git clone <repository_url>
cd <repository_name>

### Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

### Install dependencies
pip install -r requirements.txt

⚙️ Configuration

Create a .env file in the project root:

ini

Copy code

GEMINI_API_KEY=your_google_gemini_api_key

OPENWEATHER_API_KEY=your_openweather_api_key

UNSPLASH_ACCESS_KEY=your_unsplash_access_key

UNSPLASH_SECRET_KEY=your_unsplash_secret_key

## ▶️ Running the Application

### 🖥️ Option 1 — Streamlit Wizard UI
bash
Copy code
streamlit run main.py
👉 Opens an interactive travel planning wizard in your browser.

### 🔌 Option 2 — FastAPI Backend
bash
Copy code
uvicorn main-two:app --reload
👉 Runs API server at http://127.0.0.1:8000 with Swagger docs at /docs.

### 📡 Example API Endpoints
POST /generate → Destination suggestions

POST /local-info → Attractions & cuisines

POST /schedule-trip → Day-by-day itinerary

POST /safety-info → Safety tips & emergency contacts

POST /packing-list → Season-aware packing guide

POST /budget-breakdown → Budget normalization

POST /transport-options → Intercity & in-city transport

POST /accommodation-suggestions → Stay options

POST /reviews → Summarized reviews

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License
This project is licensed under the MIT License.
