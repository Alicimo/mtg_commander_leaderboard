import datetime
from typing import List, Optional

import sqlalchemy as sa
import streamlit as st
from sqlalchemy.engine import Engine


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
    winner: str,
) -> None:
    """Submit a game to the database.

    Args:
        engine: SQLAlchemy engine
        date: Game date
        players: List of player names
        winner: Name of winner
    """
    with engine.begin() as conn:
        # Get player IDs
        # SQLite requires expanding the IN clause parameters
        placeholders = ",".join([f":name{i}" for i in range(len(players))])
        query = sa.text(f"SELECT id FROM players WHERE name IN ({placeholders})")
        params = {f"name{i}": name for i, name in enumerate(players)}
        player_ids = [p.id for p in conn.execute(query, params).fetchall()]

        winner_id = conn.execute(
            sa.text("SELECT id FROM players WHERE name = :name"), {"name": winner}
        ).scalar()

        # Get a default commander ID (for testing)
        commander_id = conn.execute(
            sa.text("SELECT id FROM commanders LIMIT 1")
        ).scalar()
        if not commander_id:
            # If no commanders exist, create a default one
            commander_id = conn.execute(
                sa.text(
                    "INSERT INTO commanders (name, scryfall_id) "
                    "VALUES ('Unknown Commander', 'default')"
                )
            ).lastrowid

        # Insert game record with required commander ID
        game_id = conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES (:date, :winner_id, :commander_id)"
            ),
            {"date": date, "winner_id": winner_id, "commander_id": commander_id},
        ).lastrowid

        # Record all players in the game with their commanders
        for player_id in player_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO game_players "
                    "(game_id, player_id, commander_id, elo_change) "
                    "VALUES (:game_id, :player_id, :commander_id, 0)"
                ),
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "commander_id": commander_id,
                },
            )


def show_game_form(engine: Engine) -> None:
    """Render game submission form."""
    st.header("Submit New Game")

    with st.form("game_form"):
        # Date picker with today as default
        game_date = st.date_input(
            "Game Date", value=datetime.date.today(), max_value=datetime.date.today()
        )

        # Get all players from DB
        with engine.connect() as conn:
            players = conn.execute(
                sa.text("SELECT name FROM players ORDER BY name")
            ).fetchall()
            player_names = [p.name for p in players]

        # Multi-select players
        selected_players = st.multiselect(
            "Players",
            options=player_names,
            default=None,
        )

        # Winner dropdown (only shows selected players)
        winner = st.selectbox(
            "Winner",
            options=selected_players,
            disabled=not selected_players,
        )

        submitted = st.form_submit_button("Submit Game")

        if submitted:
            error = validate_game_submission(selected_players, winner)
            print(error)
            if error:
                st.error(error)
            else:
                try:
                    submit_game(engine, game_date, selected_players, winner)
                    st.success("Game submitted successfully!")
                    st.rerun()  # Reset form
                except Exception as e:
                    st.error(f"Error submitting game: {e}")
