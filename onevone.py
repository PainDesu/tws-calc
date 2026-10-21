
import argparse
import json
import math
import urllib.error
import urllib.parse
import urllib.request


class GlickoMatchCalculator:
    API_BASE = "https://ch.tetr.io/api/users"
    Q = math.log(10) / 400

    @staticmethod
    def _glicko_g(rd: float) -> float:
        """Calculate the Glicko opponent uncertainty adjustment."""
        return 1 / math.sqrt(
            1 + 3 * GlickoMatchCalculator.Q**2 * rd**2 / math.pi**2
        )

    @staticmethod
    def _game_win_probability(
        rating_a: float,
        rating_b: float,
        rd_b: float
    ) -> float:
        """Estimate the probability that Player A wins one game."""
        g = GlickoMatchCalculator._glicko_g(rd_b)
        exponent = -g * (rating_a - rating_b) / 400
        return 1 / (1 + 10**exponent)

    @classmethod
    def _fetch_player(cls, username: str) -> dict:
        """Fetch a player's Glicko rating and RD from the TETR.IO API."""
        username = username.strip()

        if not username:
            raise ValueError("Player username cannot be empty.")

        encoded_username = urllib.parse.quote(username, safe="")
        url = f"{cls.API_BASE}/{encoded_username}/summaries/league"

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "GlickoMatchCalculator/1.0"}
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError(
                    f"Player '{username}' was not found."
                ) from exc

            raise RuntimeError(
                f"TETR.IO API returned HTTP {exc.code} "
                f"for '{username}'."
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not connect to TETR.IO API: {exc.reason}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "TETR.IO returned invalid JSON."
            ) from exc

        if not payload.get("success"):
            raise RuntimeError(
                f"API request failed for '{username}': "
                f"{payload.get('error', 'Unknown API error')}"
            )

        data = payload.get("data") or {}
        rating = data.get("glicko")
        rd = data.get("rd")

        if rating is None or rd is None:
            raise ValueError(
                f"No Glicko rating or RD available for '{username}'."
            )

        rating = float(rating)
        rd = float(rd)

        if rating < 0 or rd < 0:
            raise ValueError(
                f"'{username}' does not have a valid league rating. "
                "They may need to complete at least 10 league games."
            )

        return {
            "username": username,
            "glicko": rating,
            "rd": rd,
        }

    @staticmethod
    def _match_probabilities(p: float, target: int = 7):
        """
        Calculate match-win probabilities, exact scores,
        and expected match length for a first-to-target match.
        """
        q = 1 - p
        a_wins = 0.0
        b_wins = 0.0
        expected_games = 0.0
        scores = []

        # Player A wins target games, while B wins k games.
        for k in range(target):
            probability = (
                math.comb(target + k - 1, k)
                * p**target
                * q**k
            )

            scores.append((f"{target}-{k}", probability))
            a_wins += probability
            expected_games += (target + k) * probability

        # Player B wins target games, while A wins k games.
        for k in range(target):
            probability = (
                math.comb(target + k - 1, k)
                * q**target
                * p**k
            )

            scores.append((f"{k}-{target}", probability))
            b_wins += probability
            expected_games += (target + k) * probability

        return a_wins, b_wins, expected_games, scores

    @classmethod
    def predict_match(
        cls,
        username_a: str,
        username_b: str,
        target: int = 7
    ) -> str:
        """
        Fetch player ratings and return a formatted match prediction.
        """
        if target < 1:
            raise ValueError("Target must be at least 1.")

        player_a = cls._fetch_player(username_a)
        player_b = cls._fetch_player(username_b)

        rating_a = player_a["glicko"]
        rd_a = player_a["rd"]
        rating_b = player_b["glicko"]
        rd_b = player_b["rd"]

        # Estimate single-game probabilities.
        p = cls._game_win_probability(
            rating_a,
            rating_b,
            rd_b
        )
        q = 1 - p

        # Calculate match outcome probabilities.
        a_wins, b_wins, expected_games, scores = (
            cls._match_probabilities(p, target)
        )

        result = [
            f"Match prediction: First to {target} wins",
            "",
            (
                f"{player_a['username']}: "
                f"Glicko {rating_a:.2f}, RD {rd_a:.2f}"
            ),
            (
                f"{player_b['username']}: "
                f"Glicko {rating_b:.2f}, RD {rd_b:.2f}"
            ),
            "",
            (
                f"{player_a['username']} single-game win chance: "
                f"{p:.2%}"
            ),
            (
                f"{player_b['username']} single-game win chance: "
                f"{q:.2%}"
            ),
            "",
            (
                f"{player_a['username']} match win chance: "
                f"{a_wins:.2%}"
            ),
            (
                f"{player_b['username']} match win chance: "
                f"{b_wins:.2%}"
            ),
            f"Expected number of games: {expected_games:.2f}",
            "",
            "Exact final score probabilities:",
        ]

        for score, probability in sorted(
            scores,
            key=lambda item: item[1],
            reverse=True
        ):
            result.append(
                f"  {player_a['username']} {score} "
                f"{player_b['username']}: {probability:.2%}"
            )

        return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Predict a TETR.IO match using Glicko ratings "
            "and rating deviations."
        )
    )

    parser.add_argument(
        "player_a",
        help="First TETR.IO username"
    )
    parser.add_argument(
        "player_b",
        help="Second TETR.IO username"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=7,
        help="Wins required to win the match (default: 7)"
    )

    args = parser.parse_args()

    try:
        result = GlickoMatchCalculator.predict_match(
            args.player_a,
            args.player_b,
            target=args.target
        )
        print(result)

    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
