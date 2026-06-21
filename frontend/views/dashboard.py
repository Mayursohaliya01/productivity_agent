"""Dashboard / analytics page."""

import plotly.graph_objects as go
import streamlit as st

from api_client import api_get
from constants import CATEGORY_COLORS, CATEGORY_LABELS
from views.export import render_export_buttons


def show_dashboard():
    st.header("Dashboard")
    st.caption("Your productivity at a glance — this week's trends and streaks.")

    resp = api_get("/analytics/dashboard")
    if resp.status_code != 200:
        st.warning("Couldn't load dashboard data.")
        return

    data = resp.json()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Check-in streak", f"{data['streak']} day(s)", help="Consecutive days with a morning check-in")
    col2.metric("Tasks this week", data["total_tasks"])
    col3.metric("Completed", data["completed"])
    col4.metric("Completion rate", f"{data['completion_rate']}%")

    st.caption(f"Week of {data['week_start']} to {data['week_end']}")
    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Daily completion")
        daily = data.get("daily_completion", [])
        if daily and any(d["total"] > 0 for d in daily):
            labels = [d["date"][5:] for d in daily]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Completed",
                x=labels,
                y=[d["completed"] for d in daily],
                marker_color="#54A24B",
            ))
            fig.add_trace(go.Bar(
                name="Remaining",
                x=labels,
                y=[d["total"] - d["completed"] for d in daily],
                marker_color="#E8E8E8",
            ))
            fig.update_layout(
                barmode="stack",
                height=320,
                margin=dict(l=20, r=20, t=30, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis_title="Day (Mon–Sun)",
                yaxis_title="Tasks",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tasks logged this week yet.")

    with chart_col2:
        st.subheader("Tasks by category")
        cats = data.get("by_category", {})
        if cats:
            keys = list(cats.keys())
            labels = [CATEGORY_LABELS.get(k, k.capitalize()) for k in keys]
            colors = [CATEGORY_COLORS.get(k, "#999999") for k in keys]
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=[cats[k] for k in keys],
                marker=dict(colors=colors),
                hole=0.35,
            )])
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data yet.")

    st.divider()
    st.subheader("Export")
    render_export_buttons()
