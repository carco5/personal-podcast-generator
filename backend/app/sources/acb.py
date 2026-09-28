import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from itertools import groupby
from typing import Any
from zoneinfo import ZoneInfo

from app.sources.base import Source, SourceItem, parse_datetime, spoken_date
from app.sources.http import Fetcher

CALENDAR = "https://www.acb.com/es/calendario"
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
MADRID = ZoneInfo("Europe/Madrid")
FINISHED = "FINALIZED"

Match = dict[str, Any]


def calendar_data(html: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flight = "".join(json.loads(f'"{chunk}"') for chunk in FLIGHT_CHUNK.findall(html))
    rounds_at = flight.find('"rounds":[')
    teams_at = flight.rfind('"teams":[', 0, rounds_at)
    if rounds_at < 0 or teams_at < 0:
        raise ValueError("acb.com calendar without teams and rounds")
    decoder = json.JSONDecoder()
    teams, _ = decoder.raw_decode(flight, teams_at + len('"teams":'))
    rounds, _ = decoder.raw_decode(flight, rounds_at + len('"rounds":'))
    return teams, rounds


class AcbCalendarSource(Source):
    """Official Liga ACB results and next-round fixtures, read from acb.com's calendar page."""

    key = "acb-calendar"
    language = "en"
    official = True

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        teams, rounds = calendar_data(fetcher.get(CALENDAR).text)

        def name(reference: str) -> str:
            return teams[int(reference.rsplit(":", 1)[1])]["fullName"]

        played = [
            number["roundNumber"]
            for number in rounds
            if any(match["matchStatus"] == FINISHED for match in number["matches"])
        ]
        for number in rounds:
            if played and number["roundNumber"] >= max(played) - 1:
                for match in number["matches"]:
                    url = f"{CALENDAR}#match-{match['id']}"
                    if match["matchStatus"] == FINISHED and url not in known:
                        yield result_item(match, number["roundNumber"], name, url)
        upcoming = [
            number
            for number in rounds
            if any(match["matchStatus"] != FINISHED for match in number["matches"])
        ]
        if upcoming:
            number = upcoming[0]
            pending = [m for m in number["matches"] if m["matchStatus"] != FINISHED]
            yield fixtures_item(pending, number["roundNumber"], name)


def match_day(match: Match) -> date:
    return parse_datetime(match["startDateTime"]).astimezone(MADRID).date()


def result_item(match: Match, number: int, name: Callable[[str], str], url: str) -> SourceItem:
    home, away = name(match["homeTeam"]), name(match["awayTeam"])
    home_points, away_points = match["homeTeamScore"], match["awayTeamScore"]
    if home_points > away_points:
        text = f"{home} beat {away} {home_points}–{away_points} at home"
    else:
        text = f"{away} beat {home} {away_points}–{home_points} away"
    return SourceItem(
        url=url,
        title=f"Liga ACB Round {number}: {text}",
        body=f"Liga ACB (Liga Endesa), Round {number}, {spoken_date(match_day(match))}: {text}.",
        published_at=parse_datetime(match["startDateTime"]),
        kind="data",
        meta={
            "competition": "liga-acb",
            "type": "result",
            "round": number,
            "teams": [home, away],
            "date": match_day(match).isoformat(),
        },
    )


def fixtures_item(matches: list[Match], number: int, name: Callable[[str], str]) -> SourceItem:
    ordered = sorted(matches, key=match_day)
    days = [
        f"{spoken_date(day)}: "
        + ", ".join(f"{name(m['homeTeam'])} host {name(m['awayTeam'])}" for m in day_matches)
        + "."
        for day, day_matches in groupby(ordered, key=match_day)
    ]
    return SourceItem(
        url=f"{CALENDAR}#round-{number}",
        title=f"Liga ACB Round {number} fixtures",
        body=f"Liga ACB (Liga Endesa) Round {number} fixtures (official schedule). "
        + " ".join(days),
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "liga-acb",
            "type": "fixtures",
            "round": number,
            "games": [
                {
                    "date": match_day(m).isoformat(),
                    "home": name(m["homeTeam"]),
                    "away": name(m["awayTeam"]),
                }
                for m in ordered
            ],
        },
    )
