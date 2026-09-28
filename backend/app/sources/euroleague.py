from collections.abc import Iterator
from datetime import UTC, date, datetime
from itertools import groupby
from typing import Any

from app.sources.base import Source, SourceItem, count, parse_datetime, spoken_date
from app.sources.http import Fetcher

API = "https://api-live.euroleague.net"
STANDINGS = (
    "https://feeds.incrowdsports.com/provider/euroleague-feeds/v3/competitions/E/seasons/"
    "{season}/rounds/{round}/basicstandings"
)
Game = dict[str, Any]


def season_code(today: date) -> str:
    return f"E{today.year if today.month >= 7 else today.year - 1}"


class EuroleagueSource(Source):
    """Official EuroLeague data: results with top players, standings and the next round."""

    key = "euroleague-api"
    language = "en"
    official = True

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        season = season_code(datetime.now(UTC).date())
        games_url = f"{API}/v2/competitions/E/seasons/{season}/games"
        games: list[Game] = fetcher.get(games_url).json()["data"]
        played = [game for game in games if game["played"]]
        if played:
            last_round = max(game["round"] for game in played)
            for game in played:
                url = f"{API}/v3/competitions/E/seasons/{season}/games/{game['gameCode']}/stats"
                if game["round"] >= last_round - 1 and url not in known:
                    yield result_item(game, fetcher.get(url).json(), url)
            complete = [
                number
                for number in {game["round"] for game in played}
                if all(game["played"] for game in games if game["round"] == number)
            ]
            if complete:
                number = max(complete)
                url = STANDINGS.format(season=season, round=number)
                round_games = [game for game in games if game["round"] == number]
                if url not in known:
                    yield standings_item(fetcher.get(url).json(), number, round_games, url)
        upcoming = [game for game in games if not game["played"]]
        if upcoming:
            number = min(game["round"] for game in upcoming)
            round_games = [game for game in upcoming if game["round"] == number]
            yield fixtures_item(round_games, f"{games_url}?round={number}")


def team(side: dict[str, Any]) -> str:
    return side["club"]["abbreviatedName"]


def game_day(game: Game) -> date:
    return date.fromisoformat(game["date"][:10])


def player_name(raw: str) -> str:
    surname, _, first = raw.partition(",")
    return f"{first.strip()} {surname.strip()}".title()


def result_item(game: Game, stats: dict[str, Any], url: str) -> SourceItem:
    home_won = game["local"]["score"] > game["road"]["score"]
    winner_side, loser_side = ("local", "road") if home_won else ("road", "local")
    winner, loser = game[winner_side], game[loser_side]

    def quarters(side: str) -> str:
        partials = game[side]["partials"]
        text = ", ".join(str(int(partials[f"partials{quarter}"])) for quarter in range(1, 5))
        extra = [str(int(value)) for value in (partials.get("extraPeriods") or {}).values()]
        return text + (f", plus {', '.join(extra)} in overtime" if extra else "")

    def best_of(side: str) -> str:
        player = max(stats[side]["players"], key=lambda p: p["stats"]["valuation"] or 0)
        numbers = player["stats"]
        return (
            f"{player_name(player['player']['person']['name'])} ({team(game[side])}): "
            f"{count(int(numbers['points'] or 0), 'point')}, "
            f"{count(int(numbers['totalRebounds'] or 0), 'rebound')}, "
            f"{count(int(numbers['assistances'] or 0), 'assist')}, "
            f"PIR {int(numbers['valuation'] or 0)}"
        )

    score = f"{winner['score']}–{loser['score']}"
    body = (
        f"EuroLeague {game['roundAlias']}, {spoken_date(game_day(game))}: {team(winner)} beat "
        f"{team(loser)} {score} {'at home' if home_won else 'away'}, "
        f"winning by {count(winner['score'] - loser['score'], 'point')}. "
        f"Points by quarter: {team(winner)} {quarters(winner_side)}; "
        f"{team(loser)} {quarters(loser_side)}. Best player of each team by valuation (PIR): "
        f"{best_of(winner_side)}; {best_of(loser_side)}."
    )
    return SourceItem(
        url=url,
        title=f"EuroLeague {game['roundAlias']}: {team(winner)} beat {team(loser)} {score}",
        body=body,
        published_at=parse_datetime(game["utcDate"]),
        kind="data",
        meta={
            "competition": "euroleague",
            "type": "result",
            "round": game["round"],
            "teams": [team(winner), team(loser)],
            "date": game_day(game).isoformat(),
        },
    )


def standings_item(
    standings: dict[str, Any], number: int, round_games: list[Game], url: str
) -> SourceItem:
    rows = " ".join(
        f"{row['position']}. {row['club']['abbreviatedName']}, "
        f"{count(row['gamesWon'], 'win')} and {count(row['gamesLost'], 'loss', 'losses')}."
        for row in standings["teams"]
    )
    return SourceItem(
        url=url,
        title=f"EuroLeague standings after Round {number}",
        body=f"Official EuroLeague standings after Round {number}: {rows}",
        published_at=max(parse_datetime(game["utcDate"]) for game in round_games),
        kind="data",
        meta={
            "competition": "euroleague",
            "type": "standings",
            "round": number,
            "teams": [row["club"]["abbreviatedName"] for row in standings["teams"]],
        },
    )


def fixtures_item(round_games: list[Game], url: str) -> SourceItem:
    ordered = sorted(round_games, key=game_day)
    days = [
        f"{spoken_date(day)}: "
        + ", ".join(f"{team(game['local'])} host {team(game['road'])}" for game in day_games)
        + "."
        for day, day_games in groupby(ordered, key=game_day)
    ]
    alias = ordered[0]["roundAlias"]
    return SourceItem(
        url=url,
        title=f"EuroLeague {alias} fixtures",
        body=f"EuroLeague {alias} fixtures (official schedule). " + " ".join(days),
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "euroleague",
            "type": "fixtures",
            "round": ordered[0]["round"],
            "games": [
                {
                    "date": game_day(game).isoformat(),
                    "home": team(game["local"]),
                    "away": team(game["road"]),
                }
                for game in ordered
            ],
        },
    )
