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
        query = sa.text(
            f"SELECT id FROM players WHERE name IN ({','.join(['?']*len(players))})"
        )
        player_ids = conn.execute(query, players).fetchall()
        
        winner_id = conn.execute(
            sa.text("SELECT id FROM players WHERE name = :name"),
            {"name": winner}
        ).scalar()
        
        # Insert game record
        game_id = conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id) VALUES (:date, :winner_id)"
            ),
            {"date": date, "winner_id": winner_id}
        ).lastrowid
        
        # TODO: Add ELO calculations and commander selection
        # For now just record basic game info
        for player_id in player_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO game_players (game_id, player_id) "
                    "VALUES (:game_id, :player_id)"
                ),
                {"game_id": game_id, "player_id": player_id}
            )

def show_game_form(engine: Engine) -> None:
    """Render game submission form."""
    st.header("Submit New Game")
    
    with st.form("game_form"):
        # Date picker with today as default
        game_date = st.date_input(
            "Game Date",
            value=datetime.date.today(),
            max_value=datetime.date.today()
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
            if error:
                st.error(error)
            else:
                try:
                    submit_game(engine, game_date, selected_players, winner)
                    st.success("Game submitted successfully!")
                    st.rerun()  # Reset form
                except Exception as e:
                    st.error(f"Error submitting game: {e}")
