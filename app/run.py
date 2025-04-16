import sys

import streamlit as st

from app.admin import show_admin_page
from app.auth import login_form
from app.db import get_engine, init_db
from app.game import show_game_form
from app.leaderboard import show_leaderboard
from app.scryfall import load_all_commanders

print(sys.path)
sys.path.append(".")


def main():
    st.set_page_config(
        page_title="MTG Commander Leaderboard",
        page_icon="🎲",
        layout="wide",
    )

    engine = get_engine()
    init_db(engine)  # Ensure tables exist
    load_all_commanders(engine)  # Pre-load commanders

    if "admin" not in st.session_state:
        st.session_state.admin = False

    if st.session_state.admin:
        if not login_form():
            st.stop()  # Don't proceed unless authenticated
        show_admin_page(engine)
    else:
        st.title("MTG Commander Leaderboard")

        tab1, tab2, tab3 = st.tabs(["Leaderboard", "Submit Game", "Game History"])

        with tab1:
            show_leaderboard(engine)

        with tab2:
            show_game_form(engine)

        with tab3:
            from app.history import show_game_history

            show_game_history(engine)

        if st.sidebar.button("Go to Admin Dashboard"):
            st.session_state.admin = True
            st.rerun()


if __name__ == "__main__":
    main()
