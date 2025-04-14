import decimal
from decimal import Decimal

import pytest
import sqlalchemy as sa

from app.db import get_engine, init_db
from app.elo import EloResult, calculate_elo, update_elos_in_db, K_FACTOR


def test_calculate_elo_2player():
    """Test standard 2-player ELO calculation."""
    # Equal ratings
    result = calculate_elo(1000, [1000])
    assert result.winner_new_elo == Decimal("1016.00")
    assert result.losers_new_elos == [Decimal("984.00")]
    assert result.winner_delta == Decimal("16.00")
    assert result.losers_deltas == [Decimal("-16.00")]

    # Different ratings
    result = calculate_elo(1200, [1000])
    assert result.winner_new_elo == Decimal("1203.20")
    assert result.losers_new_elos == [Decimal("996.80")]
    assert result.winner_delta == Decimal("3.20")
    assert result.losers_deltas == [Decimal("-3.20")]


def test_calculate_elo_multiplayer():
    """Test multiplayer ELO distribution."""
    # 3 players, equal ratings
    result = calculate_elo(1000, [1000, 1000])
    assert result.winner_new_elo == Decimal("1016.00")  # +16 total
    assert result.losers_new_elos == [Decimal("992.00"), Decimal("992.00")]
    assert result.winner_delta == Decimal("16.00")
    assert result.losers_deltas == [Decimal("-8.00"), Decimal("-8.00")]

    # 4 players, different ratings
    result = calculate_elo(1100, [1000, 1050, 900])
    assert result.winner_new_elo == Decimal("1108.53")
    assert result.losers_new_elos == [
        Decimal("996.49"), 
        Decimal("1041.51"), 
        Decimal("893.47")
    ]
    assert result.winner_delta == Decimal("8.53")
    assert result.losers_deltas == [
        Decimal("-3.51"), 
        Decimal("-8.49"), 
        Decimal("-6.53")
    ]


def test_k_factor_variation():
    """Test different K-factor values."""
    # Higher K-factor = bigger swings
    result = calculate_elo(1000, [1000], k_factor=40)
    assert result.winner_delta == Decimal("20.00")
    assert result.losers_deltas == [Decimal("-20.00")]

    # Lower K-factor = smaller swings
    result = calculate_elo(1000, [1000], k_factor=16)
    assert result.winner_delta == Decimal("8.00")
    assert result.losers_deltas == [Decimal("-8.00")]


@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Test database fixture"""
    db_path = tmp_path / "test.db"
    if db_path.exists():
        db_path.unlink()
    engine = get_engine(db_path)
    init_db(engine)
    with engine.begin() as conn:
        # Add players
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES (:name, :elo)"),
            [
                {"name": "Alice", "elo": 1000},
                {"name": "Bob", "elo": 1000},
                {"name": "Charlie", "elo": 1000},
            ],
        )
        # Add a commander first
        conn.execute(
            sa.text(
                "INSERT INTO commanders (name, scryfall_id) "
                "VALUES ('Test Commander', 'test')"
            )
        )
        # Add a game with valid commander reference
        conn.execute(
            sa.text(
                "INSERT INTO games (date, winner_id, winner_commander_id) "
                "VALUES ('2024-01-01', 1, 1)"
            )
        )
        # Add game players
        conn.execute(
            sa.text(
                "INSERT INTO game_players (game_id, player_id, commander_id, elo_change) "
                "VALUES (1, 1, 1, 0), (1, 2, 1, 0), (1, 3, 1, 0)"
            )
        )
    yield engine
    engine.dispose()


def test_update_elos_in_db(test_db):
    """Test database integration."""
    changes = update_elos_in_db(test_db, game_id=1, winner_id=1, loser_ids=[2, 3])
    
    assert changes == {
        1: 16.0,  # Winner gains 16 total (8 from each loser)
        2: -8.0,  # Each loser loses 8
        3: -8.0,
    }
    
    # Verify database updates
    with test_db.connect() as conn:
        alice = conn.execute(
            sa.text("SELECT elo FROM players WHERE id = 1")
        ).scalar()
        assert alice == 1016.0
        
        bob = conn.execute(
            sa.text("SELECT elo FROM players WHERE id = 2")
        ).scalar()
        assert bob == 992.0
        
        # Verify game_players records updated
        changes = conn.execute(
            sa.text("SELECT player_id, elo_change FROM game_players WHERE game_id = 1")
        ).fetchall()
        assert changes == [(1, 16.0), (2, -8.0), (3, -8.0)]


def test_elo_precision():
    """Test decimal precision handling."""
    # Test with ratings that would expose floating point errors
    result = calculate_elo(1234.56, [987.65, 1056.78])
    assert str(result.winner_new_elo) == "1238.29"
    assert [str(elo) for elo in result.losers_new_elos] == ["983.41", "1052.74"]
