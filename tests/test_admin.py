import json
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa

from app.admin import show_admin_page
from app.db import (
    SCHEMA_VERSION,
    backup_sqlite_db,
    check_connection,
    export_db_to_json,
    get_engine,
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

    # Add some initial data for export tests
    with engine.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES (:name, :elo)"),
            [
                {"name": "Alice", "elo": 1050.0},
                {"name": "Bob", "elo": 950.0},
            ],
        )
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) VALUES (:name, :scryfall_id)"
            ),
            [
                {"name": "Commander A", "scryfall_id": "scryfall_a"},
                {"name": "Commander B", "scryfall_id": "scryfall_b"},
            ],
        )
        conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) VALUES (:date, :wid, :wcid)"
            ),
            [
                {
                    "date": date(2024, 1, 1),
                    "wid": 1, # Alice
                    "wcid": 1, # Commander A
                }
            ],
        )
        conn.execute(
            sa.text(
                "INSERT INTO game_players (game_id, player_id, commander_id, elo_change) VALUES (:gid, :pid, :cid, :elo)"
            ),
            [
                {"gid": 1, "pid": 1, "cid": 1, "elo": 10.0}, # Alice won
                {"gid": 1, "pid": 2, "cid": 2, "elo": -10.0}, # Bob lost
            ],
        )

    yield engine # Provide the engine to the test

    # Cleanup after test
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_DATA_DIR.exists() and not any(TEST_DATA_DIR.iterdir()):
         TEST_DATA_DIR.rmdir() # Remove dir only if empty


def test_add_player(test_db):
    """Test adding a new player."""
    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="Test Player"):
            with patch("streamlit.success") as mock_success:
                show_admin_page(test_db)
                mock_success.assert_called_once_with("Added player: Test Player")
    
    # Verify player was added
    with test_db.connect() as conn:
        result = conn.execute(
            sa.text("SELECT name FROM players WHERE name = 'Test Player'")
        ).scalar()
        assert result == "Test Player"


def test_duplicate_player(test_db):
    """Test duplicate player prevention."""
    # Add initial player
    with test_db.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Test Player', 1000)")
        )

    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="Test Player"):
            with patch("streamlit.error") as mock_error:
                show_admin_page(test_db)
                mock_error.assert_called_once_with("Player 'Test Player' already exists")


def test_delete_player(test_db):
    """Test player deletion."""
    # Add test player
    with test_db.begin() as conn:
        result = conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Test Player', 1000)")
        )
        player_id = result.lastrowid
    
    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.selectbox", return_value=f"Test Player (ID: {player_id})"):
            with patch("streamlit.checkbox", return_value=True):
                with patch("streamlit.success") as mock_success:
                    show_admin_page(test_db)
                    mock_success.assert_called_once_with("Deleted player: Test Player (ID: 1)")

    # Verify player was deleted
    with test_db.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM players")).scalar()
        assert result == 0


# --- Export Tests ---

# Patch DB_PATH for export functions during testing
@patch("app.db.DB_PATH", TEST_DB_PATH)
@patch("app.admin.DB_PATH", TEST_DB_PATH)
def test_export_sqlite(test_db):
    """Test SQLite database backup function."""
    backup_dir = TEST_DATA_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    try:
        backup_path = backup_sqlite_db(target_dir=backup_dir)
        assert backup_path.exists()
        assert backup_path.parent == backup_dir
        assert backup_path.name.startswith("commander_backup_")
        assert backup_path.name.endswith(".db")
        assert backup_path.stat().st_size > 0 # Check file is not empty

        # Simple check: try to connect to the backup
        backup_engine = get_engine(db_path=backup_path)
        assert check_connection(backup_engine)
        backup_engine.dispose()

    finally:
        # Clean up backup file and directory
        if 'backup_path' in locals() and backup_path.exists():
            backup_path.unlink()
        if backup_dir.exists():
            shutil.rmtree(backup_dir)


def test_export_json(test_db):
    """Test exporting database contents to JSON."""
    json_output = export_db_to_json(test_db)
    data = json.loads(json_output)

    assert data["schema_version"] == SCHEMA_VERSION
    assert "tables" in data
    assert "players" in data["tables"]
    assert "commanders" in data["tables"]
    assert "games" in data["tables"]
    assert "game_players" in data["tables"]

    # Check players table data
    assert len(data["tables"]["players"]) == 2
    assert data["tables"]["players"][0]["name"] == "Alice"
    assert data["tables"]["players"][0]["elo"] == 1050.0

    # Check games table data (and date format)
    assert len(data["tables"]["games"]) == 1
    assert data["tables"]["games"][0]["date"] == "2024-01-01"
    assert data["tables"]["games"][0]["winner_id"] == 1 # Alice

    # Check game_players data
    assert len(data["tables"]["game_players"]) == 2
    assert data["tables"]["game_players"][0]["player_id"] == 1 # Alice
    assert data["tables"]["game_players"][0]["elo_change"] == 10.0


# Mock streamlit functions for UI tests if needed later
# Example:
# @patch("streamlit.button")
# @patch("streamlit.download_button")
# def test_admin_export_ui(mock_download, mock_button, test_db):
#     # Simulate button clicks and check if download_button is called
#     pass
