"""Focus mode — Pomodoro timer linked to today's tasks."""

from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

from api_client import api_get, api_post


def _countdown_html(end_iso: str, task_title: str, duration: int) -> str:
    safe_title = task_title.replace('"', "&quot;")
    return f"""
    <div style="text-align:center;padding:24px;font-family:sans-serif;">
        <div style="font-size:1.1rem;color:#666;margin-bottom:8px;">Focusing on</div>
        <div style="font-size:1.3rem;font-weight:bold;margin-bottom:20px;">{safe_title}</div>
        <div id="timer" style="font-size:3.5rem;font-weight:bold;color:#FF4B4B;"></div>
        <div style="font-size:0.9rem;color:#888;margin-top:12px;">Pomodoro — {duration} min</div>
    </div>
    <script>
        const end = new Date("{end_iso}").getTime();
        const el = document.getElementById("timer");
        function tick() {{
            const left = Math.max(0, Math.floor((end - Date.now()) / 1000));
            const m = Math.floor(left / 60);
            const s = left % 60;
            el.textContent = m + ":" + String(s).padStart(2, "0");
            if (left > 0) setTimeout(tick, 1000);
            else el.textContent = "Done!";
        }}
        tick();
    </script>
    """


def show_focus():
    st.header("Focus Mode")
    st.caption("Pick a task and run a Pomodoro session.")

    stats_resp = api_get("/pomodoro/today")
    stats = stats_resp.json() if stats_resp.status_code == 200 else {"count": 0, "total_minutes": 0, "sessions": []}

    c1, c2 = st.columns(2)
    c1.metric("Pomodoros today", stats["count"])
    c2.metric("Focus minutes", stats["total_minutes"])

    tasks_resp = api_get("/tasks/today")
    pending = []
    if tasks_resp.status_code == 200:
        pending = [
            t for t in tasks_resp.json()
            if not t["completed_at"] and not t["skipped"]
        ]

    st.divider()

    if st.session_state.get("pomo_running"):
        end: datetime = st.session_state.pomo_end
        task_title = st.session_state.pomo_task
        duration = st.session_state.get("pomo_duration", 25)

        if datetime.now() >= end:
            st.success(f"Pomodoro complete — great work on **{task_title}**!")
            api_post("/pomodoro/complete", {
                "task_title": task_title,
                "duration_minutes": duration,
            })
            st.session_state.pomo_running = False
            for key in ("pomo_end", "pomo_task", "pomo_duration"):
                st.session_state.pop(key, None)
            st.rerun()
        else:
            components.html(
                _countdown_html(end.isoformat(), task_title, duration),
                height=200,
            )
            if st.button("Stop session", type="secondary"):
                st.session_state.pomo_running = False
                for key in ("pomo_end", "pomo_task", "pomo_duration"):
                    st.session_state.pop(key, None)
                st.rerun()
            st.caption("Timer updates live above.")
        return

    st.subheader("Start a session")

    duration = st.selectbox("Duration (minutes)", [15, 25, 45], index=1)

    if pending:
        selected = st.selectbox("Task to focus on", [t["title"] for t in pending])
    else:
        selected = st.text_input("Task to focus on", placeholder="What are you working on?")
        if not selected:
            st.info("No pending tasks today — type a custom focus task above.")

    if st.button(f"Start {duration}-min Pomodoro", type="primary", use_container_width=True):
        if selected:
            st.session_state.pomo_running = True
            st.session_state.pomo_task = selected
            st.session_state.pomo_duration = duration
            st.session_state.pomo_end = datetime.now() + timedelta(minutes=duration)
            st.rerun()
        else:
            st.error("Pick or enter a task first.")

    if stats.get("sessions"):
        st.divider()
        st.subheader("Today's sessions")
        for s in stats["sessions"]:
            ts = s["completed_at"][:16].replace("T", " ")
            st.write(f"- **{s['task_title']}** — {s['duration_minutes']} min at {ts}")
