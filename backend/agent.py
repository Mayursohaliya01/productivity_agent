import json
import re
import sqlite3
from typing import TypedDict, List
from datetime import date, timedelta

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .config import settings

# use the fast small model for classification, bigger one for writing
FAST_MODEL = "llama-3.1-8b-instant"
SMART_MODEL = "llama-3.3-70b-versatile"

# Groq client — only created if an API key is set
_groq_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
        from groq import Groq
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


class AgentState(TypedDict):
    user_id: int
    mode: str          # "morning" or "evening"
    today_date: str
    raw_tasks: List[str]
    morning_note: str
    classified_tasks: List[dict]
    overdue_tasks: List[dict]
    completed_ids: List[int]
    skipped_ids: List[int]
    evening_note: str
    eod_summary: str
    tomorrow_plan: List[str]


def _call_groq(model: str, prompt: str, max_tokens: int = 600) -> str:
    client = _get_groq()
    if client is None:
        raise RuntimeError("No Groq API key configured")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ─── FALLBACK LOGIC (no API key needed) ──────────────────────────────────────

_WORK_WORDS = {"report", "meeting", "email", "project", "deadline", "review", "presentation",
               "code", "client", "call", "task", "work", "office", "proposal", "invoice", "slide"}
_HEALTH_WORDS = {"gym", "exercise", "workout", "walk", "run", "yoga", "doctor", "medicine",
                 "sleep", "diet", "health", "swim", "jog", "pushup", "stretching"}
_LEARN_WORDS = {"read", "study", "learn", "course", "book", "tutorial", "research",
                "practice", "chapter", "lecture", "assignment", "homework", "video"}


def _rule_classify(title: str) -> dict:
    words = set(re.findall(r"\w+", title.lower()))
    if words & _HEALTH_WORDS:
        cat = "health"
    elif words & _LEARN_WORDS:
        cat = "learning"
    elif words & _WORK_WORDS:
        cat = "work"
    else:
        cat = "personal"
    urgency = "high" if any(w in title.lower() for w in ("urgent", "asap", "today", "deadline", "must")) else "medium"
    return {"title": title, "category": cat, "urgency": urgency}


def _rule_eod(done: list, slipped: list, note: str) -> str:
    done_str = ", ".join(done) if done else "nothing"
    slip_str = ", ".join(slipped) if slipped else "none"
    lines = [f"Completed today: {done_str}."]
    if slipped:
        lines.append(f"Didn't finish: {slip_str}.")
    if note:
        lines.append(f"Note: {note}.")
    return " ".join(lines)


def _rule_plan(pending: list) -> list:
    return [t["title"] for t in pending[:5]] or ["Plan your day!"]


def _parse_json_response(raw: str) -> list:
    # LLMs sometimes wrap JSON in markdown code blocks
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def classify_node(state: AgentState) -> AgentState:
    if not state.get("raw_tasks"):
        return {**state, "classified_tasks": []}

    task_lines = "\n".join(f"- {t}" for t in state["raw_tasks"])
    prompt = f"""You're a productivity assistant helping classify daily tasks.

Classify each task below. Return ONLY a JSON array, no explanation.

For each task return: {{"title": "...", "category": "work|personal|health|learning|other", "urgency": "high|medium|low"}}

Tasks:
{task_lines}

JSON array:"""

    try:
        raw = _call_groq(FAST_MODEL, prompt, max_tokens=600)
        classified = _parse_json_response(raw)
    except Exception:
        # no API key or LLM error — use keyword-based classification
        classified = [_rule_classify(t) for t in state["raw_tasks"]]

    return {**state, "classified_tasks": classified}


