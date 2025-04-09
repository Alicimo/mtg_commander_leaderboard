import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.engine import Engine, Row

# Define base path and ensure data directory exists
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "commander.db"
SCHEMA_VERSION = 1


def get_engine(db_path: Path = DB_PATH) -> Engine:
    """Create and return SQLAlchemy engine."""
    db_url = f"sqlite:///{db_path}"
    return sa.create_engine(db_url)


def init_db(engine: Optional[Engine] = None) -> Engine:
    """Initialize database with schema if not exists."""
    if engine is None:
        engine = get_engine()

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
        sa.Column(
            "winner_commander_id",
            sa.Integer,
            sa.ForeignKey("commanders.id"),
            nullable=False,
        ),
    )

    sa.Table(
        "game_players",
        metadata,
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), primary_key=True),
        sa.Column(
            "player_id", sa.Integer, sa.ForeignKey("players.id"), primary_key=True
        ),
        sa.Column(
            "commander_id", sa.Integer, sa.ForeignKey("commanders.id"), nullable=False
        ),
        sa.Column("elo_change", sa.Float, nullable=False),
    )

    # Create all tables with foreign key constraints
    with engine.begin() as conn:
        metadata.create_all(conn)
        # Enable foreign key constraints for SQLite
        conn.execute(sa.text("PRAGMA foreign_keys = ON"))

    return engine


def check_connection(engine: Engine) -> bool:
    """Test database connection by querying SQLite version."""
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT sqlite_version()"))
        return True
    except Exception as e:
        print(f"Connection check failed: {e}")
        return False


# --- Data Export Functions ---

def _json_serializer(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, Row): # Handle SQLAlchemy Row objects
        return dict(obj._mapping)
    raise TypeError(f"Type {type(obj)} not serializable")


def export_db_to_json(engine: Engine) -> str:
    """Export all database tables to a JSON string."""
    metadata = sa.MetaData()
    metadata.reflect(bind=engine)
    all_data: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "tables": {}}

    with engine.connect() as connection:
        for table_name, table in metadata.tables.items():
            select_query = sa.select(table)
            result = connection.execute(select_query).fetchall()
            # Convert list of Row objects to list of dicts
            all_data["tables"][table_name] = [row._asdict() for row in result]

    return json.dumps(all_data, indent=2, default=_json_serializer)


def backup_sqlite_db(target_dir: Path = DATA_DIR) -> Path:
    """Copy the SQLite database file to a timestamped backup file."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"commander_backup_{timestamp}.db"
    backup_path = target_dir / backup_filename

    try:
        shutil.copyfile(DB_PATH, backup_path)
        return backup_path
    except OSError as e:
        raise OSError(f"Failed to create SQLite backup: {e}") from e
