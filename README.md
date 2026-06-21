# Personal Productivity Agent

A daily-log app with an LLM agent that classifies your tasks, surfaces overdue items, drafts your EOD summary, and plans tomorrow's work.

## Stack

- **Backend** — FastAPI + LangGraph stateful agent + SQLite (SQLAlchemy)
- **LLM** — Groq (llama-3.1-8b for classification, llama-3.3-70b for summaries)
- **Frontend** — Streamlit
- **Scheduler** — APScheduler (weekly review every Sunday)

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
