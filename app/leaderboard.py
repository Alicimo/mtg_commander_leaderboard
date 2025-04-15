import streamlit as st
from sqlalchemy.engine import Engine

from app.db import get_player_leaderboard, get_player_commander_leaderboard


def show_leaderboard(engine: Engine) -> None:
    """Render the leaderboard interface with toggle between views."""
    st.header("Leaderboards")
    
    # Toggle between views
    view_type = st.radio(
        "View:",
        ["Player Rankings", "Player + Commander Stats"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if view_type == "Player Rankings":
        show_player_leaderboard(engine)
    else:
        show_player_commander_leaderboard(engine)


def show_player_leaderboard(engine: Engine) -> None:
    """Display player-only leaderboard."""
    data = get_player_leaderboard(engine)
    
    if not data:
        st.info("No players yet - submit some games!")
        return
    
    st.subheader("Player Rankings")
    st.dataframe(
        data,
        column_config={
            "rank": "Rank",
            "name": "Player",
            "elo": st.column_config.NumberColumn(
                "ELO Rating",
                format="%.0f",
                help="Current ELO rating (higher is better)"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


def show_player_commander_leaderboard(engine: Engine) -> None:
    """Display player+commander leaderboard."""
    data = get_player_commander_leaderboard(engine)
    
    if not data:
        st.info("Not enough games yet - need at least 3 games per commander")
        return
    
    st.subheader("Player + Commander Stats")
    st.dataframe(
        data,
        column_config={
            "rank": "Rank",
            "player_name": "Player",
            "commander_name": "Commander",
            "avg_elo_change": st.column_config.NumberColumn(
                "Avg ELO Change",
                format="+%.1f",
                help="Average ELO change per game with this commander"
            ),
            "games_played": st.column_config.NumberColumn(
                "Games Played",
                format="%d",
                help="Total games with this commander"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
