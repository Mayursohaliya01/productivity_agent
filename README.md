# Personal Productivity Agent

An AI-powered daily task management system that helps you structure your day, track progress, and reflect on productivity patterns. The agent classifies tasks by category/urgency, surfaces overdue items, drafts end-of-day summaries, and generates weekly reviews.

**Live Demo:** [Deploy to Streamlit Cloud](#deploying-to-streamlit-cloud) _(placeholder — add your link after deployment)_

## Stack

- **Backend** — FastAPI + LangGraph stateful agent + SQLite (SQLAlchemy)
- **LLM** — Groq (free tier, llama-3.1-8b for classification, llama-3.3-70b for summaries)
- **Frontend** — Streamlit
- **Scheduler** — APScheduler (weekly reviews every Sunday)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 3. Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

The API docs are at `http://localhost:8000/docs`.

### 4. Run the frontend (new terminal)

```bash
streamlit run frontend/app.py
```

Opens at `http://localhost:8501`.

## How to use

1. **Register / Login** — create your account
2. **Morning Check-in** — paste your tasks for the day (one per line). The agent classifies them by category and urgency, and flags anything overdue from previous days.
3. **My Tasks** — view today's task list, mark things done or skip them as you go.
4. **Evening Check-in** — confirm what you finished. The agent drafts a 3-4 sentence EOD summary and suggests what to tackle tomorrow.
5. **EOD History** — browse past daily summaries.
6. **This Week** — completion stats and daily summaries side-by-side.
7. **Weekly Review** — pattern analysis (runs automatically every Sunday, or trigger manually).

## Project structure

```
productivity_agent/
├── backend/
│   ├── main.py        # FastAPI routes
│   ├── agent.py       # LangGraph pipeline (classify → overdue / eod → plan)
│   ├── models.py      # SQLAlchemy models
│   ├── schemas.py     # Pydantic request/response models
│   ├── auth.py        # JWT auth
│   ├── database.py    # DB engine + session
│   ├── scheduler.py   # APScheduler weekly job
│   └── config.py      # Settings from .env
├── frontend/
│   └── app.py         # Streamlit UI
├── requirements.txt
└── .env.example
```

## DB schema (quick view)

| Table | Key columns |
|---|---|
| `users` | id, email, username, hashed_password |
| `tasks` | id, user_id, title, category, urgency, due_date, completed_at, skipped |
| `daily_logs` | id, user_id, log_date, morning_note, evening_note |
| `eod_summaries` | id, user_id, summary_date, summary_text, tomorrow_plan |
| `weekly_reviews` | id, user_id, week_start, review_text |

---

## Deploying to Streamlit Cloud

### Prerequisites

1. **GitHub Repo** — Push this code to https://github.com/Mayursohaliya01/productivity_agent.git
2. **Groq API Key** — Get free at [console.groq.com](https://console.groq.com)
3. **Streamlit Account** — Sign up at [share.streamlit.io](https://share.streamlit.io)

### Steps

1. Go to [share.streamlit.io](https://share.streamlit.io) and click **"New App"**
2. Select your GitHub repo, branch (`main`), and main file (`frontend/app.py`)
3. Click **Advanced Settings**
4. Under **Secrets**, paste your secrets in TOML format:
   ```toml
   GROQ_API_KEY = "gsk_your_actual_key"
   SECRET_KEY = "your_secure_random_string"
   DATABASE_URL = "sqlite:///./productivity.db"
   CHECKPOINT_DB = "agent_state.db"
   TOKEN_EXPIRE_MINUTES = 1440
   DEMO_MODE = "false"
   DEMO_SEED = "false"
   ```
   See `.streamlit/secrets.toml.example` for all available options.

5. Click **Deploy** and wait ~2 minutes for the app to launch

### Important Notes

- **Database**: Uses SQLite with Streamlit's file persistence. Each deployment gets its own isolated database.
- **Backend**: This deployment is **frontend-only**. The backend runs on your local machine or a separate server.
  - For production, deploy the backend to a service like Render, Railway, or Heroku
  - Update `API_BASE` in `frontend/api_client.py` to point to your backend URL
  - Or run both locally during development and use `http://localhost:8000` for testing
- **Secrets**: Never commit `.streamlit/secrets.toml` to GitHub. Always use Streamlit's secrets manager.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'streamlit'"
Run `pip install -r requirements.txt` before launching.

### API connection errors
Check that the backend is running (default: `http://localhost:8000`).  
Update `API_BASE` in `frontend/api_client.py` if running on a different host/port.

### Groq API errors
Verify your `GROQ_API_KEY` is set in `.env` (local) or Streamlit Secrets (cloud).  
The app has fallback rule-based classification if the API key is missing.

---

## License

MIT
