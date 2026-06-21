"""Chat with the productivity agent."""

import streamlit as st

from api_client import api_post


def show_chat():
    st.header("Chat with Agent")
    st.caption("Ask about priorities, overdue tasks, weekly patterns, and more.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("Clear chat", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask your productivity agent..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            resp = api_post("/chat", {
                "message": prompt,
                "history": st.session_state.chat_history[:-1],
            })

        if resp.status_code == 200:
            reply = resp.json()["reply"]
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
        else:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Sorry, I couldn't process that. Is the backend running?",
            })
        st.rerun()

    if not st.session_state.chat_history:
        st.info("Try: *What should I focus on today?* or *How is my week going?*")