def overdue_check_node(state: AgentState) -> AgentState:
    from .database import SessionLocal
    from . import models

    db = SessionLocal()
    try:
        today = state["today_date"]
        tasks = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == state["user_id"],
                models.Task.completed_at == None,
                models.Task.skipped == False,
                models.Task.due_date != None,
                models.Task.due_date < today,
            )
            .all()
        )
        overdue = [
            {
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "urgency": t.urgency,
                "due_date": t.due_date,
            }
            for t in tasks
        ]
    except Exception:
        overdue = []
    finally:
        db.close()

    return {**state, "overdue_tasks": overdue}


def eod_summary_node(state: AgentState) -> AgentState:
    from .database import SessionLocal
    from . import models

    db = SessionLocal()
    try:
        today = state["today_date"]
        tasks = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == state["user_id"],
                models.Task.due_date == today,
            )
            .all()
        )

        done = [t.title for t in tasks if t.completed_at is not None]
        slipped = [t.title for t in tasks if t.completed_at is None and not t.skipped]
        skipped = [t.title for t in tasks if t.skipped]
        note = state.get("evening_note", "") or ""

        completed_str = ", ".join(done) if done else "nothing completed"
        slipped_str = ", ".join(slipped) if slipped else "none"
        skipped_str = ", ".join(skipped) if skipped else "none"

        prompt = f"""Write a brief, honest end-of-day summary (3-4 sentences) for a personal productivity log.

Date: {today}
Completed: {completed_str}
Slipped (not done): {slipped_str}
Skipped: {skipped_str}
User's note: {note if note else 'none'}

Be direct, not preachy. Just capture what happened today."""

        summary = _call_groq(SMART_MODEL, prompt, max_tokens=250)
    except RuntimeError:
        summary = _rule_eod([t.title for t in tasks if t.completed_at], [t.title for t in tasks if not t.completed_at and not t.skipped], note)
    except Exception as e:
        summary = _rule_eod([t.title for t in tasks if t.completed_at], [t.title for t in tasks if not t.completed_at and not t.skipped], note)
    finally:
        db.close()

    return {**state, "eod_summary": summary}


def tomorrow_planner_node(state: AgentState) -> AgentState:
    from .database import SessionLocal
    from . import models

    db = SessionLocal()
    try:
        today = state["today_date"]

        # tasks from today that slipped
        slipped_today = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == state["user_id"],
                models.Task.due_date == today,
                models.Task.completed_at == None,
                models.Task.skipped == False,
            )
            .all()
        )

        # anything else still overdue
        older_overdue = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == state["user_id"],
                models.Task.completed_at == None,
                models.Task.skipped == False,
                models.Task.due_date != None,
                models.Task.due_date < today,
            )
            .all()
        )

        pending = slipped_today + older_overdue
        pending_str = (
            "\n".join(f"- {t.title} (urgency: {t.urgency})" for t in pending)
            if pending else "none"
        )
        eod = state.get("eod_summary", "")

        prompt = f"""Based on what slipped today and existing overdue tasks, suggest a realistic plan for tomorrow. Max 5 items.

Today's summary: {eod}

Pending / overdue tasks:
{pending_str}

Return ONLY a JSON array of task title strings. Example:
["Finish the report", "30min workout", "Call client back"]

JSON array:"""

        raw = _call_groq(SMART_MODEL, prompt, max_tokens=300)
        plan = _parse_json_response(raw)
        if not isinstance(plan, list):
            raise ValueError("not a list")
    except Exception:
        plan = _rule_plan([{"title": t.title} for t in pending])
    finally:
        db.close()

    return {**state, "tomorrow_plan": plan}


def route_by_mode(state: AgentState) -> str:
    return state.get("mode", "morning")


def _build_graph():
    conn = sqlite3.connect(settings.CHECKPOINT_DB, check_same_thread=False)
    memory = SqliteSaver(conn)

    builder = StateGraph(AgentState)

    builder.add_node("router", lambda s: s)
    builder.add_node("classify", classify_node)
    builder.add_node("overdue_check", overdue_check_node)
    builder.add_node("eod_draft", eod_summary_node)
    builder.add_node("planner", tomorrow_planner_node)

    builder.set_entry_point("router")
    builder.add_conditional_edges(
        "router",
        route_by_mode,
        {"morning": "classify", "evening": "eod_draft"},
    )

    builder.add_edge("classify", "overdue_check")
    builder.add_edge("overdue_check", END)

    builder.add_edge("eod_draft", "planner")
    builder.add_edge("planner", END)

    return builder.compile(checkpointer=memory)


