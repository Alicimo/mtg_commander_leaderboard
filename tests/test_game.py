import datetime

import pytest
import sqlalchemy as sa

from app.db import get_engine, init_db
from app.game import submit_game, validate_game_submission


@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Test database fixture"""
    db_path = tmp_path / "test.db"
    if db_path.exists():
        db_path.unlink()
    engine = get_engine(db_path)
    init_db(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES (:name, :elo)"),
            [
                {"name": "Alice", "elo": 1000},
                {"name": "Bob", "elo": 1000},
                {"name": "Charlie", "elo": 1000},
            ],
        )
    yield engine
    engine.dispose()


def test_validate_game_submission():
    """Test game submission validation"""
    # Valid cases
    assert validate_game_submission(["Alice", "Bob"], "Alice") is None
    assert validate_game_submission(["Alice", "Bob", "Charlie"], "Bob") is None

    # Invalid cases
    assert validate_game_submission(["Alice"], "Alice") == "At least 2 players required"
    assert (
        validate_game_submission(["Alice", "Bob"], "Charlie")
        == "Winner must be one of the selected players"
    )


def test_submit_game(test_db):
    """Test game submission to database"""
    # Submit a valid game
    submit_game(test_db, datetime.date.today(), ["Alice", "Bob"], "Alice")

    # Verify data was inserted
    with test_db.connect() as conn:
        # Check games table
        game = conn.execute(sa.text("SELECT date, winner_id FROM games")).fetchone()
        assert game is not None

        # Check game_players table
        players = conn.execute(
            sa.text("SELECT player_id FROM game_players WHERE game_id = 1")
        ).fetchall()
        assert len(players) == 2


def test_submit_game_transaction(test_db):
    """Test that failed submissions don't leave partial data"""
    # This should fail due to invalid winner
    with pytest.raises(Exception):
        submit_game(
            test_db,
            datetime.date.today(),
            ["Alice", "Bob"],
            "Charlie",  # Not in players list
        )

    # Verify no data was inserted
    with test_db.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM games")).scalar()
        assert count == 0
