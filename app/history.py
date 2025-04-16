import streamlit as st
from sqlalchemy.engine import Engine

from app.db import get_game_history


def show_game_history(engine: Engine) -> None:
    """Render paginated game history table."""
    st.header("Game History")

    # Initialize pagination state
    if "history_page" not in st.session_state:
        st.session_state.history_page = 1

    # Get paginated results
    games, total = get_game_history(engine, st.session_state.history_page)

    if not games:
        st.info("No games recorded yet")
        return

    # Show pagination controls
    cols = st.columns([1, 2, 1])
    with cols[0]:
        if st.button("Previous", disabled=st.session_state.history_page <= 1):
            st.session_state.history_page -= 1
            st.rerun()
    with cols[1]:
        st.caption(
            f"Page {st.session_state.history_page} of {max(1, (total + 19) // 20)}"
        )
    with cols[2]:
        if st.button("Next", disabled=st.session_state.history_page * 20 >= total):
            st.session_state.history_page += 1
            st.rerun()

    # Display table
    st.dataframe(
        games,
        column_config={
            "date": st.column_config.DateColumn("Date"),
            "winner": "Winner (Commander)",
            "losers": "Losers (Commanders)",
            "elo_changes": st.column_config.TextColumn(
                "ELO Changes", help="Winner gain / Losers loss"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
