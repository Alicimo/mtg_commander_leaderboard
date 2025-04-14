import datetime
from typing import Dict, List, Optional, Tuple

import sqlalchemy as sa
import streamlit as st
from sqlalchemy.engine import Engine

from app.scryfall import get_player_commanders, search_commanders


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
) -> None:
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

        # Get commander IDs for all players
        commander_ids = {}
        for player, commander in commanders.items():
            # Find or create commander
            commander_id = conn.execute(
                sa.text(
                    "INSERT OR IGNORE INTO commanders (name, scryfall_id) "
                    "VALUES (:name, 'unknown') RETURNING id"
                ),
                {"name": commander},
            ).scalar()
            if not commander_id:  # If already exists
                commander_id = conn.execute(
                    sa.text("SELECT id FROM commanders WHERE name = :name"),
                    {"name": commander},
                ).scalar()
            commander_ids[player] = commander_id

        # Insert game record with winner's commander
        game_id = conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES (:date, :winner_id, :commander_id)"
            ),
            {
                "date": date, 
                "winner_id": winner_id, 
                "commander_id": commander_ids[winner]
            },
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
                    "commander_id": commander_ids[player],
                },
            )


def show_game_form(engine: Engine) -> None:
    """Render game submission form with commander selection."""
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

        # Commander selection for each player
        commanders = {}
        if selected_players:
            st.subheader("Commanders")
            for player in selected_players:
                # Get player's previous commanders first
                prev_commanders = get_player_commanders(engine, player)
                
                # Add search box for new commanders
                search_term = st.text_input(
                    f"Search commander for {player}",
                    value="",
                    key=f"commander_search_{player}",
                )
                
                # Combine previous and search results
                options = []
                if prev_commanders:
                    options.extend([(c["name"], "recent") for c in prev_commanders])
                
                if search_term:
                    search_results = search_commanders(engine, search_term)
                    options.extend([(c["name"], "search") for c in search_results])
                
                # Remove duplicates while preserving order
                seen = set()
                unique_options = []
                for name, source in options:
                    if name not in seen:
                        seen.add(name)
                        unique_options.append((name, source))
                
                # Show dropdown with sources indicated
                selected = st.selectbox(
                    f"Select commander for {player}",
                    options=[o[0] for o in unique_options],
                    format_func=lambda x: f"{x} (recent)" if any(o[0] == x and o[1] == "recent" for o in unique_options) else x,
                    key=f"commander_select_{player}",
                )
                commanders[player] = selected

        # Winner dropdown (only shows selected players)
        winner = st.selectbox(
            "Winner",
            options=selected_players,
            disabled=not selected_players,
        )

        submitted = st.form_submit_button("Submit Game")

        if submitted:
            try:
                submit_game(engine, game_date, selected_players, winner)
                st.success("Game submitted successfully!")
                st.rerun()  # Reset form
            except Exception as e:
                st.error(f"Error submitting game: {e}")
