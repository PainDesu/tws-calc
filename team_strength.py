"""Team strength calculation (update)."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://ch.tetr.io/api"
REQUEST_DELAY_SECONDS = 1.0
USER_AGENT = "tws-calc/0.1 (Tetra League team strength updater)"
FIELDNAMES = ("ID", "NAME", "GLICKO", "RD")


def update_team_strength(team_name: str, teams_dir: Path) -> None:
    """Fetch current Glicko and RD for each player and write them back to the CSV.

    Args:
        team_name: Team identifier (matches CSV filename without extension).
        teams_dir: Path to the Teams folder containing CSV files.
    """
    csv_path = teams_dir / f"{team_name}.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Team file not found: {csv_path}")

    rows = _read_team_csv(csv_path)
    for index, row in enumerate(rows):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)

        username = row.get("NAME", "").strip()
        if not username:
            print(f"Skipping row {row.get('ID', '?')}: missing NAME")
            continue

        try:
            glicko, rd = fetch_league_glicko_rd(username)
        except LookupError as exc:
            print(f"Warning: {exc}")
            continue

        row["GLICKO"] = _format_rating(glicko)
        row["RD"] = _format_rating(rd)
        print(f"{username}: glicko={row['GLICKO']} rd={row['RD']}")

    _write_team_csv(csv_path, rows)


def fetch_league_glicko_rd(username: str) -> tuple[float, float]:
    """Return current Tetra League Glicko and RD for a TETR.IO username."""
    payload = _get_json(f"/users/{urllib.parse.quote(username.lower())}/summaries/league")
    if not payload.get("success"):
        error = payload.get("error") or payload
        raise LookupError(f"API error for {username}: {error}")

    data = payload.get("data") or {}
    glicko = data.get("glicko")
    rd = data.get("rd")
    if glicko is None or rd is None:
        raise LookupError(
            f"No Glicko/RD for {username} (played {data.get('gamesplayed', 0)} league games)"
        )
    return float(glicko), float(rd)


def _get_json(path: str) -> dict:
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError as json_exc:
            raise LookupError(f"HTTP {exc.code} for {path}: {body}") from json_exc


def _read_team_csv(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_team_csv(csv_path: Path, rows: list[dict[str, str]]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDNAMES), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _format_rating(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")
