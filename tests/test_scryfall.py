import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests
import sqlalchemy as sa

from app.scryfall import (
    cache_commanders,
    get_cached_commanders,
    get_player_commanders,
    get_similar_cached_commanders,
    search_commanders,
)


@pytest.fixture
def mock_scryfall_response():
    return {
        "data": [
            {
                "id": "123",
                "name": "Atraxa, Praetors' Voice",
                "image_uris": {"normal": "image_url"},
            },
            {
                "id": "456",
                "name": "Kinnan, Bonder Prodigy",
                "image_uris": {"normal": "image_url"},
            },
        ]
    }


def test_search_commanders_api_success(mock_scryfall_response, test_db):
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_scryfall_response
        mock_get.return_value.raise_for_status.return_value = None

        results = search_commanders(test_db, "atraxa")
        assert len(results) == 2
        assert results[0]["name"] == "Atraxa, Praetors' Voice"
        assert results[0]["scryfall_id"] == "123"


def test_search_commanders_api_fallback(test_db):
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException

        # First seed some cached data
        with test_db.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO commanders (name, scryfall_id, last_searched) "
                    "VALUES ('Cached Commander', '789', :now)"
                ),
                {"now": datetime.datetime.now()},
            )

        results = search_commanders(test_db, "cached")
        assert len(results) == 1
        assert results[0]["name"] == "Cached Commander"


def test_cache_commanders(test_db):
    commanders = [
        {"name": "Test Commander", "scryfall_id": "111", "image_url": ""},
        {"name": "Another Commander", "scryfall_id": "222", "image_url": ""},
    ]
    cache_commanders(test_db, "test", commanders)

    with test_db.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM commanders")).scalar()
        assert count == 2


def test_get_player_commanders(test_db):
    # Setup test data
    with test_db.begin() as conn:
        # Add players
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Alice', 1000)")
        )
        alice_id = conn.execute(
            sa.text("SELECT id FROM players WHERE name = 'Alice'")
        ).scalar()
        
        # Add commanders
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) "
                "VALUES ('Commander A', '111'), ('Commander B', '222')"
            )
        )
        
        # Add games
        conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES ('2024-01-01', :aid, 1), ('2024-01-02', :aid, 2)"
            ),
            {"aid": alice_id},
        )
        
        # Add game players
        conn.execute(
            sa.text(
                "INSERT INTO game_players (game_id, player_id, commander_id, elo_change) "
                "VALUES (1, :aid, 1, 10), (2, :aid, 2, 10)"
            ),
            {"aid": alice_id},
        )

    results = get_player_commanders(test_db, "Alice")
    assert len(results) == 2
    # Should be ordered by most recent first
    assert results[0]["name"] == "Commander B"
    assert results[1]["name"] == "Commander A"
