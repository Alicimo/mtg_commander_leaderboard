from unittest.mock import patch

import pytest
import sqlalchemy as sa

from app.db import get_engine, init_db
from app.scryfall import (
    cache_commanders,
    get_player_commanders,
    load_all_commanders,
    search_commanders,
)


@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Test database fixture"""
    db_path = tmp_path / "test.db"
    if db_path.exists():
        db_path.unlink()
    engine = get_engine(db_path)
    init_db(engine)
    yield engine
    engine.dispose()


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
        ],
        "has_more": False,
    }


def test_load_all_commanders(mock_scryfall_response, test_db):
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_scryfall_response
        mock_get.return_value.raise_for_status.return_value = None

        load_all_commanders(test_db)

        # Verify commanders were loaded
        with test_db.connect() as conn:
            count = conn.execute(sa.text("SELECT COUNT(*) FROM commanders")).scalar()
            assert count == 2
            names = [
                r[0]
                for r in conn.execute(sa.text("SELECT name FROM commanders")).fetchall()
            ]
            assert "Atraxa, Praetors' Voice" in names
            assert "Kinnan, Bonder Prodigy" in names


def test_search_commanders_local(test_db):
    # Seed some test data
    with test_db.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) "
                "VALUES ('Test Commander', '123'), ('Another Commander', '456')"
            )
        )

    results = search_commanders(test_db, "test")
    assert len(results) == 1
    assert results[0]["name"] == "Test Commander"


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
        conn.execute(sa.text("INSERT INTO players (name, elo) VALUES ('Alice', 1000)"))
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
    assert results[0] == "Commander B"
    assert results[1] == "Commander A"
