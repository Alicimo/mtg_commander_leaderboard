import datetime
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa

from app.db import (
    SCHEMA_VERSION,
    backup_sqlite_db,
    check_connection,
    export_db_to_json,
    get_engine,
    get_game_history,
    get_player_commander_leaderboard,
    get_player_leaderboard,
    init_db,
)

# Define test data directory relative to this file
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DB_PATH = TEST_DATA_DIR / "test_commander.db"


@pytest.fixture(scope="function")
def test_db():
    """Fixture to initialize a clean test database for each test function."""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    # Ensure clean state before test
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = get_engine(db_path=TEST_DB_PATH)
    init_db(engine)
    yield engine  # Provide the engine to the test

    # Cleanup after test
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_DATA_DIR.exists() and not any(TEST_DATA_DIR.iterdir()):
        TEST_DATA_DIR.rmdir()  # Remove dir only if empty


def test_db_initialization(test_db):
    """Test database initialization creates tables."""
    inspector = sa.inspect(test_db)
    assert inspector.has_table("players")
    assert inspector.has_table("commanders")
    assert inspector.has_table("games")
    assert inspector.has_table("game_players")


def test_table_structures(test_db):
    """Verify table columns match spec."""
    inspector = sa.inspect(test_db)

    # Test players table
    players_cols = {
        c["name"]: type(c["type"]) for c in inspector.get_columns("players")
    }
    assert players_cols == {
        "id": sa.INTEGER,
        "name": sa.VARCHAR,
        "elo": sa.FLOAT,
    }

    # Test commanders table
    commanders_cols = {
        c["name"]: type(c["type"]) for c in inspector.get_columns("commanders")
    }
    assert commanders_cols == {
        "id": sa.INTEGER,
        "name": sa.VARCHAR,
        "scryfall_id": sa.VARCHAR,
        "last_searched": sa.DATETIME,
    }


def test_connection_working(test_db):
    """Test connection check works."""
    assert check_connection(test_db)


def test_connection_failure():
    """Test connection check fails gracefully."""
    # Use a non-existent path
    bad_engine = get_engine(db_path=TEST_DATA_DIR / "non_existent.db")
    assert not check_connection(bad_engine)


# Patch DB_PATH for export functions during testing
@patch("app.db.DB_PATH", TEST_DB_PATH)
def test_backup_sqlite_db(test_db):
    """Test SQLite database backup function."""
    backup_dir = TEST_DATA_DIR / "backups_db_test"
    backup_dir.mkdir(exist_ok=True)

    try:
        backup_path = backup_sqlite_db(target_dir=backup_dir)
        assert backup_path.exists()
        assert backup_path.parent == backup_dir
        assert backup_path.name.startswith("commander_backup_")
        assert backup_path.name.endswith(".db")
        assert backup_path.stat().st_size > 0  # Check file is not empty

        # Simple check: try to connect to the backup
        backup_engine = get_engine(db_path=backup_path)
        assert check_connection(backup_engine)
        backup_engine.dispose()

    finally:
        # Clean up backup file and directory
        if "backup_path" in locals() and backup_path.exists():
            backup_path.unlink()
        if backup_dir.exists():
            shutil.rmtree(backup_dir)


def test_get_player_leaderboard(test_db):
    """Test player leaderboard query."""
    with test_db.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES (:name, :elo)"),
            [
                {"name": "Alice", "elo": 1050},
                {"name": "Bob", "elo": 950},
                {"name": "Charlie", "elo": 1000},
            ],
        )

    results = get_player_leaderboard(test_db)
    assert len(results) == 3
    assert results[0]["name"] == "Alice"
    assert results[0]["rank"] == 1
    assert results[1]["name"] == "Charlie"
    assert results[1]["rank"] == 2
    assert results[2]["name"] == "Bob"
    assert results[2]["rank"] == 3


def test_get_game_history(test_db):
    """Test game history pagination."""
    # Setup test data
    with test_db.begin() as conn:
        # Add players
        conn.execute(
            sa.text(
                "INSERT INTO players (name, elo) VALUES ('Alice', 1000), ('Bob', 1000)"
            )
        )
        # Add commanders
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) VALUES ('CmdA', '1'), ('CmdB', '2')"
            )
        )
        # Add 25 test games
        for i in range(1, 26):
            conn.execute(
                sa.text(
                    "INSERT INTO games (date, winner_id, winner_commander_id) "
                    "VALUES (:date, 1, 1)"
                ),
                {"date": datetime.date(2024, 1, i)},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO game_players (game_id, player_id, commander_id, elo_change) "
                    "VALUES (:gid, 1, 1, 10), (:gid, 2, 2, -10)"
                ),
                {"gid": i},
            )

    # Test pagination
    page1, total = get_game_history(test_db, page=1)
    assert len(page1) == 20
    assert total == 25
    assert page1[0]["date"] == "2024-01-01"  # Oldest first

    page2, total = get_game_history(test_db, page=2)
    assert len(page2) == 5
    assert page2[0]["date"] == "2024-01-21"


def test_get_player_commander_leaderboard(test_db):
    """Test player+commander leaderboard query."""
    # Setup test data
    with test_db.begin() as conn:
        # Add players
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES (:name, :elo)"),
            [
                {"name": "Alice", "elo": 1000},
                {"name": "Bob", "elo": 1000},
            ],
        )
        # Add commanders
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) "
                "VALUES ('Commander A', '111'), ('Commander B', '222')"
            ),
        )
        # Add games
        conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES ('2024-01-01', 1, 1), ('2024-01-02', 1, 1), ('2024-01-03', 2, 2)"
            ),
        )
        # Add game players with ELO changes
        conn.execute(
            sa.text(
                "INSERT INTO game_players (game_id, player_id, commander_id, elo_change) "
                "VALUES (1, 1, 1, 10), (1, 2, 2, -10), "
                "(2, 1, 1, 5), (2, 2, 2, -5), "
                "(3, 1, 1, -8), (3, 2, 2, 8)"
            ),
        )

    results = get_player_commander_leaderboard(test_db)
    assert len(results) == 2
    assert results[0]["player_name"] == "Alice"
    assert results[0]["commander_name"] == "Commander A"
    assert results[0]["avg_elo_change"] == pytest.approx((10 + 5 - 8) / 3)
    assert results[0]["games_played"] == 3


def test_export_db_to_json(test_db):
    """Test exporting database contents to JSON."""
    # Add some data to export
    with test_db.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Test Player', 1000)")
        )

    json_output = export_db_to_json(test_db)
    data = json.loads(json_output)

    assert data["schema_version"] == SCHEMA_VERSION
    assert "tables" in data
    assert "players" in data["tables"]
    assert len(data["tables"]["players"]) == 1
    assert data["tables"]["players"][0]["name"] == "Test Player"
    assert data["tables"]["players"][0]["elo"] == 1000.0  # Default ELO
    # Check other tables are present but empty
    assert "commanders" in data["tables"] and len(data["tables"]["commanders"]) == 0
    assert "games" in data["tables"] and len(data["tables"]["games"]) == 0
    assert "game_players" in data["tables"] and len(data["tables"]["game_players"]) == 0