# initialised once when the backend starts up
agent_graph = _build_graph()


def run_morning(user_id: int, tasks: list, morning_note: str = "") -> dict:
    today = str(date.today())
    config = {"configurable": {"thread_id": f"user_{user_id}"}}

    state = {
        "user_id": user_id,
        "mode": "morning",
        "today_date": today,
        "raw_tasks": tasks,
        "morning_note": morning_note,
        "classified_tasks": [],
        "overdue_tasks": [],
        "completed_ids": [],
        "skipped_ids": [],
        "evening_note": "",
        "eod_summary": "",
        "tomorrow_plan": [],
    }

    result = agent_graph.invoke(state, config=config)
    return {
        "classified_tasks": result.get("classified_tasks", []),
        "overdue_tasks": result.get("overdue_tasks", []),
    }


def run_evening(user_id: int, completed_ids: list, skipped_ids: list, evening_note: str = "") -> dict:
    today = str(date.today())
    config = {"configurable": {"thread_id": f"user_{user_id}_eve_{today}"}}

    state = {
        "user_id": user_id,
        "mode": "evening",
        "today_date": today,
        "raw_tasks": [],
        "morning_note": "",
        "classified_tasks": [],
        "overdue_tasks": [],
        "completed_ids": completed_ids,
        "skipped_ids": skipped_ids,
        "evening_note": evening_note,
        "eod_summary": "",
        "tomorrow_plan": [],
    }

    result = agent_graph.invoke(state, config=config)
    return {
        "eod_summary": result.get("eod_summary", ""),
        "tomorrow_plan": result.get("tomorrow_plan", []),
    }


def run_weekly_review(user_id: int) -> str:
    """Generates a weekly pattern summary. Called by the scheduler every Sunday."""
    from .database import SessionLocal
    from . import models

    db = SessionLocal()
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)
        week_ago_str = str(week_ago)

        tasks = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == user_id,
                models.Task.due_date >= week_ago_str,
                models.Task.due_date <= str(today),
            )
            .all()
        )

        if not tasks:
            return "No tasks logged this week — start adding daily tasks to get weekly insights!"

        done = [t for t in tasks if t.completed_at is not None]
        slipped = [t for t in tasks if t.completed_at is None and not t.skipped]

        # count how many times each task title repeated without completion
        from collections import Counter
        slip_counts = Counter(t.title for t in slipped)
        repeat_slips = [f"'{k}' (pushed {v} times)" for k, v in slip_counts.most_common(3) if v > 1]

        by_category = Counter(t.category for t in tasks)
        cat_str = ", ".join(f"{k}: {v}" for k, v in by_category.items())
        completion_rate = round(len(done) / len(tasks) * 100) if tasks else 0

        prompt = f"""Write a weekly productivity review (4-6 sentences) based on this week's data.

Week: {week_ago_str} to {str(today)}
Total tasks: {len(tasks)}
Completed: {len(done)} ({completion_rate}%)
Slipped/incomplete: {len(slipped)}
Repeatedly pushed tasks: {', '.join(repeat_slips) if repeat_slips else 'none'}
Categories this week: {cat_str}

Be honest, direct, and point out any clear patterns. Keep it encouraging but real."""

        review = _call_groq(SMART_MODEL, prompt, max_tokens=350)
    except Exception:
        review = (
            f"Week of {week_ago_str} to {str(today)}: "
            f"{len(tasks)} tasks logged, {len(done)} completed ({completion_rate}% rate). "
            f"Add a Groq API key to get AI-powered pattern analysis."
        )
    finally:
        db.close()

    return review
