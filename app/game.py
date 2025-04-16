import datetime
from typing import Dict, List, Optional

import sqlalchemy as sa
import streamlit as st
from sqlalchemy.engine import Engine

from app.elo import update_elos_in_db
from app.scryfall import get_player_commanders


def validate_game_submission(players: List[str], winner: str) -> Optional[str]:
    """Validate game submission data.

    Args:
        players: List of player names
        winner: Name of winner

    Returns:
        str: Error message if invalid, None if valid
    """
    if len(players) < 2:
        return "At least 2 players required"
    if winner not in players:
        return "Winner must be one of the selected players"
    return None


def submit_game(
    engine: Engine,
    date: datetime.date,
    players: List[str],
    commanders: Dict[str, str],
    winner: str,
) -> Dict[str, float]:
    """Submit a game to the database.

    Args:
        engine: SQLAlchemy engine
        date: Game date
        players: List of player names
        winner: Name of winner

    Raises:
        ValueError: If winner is not in players list
    """
    error = validate_game_submission(players, winner)
    if error:
        raise ValueError(error)

    with engine.connect() as conn:
        winner_id = conn.execute(
            sa.text("SELECT id FROM players WHERE name = :name"), {"name": winner}
        ).scalar()

        # Get player and commander IDs for all players
        player_ids = {}
        commander_ids = {}
        for player, commander in commanders.items():
            player_ids[player] = conn.execute(
                sa.text("SELECT id FROM players WHERE name = :name"),
                {"name": player},
            ).scalar()
            commander_ids[player] = conn.execute(
                sa.text("SELECT id FROM commanders WHERE name = :name"),
                {"name": commander},
            ).scalar()

        # Insert game record with winner's commander
        game_id = conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES (:date, :winner_id, :commander_id)"
            ),
            {
                "date": date,
                "winner_id": winner_id,
                "commander_id": commander_ids[winner],
            },
        ).lastrowid

        # Record all players in the game with their commanders (initial 0 delta)
        for player in commanders:
            conn.execute(
                sa.text(
                    "INSERT INTO game_players "
                    "(game_id, player_id, commander_id, elo_change) "
                    "VALUES (:game_id, :player_id, :commander_id, 0)"
                ),
                {
                    "game_id": game_id,
                    "player_id": player_ids[player],
                    "commander_id": commander_ids[player],
                },
            )

        # Calculate and apply ELO changes
        loser_ids = [pid for pid in player_ids.values() if pid != winner_id]
        conn.commit()
    return update_elos_in_db(engine, game_id, winner_id, loser_ids)


def show_game_form(engine: Engine) -> None:
    """Render game submission form with commander selection."""

    if "form_stage" not in st.session_state:
        st.session_state.form_stage = "select_players"
    if "game_date" not in st.session_state:
        st.session_state.game_date = datetime.date.today()
    if "selected_players" not in st.session_state:
        st.session_state.selected_players = []

    st.header("Submit New Game")

    if st.session_state.form_stage == "select_players":
        with st.form("form_select_players"):
            # Game Date
            st.session_state.game_date = st.date_input(
                "Game Date",
                value=st.session_state.game_date,
                max_value=datetime.date.today(),
            )

            # Get all players from DB
            with engine.connect() as conn:
                players = conn.execute(
                    sa.text("SELECT name FROM players ORDER BY name")
                ).fetchall()
                player_names = [p.name for p in players]

            # Multi-select players
            st.session_state.selected_players = st.multiselect(
                "Players",
                options=player_names,
                default=st.session_state.selected_players,
            )
            submitted_players = st.form_submit_button("Next")

            if submitted_players and st.session_state.selected_players:
                st.session_state.form_stage = "add_commanders"
                st.rerun()

    elif st.session_state.form_stage == "add_commanders":
        with st.form("form_add_commanders"):
            winner = st.selectbox(
                "Winner",
                options=st.session_state.selected_players,
            )

            with engine.connect() as conn:
                commanders = conn.execute(
                    sa.text("SELECT name FROM commanders ORDER BY name")
                ).fetchall()
                commander_names = [c.name for c in commanders]

            st.subheader("Commanders")
            submitted_commanders = {}
            for player in st.session_state.selected_players:
                prev_commanders = get_player_commanders(engine, player)
                other_commanders = commander_names.copy()
                for prev in prev_commanders:
                    other_commanders.remove(prev)
                selected = st.selectbox(
                    f"Select commander for {player}",
                    options=prev_commanders + other_commanders,
                    key=f"commander_select_{player}",
                )
                submitted_commanders[player] = selected

            submitted = st.form_submit_button("Submit Game")

        if submitted:
            try:
                submit_game(
                    engine,
                    st.session_state.game_date,
                    st.session_state.selected_players,
                    submitted_commanders,
                    winner,
                )
                st.session_state.form_stage = "success"
                st.session_state.selected_players = []
                st.rerun()
            except Exception as e:
                st.error(f"Error submitting game: {e}")

        # Add a back button
        if st.button("Back to player selection"):
            st.session_state.form_stage = "select_players"
            st.rerun()

    # display balloons and reset the flag
    elif st.session_state.form_stage == "success":
        st.balloons()
        st.success("Game submitted successfully!")
        if st.button("Submit another game"):
            st.session_state.form_stage = "select_players"
            st.rerun()
