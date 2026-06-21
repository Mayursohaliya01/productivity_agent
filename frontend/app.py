import json
import requests
import streamlit as st
from datetime import date

from api_client import API_BASE, api_delete, api_get, api_post
from constants import URGENCY_LABELS
from demo_config import DEMO_MODE, DEMO_USERNAME, DEMO_PASSWORD
from views.calendar import show_calendar
from views.chat import show_chat
from views.dashboard import show_dashboard
from views.export import render_export_buttons, show_export
from views.focus import show_focus
from views.login_styles import inject_login_styles
from views.suggestions import render_morning_suggestions


def is_logged_in() -> bool:
    """True only if a token exists and has been verified with the backend."""
    return bool(st.session_state.get("token")) and bool(
        st.session_state.get("_auth_validated")
    )


def ensure_authenticated() -> bool:
    """
    Verify the stored JWT with the backend on each session.
    Clears stale/invalid tokens so refresh cannot bypass login.
    """
    token = st.session_state.get("token")
    if not token:
        st.session_state.pop("_auth_validated", None)
        st.session_state.pop("_validated_token", None)
        return False

    if (
        st.session_state.get("_auth_validated")
        and st.session_state.get("_validated_token") == token
    ):
        return True

    try:
        resp = requests.get(
            f"{API_BASE}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["user_id"] = data["user_id"]
            st.session_state["username"] = data["username"]
            st.session_state["_auth_validated"] = True
            st.session_state["_validated_token"] = token
            return True
    except requests.RequestException:
        pass

    _clear_auth_state()
    return False


LOGOUT_FLAG = "user_manually_logged_out"


def _clear_auth_state():
    """Remove all auth-related session keys (keep manual logout flag)."""
    logout_flag = st.session_state.get(LOGOUT_FLAG)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if logout_flag:
        st.session_state[LOGOUT_FLAG] = logout_flag


def logout():
    """Clear session and block demo auto-login until user signs in again."""
    st.session_state[LOGOUT_FLAG] = True
    _clear_auth_state()
    st.session_state[LOGOUT_FLAG] = True
    st.rerun()


def _clear_logout_flag():
    st.session_state.pop(LOGOUT_FLAG, None)


# ═══ DEMO ONLY — remove before production ═══════════════════════════════════
# Demo banner on login page only — credentials must be entered manually.


def show_demo_morning_context():
    """Show seeded morning check-in data above the input form."""
    resp = api_get("/demo/today-context")
    if resp.status_code != 200:
        return

    data = resp.json()
    morning_note = data.get("morning_note")
    tasks = data.get("tasks", [])
    overdue = data.get("overdue_tasks", [])

    if not morning_note and not tasks:
        return

    st.info("**Demo:** Today's check-in is already seeded. Add more tasks below or browse other sections.")
    if morning_note:
        st.markdown(f"**This morning you noted:** _{morning_note}_")

    if tasks:
        st.subheader("Today's plan (seeded)")
        for t in tasks:
            icon = CATEGORY_ICONS.get(t.get("category", "other"), ":material/push_pin:")
            urg = URGENCY_LABELS.get(t.get("urgency", "medium"), "")
            if t.get("completed_at"):
                st.write(f"{icon} ~~{t['title']}~~ `{urg}` _(done)_")
            elif t.get("skipped"):
                st.write(f"{icon} {t['title']} `{urg}` _(skipped)_")
            else:
                st.write(f"{icon} **{t['title']}** `{urg}` — _{t.get('category', 'other')}_")

    if overdue:
        st.warning(f"{len(overdue)} overdue task(s) from earlier this week:")
        for t in overdue:
            urg = URGENCY_LABELS.get(t.get("urgency", "medium"), "")
            st.write(f"- `{urg}` **{t['title']}** (due {t['due_date']})")

    st.divider()


# ═══ END DEMO BLOCK ═══════════════════════════════════════════════════════════


CATEGORY_ICONS = {
    "work":     ":material/work:",
    "personal": ":material/home:",
    "health":   ":material/fitness_center:",
    "learning": ":material/menu_book:",
    "other":    ":material/push_pin:",
}


# ─── AUTH PAGES ──────────────────────────────────────────────────────────────

def show_login():
    inject_login_styles()

    st.title("Personal Productivity Agent")
    st.caption("Check in every morning and evening to stay on top of your day.")

    # DEMO — remove before production
    if DEMO_MODE:
        st.success(f"Demo mode: log in as **{DEMO_USERNAME}** / `{DEMO_PASSWORD}`")

    tab_login, tab_register = st.tabs(["Login", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Fill in both fields.")
            else:
                resp = requests.post(
                    f"{API_BASE}/auth/login",
                    json={"username": username, "password": password},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    _clear_logout_flag()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["user_id"] = data["user_id"]
                    st.session_state["username"] = data["username"]
                    st.session_state["_auth_validated"] = True
                    st.session_state["_validated_token"] = data["access_token"]
                    st.rerun()
                else:
                    st.error("Wrong username or password.")

    with tab_register:
        with st.form("register_form"):
            new_email = st.text_input("Email", placeholder="you@example.com")
            new_username = st.text_input("Username", placeholder="Choose a username")
            new_password = st.text_input("Password", type="password", placeholder="Min. 6 characters")
            submitted_reg = st.form_submit_button("Create Account", use_container_width=True)

        if submitted_reg:
            if not new_email or not new_username or not new_password:
                st.error("All fields are required.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                resp = requests.post(
                    f"{API_BASE}/auth/register",
                    json={"email": new_email, "username": new_username, "password": new_password},
                    timeout=10,
                )
                if resp.status_code == 201:
                    data = resp.json()
                    _clear_logout_flag()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["user_id"] = data["user_id"]
                    st.session_state["username"] = data["username"]
                    st.session_state["_auth_validated"] = True
                    st.session_state["_validated_token"] = data["access_token"]
                    st.success("Account created!")
                    st.rerun()
                else:
                    detail = resp.json().get("detail", "Registration failed.")
                    st.error(detail)


# ─── MAIN PAGES ──────────────────────────────────────────────────────────────

def show_morning_checkin():
    st.header(":material/wb_sunny: Morning Check-in")
    st.caption(f"Today is {date.today().strftime('%A, %B %d %Y')}. What are you working on today?")

    # DEMO — remove before production
    if DEMO_MODE:
        show_demo_morning_context()

    render_morning_suggestions()

    if "morning_tasks_text" not in st.session_state:
        st.session_state.morning_tasks_text = ""

    with st.form("morning_form"):
        tasks_raw = st.text_area(
            "Your tasks for today",
            value=st.session_state.morning_tasks_text,
            placeholder="One task per line, e.g.\nFinish project report\nGo for a run\nCall dentist",
            height=200,
        )
        morning_note = st.text_input(
            "Anything else on your mind? (optional)",
            placeholder="Feeling focused, have a meeting at 3pm..."
        )
        submitted = st.form_submit_button("Start My Day", use_container_width=True, type="primary")

    if submitted:
        task_list = [t.strip() for t in tasks_raw.strip().splitlines() if t.strip()]
        if not task_list:
            st.error("Add at least one task.")
            return

        with st.spinner("Classifying your tasks and checking for overdue items..."):
            resp = api_post("/checkin/morning", {"tasks": task_list, "morning_note": morning_note})

        if resp.status_code == 200:
            st.session_state.morning_tasks_text = ""
            data = resp.json()
            classified = data.get("classified_tasks", [])
            overdue = data.get("overdue_tasks", [])

            st.success(f"Got it! {len(classified)} task(s) saved for today.")

            if overdue:
                st.warning(f"You have {len(overdue)} overdue task(s) from previous days:")
                for t in overdue:
                    urg = URGENCY_LABELS.get(t["urgency"], "")
                    st.write(f"- `{urg}` **{t['title']}** (due {t['due_date']})")

            if classified:
                st.subheader("Today's plan")
                for t in classified:
                    icon = CATEGORY_ICONS.get(t.get("category", "other"), ":material/push_pin:")
                    urg = URGENCY_LABELS.get(t.get("urgency", "medium"), "")
                    st.write(f"{icon} `{urg}` **{t['title']}** — _{t.get('category', 'other')}_")
        else:
            st.error(f"Something went wrong: {resp.json().get('detail', 'Unknown error')}")


def show_my_tasks():
    st.header(":material/checklist: My Tasks — Today")

    resp = api_get("/tasks/today")
    if resp.status_code != 200:
        st.info("No tasks yet. Do your morning check-in first!")
        return

    tasks = resp.json()
    if not tasks:
        st.info("No tasks for today. Head to Morning Check-in to add some.")
        return

    pending = [t for t in tasks if not t["completed_at"] and not t["skipped"]]
    done = [t for t in tasks if t["completed_at"]]
    skipped_tasks = [t for t in tasks if t["skipped"]]

    col1, col2, col3 = st.columns(3)
    col1.metric("Pending", len(pending))
    col2.metric("Done", len(done))
    col3.metric("Skipped", len(skipped_tasks))

    st.divider()

    if pending:
        st.subheader("Pending")
        for task in pending:
            icon = CATEGORY_ICONS.get(task["category"], ":material/push_pin:")
            urg = URGENCY_LABELS.get(task["urgency"], "")
            col_task, col_done, col_skip, col_del = st.columns([5, 1, 1, 1])
            col_task.write(f"{icon} `{urg}` **{task['title']}** — _{task['category']}_")
            if col_done.button("Done", key=f"done_{task['id']}", help="Mark complete"):
                api_post(f"/tasks/{task['id']}/complete", {})
                st.rerun()
            if col_skip.button("Skip", key=f"skip_{task['id']}", help="Skip"):
                api_post(f"/tasks/{task['id']}/skip", {})
                st.rerun()
            if col_del.button("Del", key=f"del_{task['id']}", help="Delete"):
                api_delete(f"/tasks/{task['id']}")
                st.rerun()

    if done:
        with st.expander(f"Completed ({len(done)})"):
            for task in done:
                icon = CATEGORY_ICONS.get(task["category"], ":material/push_pin:")
                st.write(f"{icon} ~~{task['title']}~~")

    if skipped_tasks:
        with st.expander(f"Skipped ({len(skipped_tasks)})"):
            for task in skipped_tasks:
                icon = CATEGORY_ICONS.get(task["category"], ":material/push_pin:")
                st.write(f"{icon} {task['title']}")


def show_evening_checkin():
    st.header(":material/bedtime: Evening Check-in")
    st.caption("Wrap up your day. Mark what you got done, and the agent will draft your summary.")

    resp = api_get("/tasks/today")
    if resp.status_code != 200 or not resp.json():
        st.info("No tasks for today. Do your morning check-in first.")
        return

    tasks = resp.json()
    pending = [t for t in tasks if not t["completed_at"] and not t["skipped"]]
    done = [t for t in tasks if t["completed_at"]]

    if done:
        st.success(f"Already completed: {len(done)} task(s).")

    with st.form("evening_form"):
        if pending:
            st.subheader("Remaining tasks — what got done?")
            completed_ids = []
            skipped_ids = []
            for task in pending:
                icon = CATEGORY_ICONS.get(task["category"], ":material/push_pin:")
                col_label, col_status = st.columns([4, 2])
                col_label.write(f"{icon} **{task['title']}**")
                status = col_status.radio(
                    "Status",
                    ["still pending", "completed", "skip"],
                    key=f"eve_{task['id']}",
                    horizontal=True,
                    label_visibility="collapsed",
                )
                if status == "completed":
                    completed_ids.append(task["id"])
                elif status == "skip":
                    skipped_ids.append(task["id"])
        else:
            completed_ids = []
            skipped_ids = []
            st.info("All tasks already marked — just add a note and generate your summary.")

        evening_note = st.text_area(
            "How did your day go? (optional)",
            placeholder="Got interrupted a lot, but made progress on the main thing...",
        )
        submitted = st.form_submit_button("Generate EOD Summary", use_container_width=True, type="primary")

    if submitted:
        with st.spinner("The agent is drafting your end-of-day summary..."):
            resp = api_post("/checkin/evening", {
                "completed_task_ids": completed_ids,
                "skipped_task_ids": skipped_ids,
                "evening_note": evening_note,
            })

        if resp.status_code == 200:
            data = resp.json()
            st.subheader(":material/summarize: Today's Summary")
            st.info(data["eod_summary"])

            if data.get("tomorrow_plan"):
                st.subheader(":material/event_note: Tomorrow's suggested plan")
                for i, item in enumerate(data["tomorrow_plan"], 1):
                    st.write(f"{i}. {item}")
        else:
            st.error(resp.json().get("detail", "Something went wrong."))


def show_eod_history():
    st.header(":material/calendar_today: EOD History")

    resp = api_get("/eod/history?limit=7")
    if resp.status_code != 200:
        st.info("No summaries yet. Do your first evening check-in.")
        return

    summaries = resp.json()
    if not summaries:
        st.info("No summaries yet.")
        return

    for s in summaries:
        with st.expander(s["summary_date"]):
            st.write(s["summary_text"])
            if s.get("tomorrow_plan"):
                try:
                    plan = json.loads(s["tomorrow_plan"])
                    if plan:
                        st.write("**Tomorrow's plan was:**")
                        for item in plan:
                            st.write(f"- {item}")
                except Exception:
                    pass


def show_week_view():
    st.header(":material/bar_chart: This Week")

    resp = api_get("/tasks/week")
    if resp.status_code != 200:
        st.warning("Couldn't load weekly stats.")
        return

    data = resp.json()

    st.caption(f"Week of {data['week_start']} to {data['week_end']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total tasks", data["total_tasks"])
    col2.metric("Completed", data["completed"])
    col3.metric("Slipped", data["slipped"])
    col4.metric("Completion rate", f"{data['completion_rate']}%")

    if data.get("by_category"):
        st.subheader("By category")
        cats = data["by_category"]
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            icon = CATEGORY_ICONS.get(cat, ":material/push_pin:")
            st.write(f"{icon} **{cat.capitalize()}** — {count} task(s)")

    if data.get("daily_summaries"):
        st.subheader("Daily summaries")
        for entry in data["daily_summaries"]:
            with st.expander(entry["date"]):
                st.write(entry["summary"])

    st.divider()
    st.subheader("Export")
    render_export_buttons()


def show_weekly_review():
    st.header(":material/manage_search: Weekly Review")
    st.caption("A pattern analysis of your week, generated every Sunday (or on demand below).")

    resp = api_get("/review/latest")
    if resp.status_code == 200:
        review = resp.json()
        st.info(review["review_text"])
        st.caption(f"Generated: {review['created_at'][:10]} | Week of {review['week_start']}")
    else:
        st.info("No weekly review yet.")

    st.divider()
    st.subheader("Generate review now")
    st.caption("Normally runs automatically every Sunday. Use this to trigger it manually.")
    if st.button("Generate weekly review", type="primary"):
        with st.spinner("Analysing your week..."):
            resp = api_post("/review/generate", {})
        if resp.status_code == 200:
            data = resp.json()
            st.success("Done!")
            st.info(data["review_text"])
        else:
            st.error("Something went wrong.")


# ─── LAYOUT ──────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Productivity Agent",
        page_icon=":material/bolt:",
        layout="centered",
    )

    # DEMO — remove before production
    if not ensure_authenticated():
        show_login()
        return

    with st.sidebar:
        username = st.session_state.get("username", "")
        st.markdown(f"**Person:** {username}")
        st.caption(f"Today: {date.today().strftime('%b %d, %Y')}")
        st.divider()

        page = st.radio(
            "Navigate",
            [
                "Dashboard",
                "Calendar",
                "Morning Check-in",
                "My Tasks",
                "Focus Mode",
                "Evening Check-in",
                "Chat with Agent",
                "EOD History",
                "This Week",
                "Weekly Review",
                "Export Reports",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()

    if page == "Dashboard":
        show_dashboard()
    elif page == "Calendar":
        show_calendar()
    elif page == "Morning Check-in":
        show_morning_checkin()
    elif page == "My Tasks":
        show_my_tasks()
    elif page == "Focus Mode":
        show_focus()
    elif page == "Evening Check-in":
        show_evening_checkin()
    elif page == "Chat with Agent":
        show_chat()
    elif page == "EOD History":
        show_eod_history()
    elif page == "This Week":
        show_week_view()
    elif page == "Weekly Review":
        show_weekly_review()
    elif page == "Export Reports":
        show_export()


if __name__ == "__main__":
    main()
