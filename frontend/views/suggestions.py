"""Smart task suggestions for morning check-in."""

import streamlit as st

from api_client import api_get


def render_morning_suggestions():
    """Show rule-based suggestions above the morning check-in form."""
    resp = api_get("/suggestions/tasks")
    if resp.status_code != 200:
        return

    suggestions = resp.json().get("suggestions", [])
    if not suggestions:
        return

    if "morning_tasks_text" not in st.session_state:
        st.session_state.morning_tasks_text = ""

    st.subheader("Suggested for today")
    st.caption("Based on overdue items and your weekly patterns.")

    for i, s in enumerate(suggestions):
        col_text, col_btn = st.columns([5, 1])
        priority = s.get("priority", "medium")
        badge = {"high": "HIGH", "medium": "MED", "low": "LOW"}.get(priority, "MED")
        col_text.markdown(f"**{s['title']}** `[{badge}]` — _{s['reason']}_")
        if col_btn.button("Add", key=f"sug_add_{i}", use_container_width=True):
            current = st.session_state.morning_tasks_text.strip()
            title = s["title"]
            if title not in current.splitlines():
                st.session_state.morning_tasks_text = f"{current}\n{title}".strip()
            st.rerun()

    if st.session_state.morning_tasks_text.strip():
        if st.button("Clear suggestion queue", key="clear_sug_queue"):
            st.session_state.morning_tasks_text = ""
            st.rerun()

    st.divider()
