import os
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from typing import Optional

DB_PATH = "data/commander.db"
SCHEMA_VERSION = 1

def get_engine() -> Engine:
    """Create and return SQLAlchemy engine."""
    db_url = f"sqlite:///{DB_PATH}"
    return sa.create_engine(db_url)

def init_db(engine: Optional[Engine] = None) -> Engine:
    """Initialize database with schema if not exists."""
    if engine is None:
        engine = get_engine()
    
    # Create data directory if needed
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    metadata = sa.MetaData()

    # Define tables matching spec
    sa.Table(
        "players",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("elo", sa.Float, default=1000.0, nullable=False),
    )

    sa.Table(
        "commanders",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("scryfall_id", sa.String(50), unique=True, nullable=False),
    )

    sa.Table(
        "games",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("winner_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False),
        sa.Column("winner_commander_id", sa.Integer, sa.ForeignKey("commanders.id"), nullable=False),
    )

    sa.Table(
        "game_players",
        metadata,
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), primary_key=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), primary_key=True),
        sa.Column("commander_id", sa.Integer, sa.ForeignKey("commanders.id"), nullable=False),
        sa.Column("elo_change", sa.Float, nullable=False),
    )

    # Create all tables
    metadata.create_all(engine)
    
    return engine

def test_connection(engine: Engine) -> bool:
    """Test database connection by querying SQLite version."""
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT sqlite_version()"))
        return True
    except Exception:
        return False
