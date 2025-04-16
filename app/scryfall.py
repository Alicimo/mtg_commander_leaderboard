import datetime
import time
from typing import Dict, List

import requests
import sqlalchemy as sa
from sqlalchemy.engine import Engine

SCRYFALL_API = "https://api.scryfall.com"
RATE_LIMIT = 0.1  # 100ms between calls (Scryfall's rate limit)
LAST_CALL_TIME = 0


def _rate_limit() -> None:
    """Enforce rate limiting between Scryfall API calls."""
    global LAST_CALL_TIME
    elapsed = time.time() - LAST_CALL_TIME
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST_CALL_TIME = time.time()


def load_all_commanders(engine: Engine) -> None:
    """Load all legal commanders from Scryfall into cache."""
    # Check if we already have commanders loaded
    with engine.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM commanders")).scalar()
        if count > 0:
            return

    # Get all commanders in one bulk request
    commanders = []
    page = 0
    while page := page + 1:
        try:
            response = requests.get(
                f"{SCRYFALL_API}/cards/search",
                params={"q": "legal:commander is:commander", "page": page},
                timeout=30,
            )
            response.raise_for_status()
            _rate_limit()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to load commanders: {e}")

        for card in response.json()["data"]:
            commanders.append({"name": card["name"], "scryfall_id": card["id"]})

        if not response.json()["has_more"]:
            break

    # Bulk insert
    with engine.begin() as conn:
        for cmd in commanders:
            conn.execute(
                sa.text(
                    "INSERT OR IGNORE INTO commanders (name, scryfall_id) "
                    "VALUES (:name, :scryfall_id)"
                ),
                {"name": cmd["name"], "scryfall_id": cmd["scryfall_id"]},
            )


def search_commanders(engine: Engine, query: str) -> List[Dict[str, str]]:
    """Search for commanders using local cache only."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text(
                "SELECT name, scryfall_id FROM commanders "
                "WHERE name LIKE :query "
                "ORDER BY name LIMIT 20"
            ),
            {"query": f"%{query}%"},
        ).fetchall()
        return [dict(r._mapping) for r in results]


def cache_commanders(
    engine: Engine, query: str, commanders: List[Dict[str, str]]
) -> None:
    """Cache commander search results."""
    with engine.begin() as conn:
        for cmd in commanders:
            # Upsert commander
            conn.execute(
                sa.text(
                    "INSERT OR IGNORE INTO commanders (name, scryfall_id) "
                    "VALUES (:name, :scryfall_id)"
                ),
                {"name": cmd["name"], "scryfall_id": cmd["scryfall_id"]},
            )
            # Update cache timestamp
            conn.execute(
                sa.text(
                    "UPDATE commanders SET last_searched = :now "
                    "WHERE scryfall_id = :scryfall_id"
                ),
                {"now": datetime.datetime.now(), "scryfall_id": cmd["scryfall_id"]},
            )


def get_player_commanders(engine: Engine, player_name: str) -> list[str]:
    """Get commanders a player has used before, ordered by most recent."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text(
                "SELECT c.name FROM commanders c "
                "JOIN game_players gp ON gp.commander_id = c.id "
                "JOIN players p ON gp.player_id = p.id "
                "WHERE p.name = :name "
                "GROUP BY c.id, c.name "
                "ORDER BY MAX(gp.game_id) DESC "
                "LIMIT 3"
            ),
            {"name": player_name},
        ).fetchall()
        return [r.name for r in results]
