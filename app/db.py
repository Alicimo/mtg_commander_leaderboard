import datetime
import json
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
        sa.Column("last_searched", sa.DateTime),
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
    if isinstance(obj, Row):  # Handle SQLAlchemy Row objects
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


def get_player_leaderboard(engine: Engine) -> list[dict]:
    """Get player leaderboard sorted by ELO."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text("""
                SELECT
                    RANK() OVER (ORDER BY elo DESC) as rank,
                    name,
                    elo
                FROM players
                ORDER BY elo DESC
            """)
        ).fetchall()
        return [dict(r._mapping) for r in results]


def get_game_history(engine: Engine, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
    """Get paginated game history with player and commander info.
    
    Args:
        engine: SQLAlchemy engine
        page: Page number (1-based)
        per_page: Items per page
    
    Returns:
        Tuple of (game_records, total_count)
    """
    offset = (page - 1) * per_page
    
    with engine.connect() as conn:
        # Get total count
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM games")
        ).scalar()
        
        # Get paginated results
        results = conn.execute(
            sa.text("""
                SELECT 
                    g.id,
                    g.date,
                    p_winner.name as winner_name,
                    c_winner.name as winner_commander,
                    GROUP_CONCAT(p_loser.name || ' (' || c_loser.name || ')', ', ') as losers,
                    GROUP_CONCAT(
                        CASE 
                            WHEN gp.player_id = g.winner_id THEN '+' || gp.elo_change 
                            ELSE gp.elo_change 
                        END, 
                        ', '
                    ) as elo_changes,
                    (SELECT gp2.elo_change 
                     FROM game_players gp2 
                     WHERE gp2.game_id = g.id AND gp2.player_id = g.winner_id) as winner_elo_change
                FROM games g
                JOIN players p_winner ON g.winner_id = p_winner.id
                JOIN commanders c_winner ON g.winner_commander_id = c_winner.id
                JOIN game_players gp ON g.id = gp.game_id
                JOIN players p_loser ON gp.player_id = p_loser.id AND gp.player_id != g.winner_id
                JOIN commanders c_loser ON gp.commander_id = c_loser.id
                GROUP BY g.id
                ORDER BY g.date ASC, g.id ASC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": per_page, "offset": offset}
        ).fetchall()
        
        games = []
        for r in results:
            games.append({
                "date": r.date,
                "winner": f"{r.winner_name} ({r.winner_commander})",
                "losers": r.losers,
                "elo_changes": f"+{r.winner_elo_change:.0f} / {r.elo_changes}"
            })
            
        return games, total


def get_player_commander_leaderboard(engine: Engine) -> list[dict]:
    """Get player+commander leaderboard sorted by average ELO."""
    with engine.connect() as conn:
        results = conn.execute(
            sa.text("""
                SELECT
                    p.name as player_name,
                    c.name as commander_name,
                    AVG(gp.elo_change) as avg_elo_change,
                    COUNT(*) as games_played,
                    RANK() OVER (ORDER BY AVG(gp.elo_change) DESC) as rank
                FROM game_players gp
                JOIN players p ON gp.player_id = p.id
                JOIN commanders c ON gp.commander_id = c.id
                GROUP BY p.id, c.id
                HAVING COUNT(*) >= 3  -- Minimum 3 games to appear
                ORDER BY avg_elo_change DESC
            """)
        ).fetchall()
        return [dict(r._mapping) for r in results]


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
