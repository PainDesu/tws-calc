"""Match outcome calculation (calculate)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

WINS_NEEDED = 7
GLICKO_SCALE = 173.7178  # 400 / ln(10)
RATING_FIELDS = ("GLICKO", "RD")


def calculate_match_outcomes(
    team_a: str, team_b: str, teams_dir: Path
) -> Path:
    """Calculate every 1v1 first-to-7 outcome and write Results/team1_vs_team2.csv.

    Args:
        team_a: First team identifier (rows).
        team_b: Second team identifier (columns).
        teams_dir: Path to the Teams folder containing CSV files.

    Returns:
        Path to the written results CSV.
    """
    players_a = _load_team_players(teams_dir / f"{team_a}.csv", team_a)
    players_b = _load_team_players(teams_dir / f"{team_b}.csv", team_b)

    results_dir = teams_dir.parent / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / f"{team_a}_vs_{team_b}.csv"

    header = [""] + [player["name"] for player in players_b]
    rows = [header]
    for player_a in players_a:
        row = [player_a["name"]]
        for player_b in players_b:
            p_game = game_win_probability(
                player_a["glicko"],
                player_a["rd"],
                player_b["glicko"],
                player_b["rd"],
            )
            row.append(most_probable_first_to_n(p_game, WINS_NEEDED))
        rows.append(row)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)

    return output_path


def game_win_probability(
    glicko_a: float, rd_a: float, glicko_b: float, rd_b: float
) -> float:
    """Glicko-2 expected score of player A in a single game against player B."""
    mu_a = (glicko_a - 1500.0) / GLICKO_SCALE
    mu_b = (glicko_b - 1500.0) / GLICKO_SCALE
    phi = math.sqrt((rd_a / GLICKO_SCALE) ** 2 + (rd_b / GLICKO_SCALE) ** 2)
    expected = 1.0 / (1.0 + math.exp(-_g(phi) * (mu_a - mu_b)))
    return min(1.0 - 1e-15, max(1e-15, expected))


def most_probable_first_to_n(p_win: float, wins_needed: int = WINS_NEEDED) -> str:
    """Return the mode of a first-to-N series with no draws, as 'W-L' for the row player."""
    p_loss = 1.0 - p_win
    best_score = (wins_needed, 0)
    best_probability = -1.0

    for losses in range(wins_needed):
        ways = math.comb(wins_needed - 1 + losses, losses)
        win_prob = ways * (p_win**wins_needed) * (p_loss**losses)
        lose_prob = ways * (p_loss**wins_needed) * (p_win**losses)

        if win_prob > best_probability:
            best_probability = win_prob
            best_score = (wins_needed, losses)
        if lose_prob > best_probability:
            best_probability = lose_prob
            best_score = (losses, wins_needed)

    return f"{best_score[0]}-{best_score[1]}"


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _load_team_players(csv_path: Path, team_name: str) -> list[dict[str, float | str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Team file not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    players: list[dict[str, float | str]] = []
    missing: list[str] = []
    for row in rows:
        name = (row.get("NAME") or "").strip()
        if not name:
            continue
        try:
            glicko = float(row.get("GLICKO") or "")
            rd = float(row.get("RD") or "")
        except ValueError:
            missing.append(name)
            continue
        if glicko < 0 or rd < 0:
            missing.append(name)
            continue
        players.append({"name": name, "glicko": glicko, "rd": rd})

    if missing:
        raise ValueError(
            f"{team_name} is missing Glicko/RD for: {', '.join(missing)}. "
            f"Run: python tws-calc.py update {team_name}"
        )
    if not players:
        raise ValueError(f"{team_name} has no players in {csv_path}")
    return players
