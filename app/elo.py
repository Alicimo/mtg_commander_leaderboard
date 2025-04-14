import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Dict, List, Tuple

import sqlalchemy as sa
from sqlalchemy.engine import Engine

# Configure decimal precision
getcontext().prec = 4  # Enough for intermediate calculations
K_FACTOR = Decimal(32)  # Standard K-factor for MTG


@dataclass
class EloResult:
    """Container for ELO calculation results."""
    winner_new_elo: Decimal
    losers_new_elos: List[Decimal]
    winner_delta: Decimal
    losers_deltas: List[Decimal]


def calculate_elo(
    winner_elo: float, 
    losers_elos: List[float], 
    k_factor: float = K_FACTOR
) -> EloResult:
    """Calculate ELO changes for a game result.
    
    Args:
        winner_elo: Current ELO of winner
        losers_elos: List of current ELOs for losers
        k_factor: K-factor to use (default 32)
        
    Returns:
        EloResult with new ratings and deltas
    """
    k_factor = Decimal(str(k_factor))
    winner_elo = Decimal(str(winner_elo))
    losers_elos = [Decimal(str(elo)) for elo in losers_elos]
    
    # Calculate expected scores and deltas
    winner_deltas = []
    for loser_elo in losers_elos:
        expected = Decimal(1) / (Decimal(1) + (Decimal(10) ** ((loser_elo - winner_elo) / Decimal(400))))
        winner_deltas.append(k_factor * (Decimal(1) - expected))
    
    # Distribute winner's gains across losers
    total_winner_delta = sum(winner_deltas) / len(losers_elos)
    winner_new_elo = winner_elo + total_winner_delta
    
    # Calculate each loser's loss
    losers_new_elos = []
    losers_deltas = []
    for i, loser_elo in enumerate(losers_elos):
        delta = -winner_deltas[i] / len(losers_elos)
        losers_new_elos.append(loser_elo + delta)
        losers_deltas.append(delta)
    
    # Round to 2 decimal places for final results
    return EloResult(
        winner_new_elo=round(winner_new_elo, 2),
        losers_new_elos=[round(elo, 2) for elo in losers_new_elos],
        winner_delta=round(total_winner_delta, 2),
        losers_deltas=[round(delta, 2) for delta in losers_deltas],
    )


def update_elos_in_db(
    engine: Engine,
    game_id: int,
    winner_id: int,
    loser_ids: List[int],
    k_factor: float = K_FACTOR
) -> Dict[int, float]:
    """Update ELO ratings in database for a game result.
    
    Args:
        engine: SQLAlchemy engine
        game_id: ID of the game record
        winner_id: Player ID of winner
        loser_ids: List of player IDs of losers
        k_factor: K-factor to use (default 32)
        
    Returns:
        Dictionary mapping player IDs to their ELO changes
    """
    with engine.begin() as conn:
        # Get current ELOs
        winner_elo = conn.execute(
            sa.text("SELECT elo FROM players WHERE id = :id"),
            {"id": winner_id},
        ).scalar()
        
        losers_elos = [
            r.elo for r in conn.execute(
                sa.text("SELECT elo FROM players WHERE id IN :ids"),
                {"ids": tuple(loser_ids)},
            ).fetchall()
        ]
        
        # Calculate changes
        result = calculate_elo(winner_elo, losers_elos, k_factor)
        
        # Update players table
        conn.execute(
            sa.text("UPDATE players SET elo = :elo WHERE id = :id"),
            {"id": winner_id, "elo": float(result.winner_new_elo)},
        )
        
        for loser_id, new_elo in zip(loser_ids, result.losers_new_elos):
            conn.execute(
                sa.text("UPDATE players SET elo = :elo WHERE id = :id"),
                {"id": loser_id, "elo": float(new_elo)},
            )
        
        # Record changes in game_players
        conn.execute(
            sa.text(
                "UPDATE game_players SET elo_change = :delta "
                "WHERE game_id = :game_id AND player_id = :player_id"
            ),
            {"game_id": game_id, "player_id": winner_id, "delta": float(result.winner_delta)},
        )
        
        for loser_id, delta in zip(loser_ids, result.losers_deltas):
            conn.execute(
                sa.text(
                    "UPDATE game_players SET elo_change = :delta "
                    "WHERE game_id = :game_id AND player_id = :player_id"
                ),
                {"game_id": game_id, "player_id": loser_id, "delta": float(delta)},
            )
        
        return {
            winner_id: float(result.winner_delta),
            **{loser_id: float(delta) for loser_id, delta in zip(loser_ids, result.losers_deltas)}
        }
