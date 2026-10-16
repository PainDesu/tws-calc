#!/usr/bin/env python3
"""TWS Calc — main entry point for team strength and match outcome tools."""

import argparse
import sys
from pathlib import Path

from match_outcomes import calculate_match_outcomes
from team_strength import update_team_strength

TEAMS_DIR = Path(__file__).resolve().parent / "Teams"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Team strength and match outcome calculator."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser(
        "update",
        help="Update team strength from a team CSV in the Teams folder.",
    )
    update_parser.add_argument(
        "team",
        help="Team name (must match a CSV filename, e.g. CZE for CZE.csv).",
    )

    calculate_parser = subparsers.add_parser(
        "calculate",
        help="Calculate match outcomes between two teams.",
    )
    calculate_parser.add_argument("team_a", help="First team name.")
    calculate_parser.add_argument("team_b", help="Second team name.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not TEAMS_DIR.is_dir():
        print(f"Error: Teams folder not found at {TEAMS_DIR}", file=sys.stderr)
        return 1

    try:
        if args.command == "update":
            update_team_strength(args.team, TEAMS_DIR)
            print(f"Updated team strength for {args.team}")
        elif args.command == "calculate":
            output_path = calculate_match_outcomes(args.team_a, args.team_b, TEAMS_DIR)
            print(f"Wrote match outcomes to {output_path}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotImplementedError as exc:
        print(f"Not implemented: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
