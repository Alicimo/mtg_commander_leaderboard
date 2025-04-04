import pytest
import sqlalchemy as sa
from app.db import init_db, get_engine, test_connection

@pytest.fixture
def test_db():
    """Fixture to initialize test database."""
    engine = get_engine()
    init_db(engine)
    yield engine
    # Cleanup - remove test database
    engine.dispose()
    import os
    if os.path.exists("data/commander.db"):
        os.remove("data/commander.db")

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
    players_cols = {c["name"]: c["type"] for c in inspector.get_columns("players")}
    assert players_cols == {
        "id": "INTEGER",
        "name": "VARCHAR(100)",
        "elo": "FLOAT"
    }
    
    # Test commanders table
    commanders_cols = {c["name"]: c["type"] for c in inspector.get_columns("commanders")}
    assert commanders_cols == {
        "id": "INTEGER",
        "name": "VARCHAR(200)",
        "scryfall_id": "VARCHAR(50)"
    }

def test_connection_working(test_db):
    """Test connection check works."""
    assert test_connection(test_db)
