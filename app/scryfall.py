import datetime
import time
from typing import Dict, List, Optional

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


def search_commanders(engine: Engine, query: str) -> List[Dict[str, str]]:
    """Search for commanders using Scryfall API with caching."""
    _rate_limit()
    
    # First check cache
    cached = get_cached_commanders(engine, query)
    if cached:
        return cached

    try:
        response = requests.get(
            f"{SCRYFALL_API}/cards/search",
            params={
                "q": f"{query} is:commander",
                "unique": "cards",
                "order": "edhrec",
            },
            timeout=5,
        )
        response.raise_for_status()
        
        commanders = []
        for card in response.json()["data"]:
            commanders.append({
                "name": card["name"],
                "scryfall_id": card["id"],
                "image_url": card.get("image_uris", {}).get("normal", "")
            })
        
        # Cache results
        cache_commanders(engine, query, commanders)
        return commanders
        
    except (requests.RequestException, KeyError):
        # Fall back to any cached results (even if not exact match)
        return get_similar_cached_commanders(engine, query)


def cache_commanders(
    engine: Engine, 
    query: str, 
    commanders: List[Dict[str, str]]
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


def get_cached_commanders(engine: Engine, query: str) -> List[Dict[str, str]]:
    """Get exact match cached commanders."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text(
                "SELECT name, scryfall_id FROM commanders "
                "WHERE name LIKE :query AND last_searched > :expiry "
                "ORDER BY last_searched DESC LIMIT 20"
            ),
            {
                "query": f"%{query}%",
                "expiry": datetime.datetime.now() - datetime.timedelta(days=7),
            },
        ).fetchall()
        return [dict(r._mapping) for r in results]


def get_similar_cached_commanders(engine: Engine, query: str) -> List[Dict[str, str]]:
    """Get loosely matching cached commanders when API fails."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text(
                "SELECT name, scryfall_id FROM commanders "
                "WHERE name LIKE :query ORDER BY last_searched DESC LIMIT 10"
            ),
            {"query": f"%{query}%"},
        ).fetchall()
        return [dict(r._mapping) for r in results]


def get_player_commanders(engine: Engine, player_name: str) -> List[Dict[str, str]]:
    """Get commanders a player has used before, ordered by most recent."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text(
                "SELECT c.name, c.scryfall_id FROM commanders c "
                "JOIN game_players gp ON gp.commander_id = c.id "
                "JOIN players p ON gp.player_id = p.id "
                "WHERE p.name = :name "
                "GROUP BY c.id ORDER BY MAX(gp.game_id) DESC LIMIT 5"
            ),
            {"name": player_name},
        ).fetchall()
        return [dict(r._mapping) for r in results]
