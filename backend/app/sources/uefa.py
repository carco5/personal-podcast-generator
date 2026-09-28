from collections.abc import Iterator
from datetime import UTC, date, datetime
from itertools import groupby
from typing import Any

from app.sources.base import (
    Goal,
    Source,
    SourceItem,
    count,
    gap_to_leader,
    goals_sentence,
    parse_datetime,
    spoken_date,
)
from app.sources.http import Fetcher

MATCHES = "https://match.uefa.com/v5/matches"
STANDINGS = "https://standings.uefa.com/v1/standings"
SITE = "https://www.uefa.com/uefachampionsleague"
CHAMPIONS_LEAGUE = 1
FINISHED = "FINISHED"

Match = dict[str, Any]


def season_year(today: date) -> int:
    return today.year + 1 if today.month >= 7 else today.year


class UefaChampionsSource(Source):
    """Official Champions League data from UEFA: results, standings and the next matchday."""

    key = "uefa-data"
    language = "en"
    official = True

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        year = season_year(datetime.now(UTC).date())
        params: dict[str, str | int] = {
            "competitionId": CHAMPIONS_LEAGUE,
            "seasonYear": year,
            "phase": "TOURNAMENT",
            "offset": 0,
            "limit": 500,
            "order": "ASC",
        }
        matches: list[Match] = fetcher.get(MATCHES, params=params).json()
        played = [matchday(m) for m in matches if m["status"] == FINISHED]
        for match in matches:
            url = f"{SITE}/match/{match['id']}/"
            recent = played and matchday(match) >= max(played) - 1
            if match["status"] == FINISHED and recent and url not in known:
                yield result_item(match, url)
        standings = fetcher.get(
            STANDINGS, params={"competitionId": CHAMPIONS_LEAGUE, "seasonYear": year}
        )
        yield standings_item(standings.json()[0]["items"])
        upcoming = [m for m in matches if m["status"] != FINISHED]
        if upcoming:
            number = min(matchday(m) for m in upcoming)
            yield fixtures_item([m for m in upcoming if matchday(m) == number], number)


def matchday(match: Match) -> int:
    return int("".join(ch for ch in match["matchday"]["name"] if ch.isdigit()) or 0)


def team(side: dict[str, Any]) -> str:
    return side["internationalName"]


def match_day(match: Match) -> date:
    return date.fromisoformat(match["kickOffTime"]["date"])


def result_item(match: Match, url: str) -> SourceItem:
    home, away = team(match["homeTeam"]), team(match["awayTeam"])
    goals = match["score"]["total"]
    home_goals, away_goals = goals["home"], goals["away"]
    if home_goals == away_goals:
        text, order = f"{home} and {away} drew {home_goals}–{away_goals}", [home, away]
    elif home_goals > away_goals:
        text, order = f"{home} beat {away} {home_goals}–{away_goals} at home", [home, away]
    else:
        text, order = f"{away} beat {home} {away_goals}–{home_goals} away", [away, home]
    number = matchday(match)
    details = " ".join(
        part for part in (goals_sentence(scorers(match), order), star(match)) if part
    )
    return SourceItem(
        url=url,
        title=f"Champions League Matchday {number}: {text}",
        body=f"UEFA Champions League, league phase Matchday {number}, "
        f"{spoken_date(match_day(match))}: {text}. {details}".strip(),
        published_at=parse_datetime(match["kickOffTime"]["dateTime"]),
        kind="data",
        meta={
            "competition": "champions-league",
            "type": "result",
            "round": number,
            "teams": [home, away],
            "date": match_day(match).isoformat(),
        },
    )


def scorers(match: Match) -> list[Goal]:
    names = {
        str(match["homeTeam"]["id"]): team(match["homeTeam"]),
        str(match["awayTeam"]["id"]): team(match["awayTeam"]),
    }
    return [
        Goal(
            team=names.get(str(event.get("teamId")), ""),
            player=event["player"]["internationalName"],
            minute=event["time"]["minute"],
            penalty=event.get("goalType") == "PENALTY",
            own_goal=event.get("goalType") == "OWN",
        )
        for event in match.get("playerEvents", {}).get("scorers", [])
    ]


def star(match: Match) -> str:
    best = match.get("playerOfTheMatch")
    if not best:
        return ""
    names = {str(match[side]["id"]): team(match[side]) for side in ("homeTeam", "awayTeam")}
    club = names.get(str(best.get("teamId")))
    suffix = f" ({club})" if club else ""
    return f"Player of the match: {best['player']['internationalName']}{suffix}."


def standings_item(rows: list[dict[str, Any]]) -> SourceItem:
    played = {row["played"] for row in rows}
    today = datetime.now(UTC).date()
    when = f"after Matchday {played.pop()}" if len(played) == 1 else f"on {spoken_date(today)}"
    leader = max(row["points"] for row in rows)
    table = " ".join(
        f"{row['rank']}. {team(row['team'])}, {count(row['points'], 'point')} from "
        f"{count(row['played'], 'game')} ({count(row['won'], 'win')}, "
        f"{count(row['drawn'], 'draw')}, {count(row['lost'], 'loss', 'losses')})"
        f"{gap_to_leader(row['points'], leader, first=row is rows[0])}."
        for row in rows
    )
    return SourceItem(
        url=f"{SITE}/standings/#played-{sum(row['played'] for row in rows)}",
        title=f"Champions League standings {when}",
        body=f"Official UEFA Champions League league phase standings {when}: {table}",
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "champions-league",
            "type": "standings",
            "teams": [team(row["team"]) for row in rows],
        },
    )


def fixtures_item(matches: list[Match], number: int) -> SourceItem:
    ordered = sorted(matches, key=match_day)
    days = [
        f"{spoken_date(day)}: "
        + ", ".join(f"{team(m['homeTeam'])} host {team(m['awayTeam'])}" for m in day_matches)
        + "."
        for day, day_matches in groupby(ordered, key=match_day)
    ]
    return SourceItem(
        url=f"{SITE}/fixtures-results/#matchday-{number}",
        title=f"Champions League Matchday {number} fixtures",
        body=f"UEFA Champions League Matchday {number} fixtures (official schedule). "
        + " ".join(days),
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "champions-league",
            "type": "fixtures",
            "round": number,
            "games": [
                {
                    "date": match_day(m).isoformat(),
                    "home": team(m["homeTeam"]),
                    "away": team(m["awayTeam"]),
                }
                for m in ordered
            ],
        },
    )
