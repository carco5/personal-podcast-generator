import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from itertools import groupby
from typing import Any
from zoneinfo import ZoneInfo

import httpx

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
from app.sources.http import Fetcher, RobotsDisallowed

log = logging.getLogger(__name__)

BASE = "https://www.laliga.com/en-GB/laliga-easports"
MATCH_PAGE = "https://www.laliga.com/en-GB/match/{slug}"
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
MADRID = ZoneInfo("Europe/Madrid")
FINISHED = "FullTime"

Match = dict[str, Any]


def page_data(html: str) -> dict[str, Any]:
    found = NEXT_DATA.search(html)
    if found is None:
        raise ValueError("laliga.com page without __NEXT_DATA__")
    return json.loads(found.group(1))["props"]["pageProps"]


class LaLigaSource(Source):
    """Official LaLiga data read from laliga.com: results, standings and the next matchday."""

    key = "laliga-data"
    language = "en"
    official = True

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        standing = page_data(fetcher.get(f"{BASE}/standing").text)
        season = int(standing["season"])
        slug = f"{season}-{(season + 1) % 100:02d}"
        current = standing["currentGameweek"]["week"]
        pending: list[tuple[int, Match]] = []
        started = False
        for week in (current - 1, current):
            if week < 1:
                continue
            url = f"{BASE}/results/{slug}/gameweek-{week}"
            for match in page_data(fetcher.get(url).text)["matches"]:
                match_url = f"{url}#match-{match['id']}"
                started = started or (week == current and match["status"] == FINISHED)
                if match["status"] != FINISHED:
                    pending.append((week, match))
                elif match_url not in known:
                    yield result_item(match, week, match_url, match_goals(fetcher, match))
        yield standings_item(standing["standings"], None if started else current - 1)
        if pending:
            week = min(number for number, _ in pending)
            upcoming = [match for number, match in pending if number == week]
            yield fixtures_item(upcoming, week, f"{BASE}/results/{slug}/gameweek-{week}")


def team(side: dict[str, Any]) -> str:
    return side["nickname"]


def match_day(match: Match) -> date:
    return parse_datetime(match["date"]).astimezone(MADRID).date()


def match_goals(fetcher: Fetcher, match: Match) -> list[Goal]:
    try:
        events = page_data(fetcher.get(MATCH_PAGE.format(slug=match["slug"])).text)["events"]
    except (httpx.HTTPError, RobotsDisallowed, ValueError, KeyError) as error:
        log.warning("laliga-data: no goals for %s (%s)", match.get("slug"), error)
        return []
    names = {side["id"]: team(side) for side in (match["home_team"], match["away_team"])}
    goals = []

    def player(person: dict[str, Any]) -> str:
        nickname = person.get("nickname") or ""
        return (person.get("name") or nickname) if "." in nickname else nickname

    for event in events:
        kind = event["match_event_kind"]["name"]
        if event["match_event_kind"].get("collection") != "goal":
            continue
        assist = player((event.get("assist") or {}).get("person") or {})
        goals.append(
            Goal(
                team=names.get(event["lineup"]["team"]["id"], ""),
                player=player(event["lineup"]["person"]),
                minute=event["time"],
                penalty="Penalty" in kind,
                assist=assist,
                own_goal=kind.startswith("Own"),
            )
        )
    return goals


def result_item(match: Match, week: int, url: str, goals: list[Goal]) -> SourceItem:
    home, away = match["home_team"], match["away_team"]
    home_goals, away_goals = match["home_score"], match["away_score"]
    if home_goals == away_goals:
        text = f"{team(home)} and {team(away)} drew {home_goals}–{away_goals}"
        order = [team(home), team(away)]
    elif home_goals > away_goals:
        text = f"{team(home)} beat {team(away)} {home_goals}–{away_goals} at home"
        order = [team(home), team(away)]
    else:
        text = f"{team(away)} beat {team(home)} {away_goals}–{home_goals} away"
        order = [team(away), team(home)]
    scorers = goals_sentence(goals, order)
    return SourceItem(
        url=url,
        title=f"LaLiga Matchday {week}: {text}",
        body=f"LaLiga EA Sports, Matchday {week}, {spoken_date(match_day(match))}: {text}. "
        f"{scorers}".strip(),
        published_at=parse_datetime(match["date"]),
        kind="data",
        meta={
            "competition": "laliga",
            "type": "result",
            "round": week,
            "teams": [team(home), team(away)],
            "date": match_day(match).isoformat(),
        },
    )


def standings_item(rows: list[dict[str, Any]], after_week: int | None) -> SourceItem:
    today = datetime.now(MADRID).date()
    when = f"after Matchday {after_week}" if after_week else f"on {spoken_date(today)}"
    leader = max(row["points"] for row in rows)
    table = " ".join(
        f"{row['position']}. {team(row['team'])}, {count(row['points'], 'point')} from "
        f"{count(row['played'], 'game')} ({count(row['won'], 'win')}, "
        f"{count(row['drawn'], 'draw')}, {count(row['lost'], 'loss', 'losses')})"
        f"{gap_to_leader(row['points'], leader, first=row is rows[0])}."
        for row in rows
    )
    return SourceItem(
        url=f"{BASE}/standing#played-{sum(row['played'] for row in rows)}",
        title=f"LaLiga standings {when}",
        body=f"Official LaLiga EA Sports standings {when}: {table}",
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "laliga",
            "type": "standings",
            "teams": [team(row["team"]) for row in rows],
        },
    )


def fixtures_item(matches: list[Match], week: int, url: str) -> SourceItem:
    ordered = sorted(matches, key=match_day)
    days = [
        f"{spoken_date(day)}: "
        + ", ".join(f"{team(m['home_team'])} host {team(m['away_team'])}" for m in day_matches)
        + "."
        for day, day_matches in groupby(ordered, key=match_day)
    ]
    return SourceItem(
        url=url,
        title=f"LaLiga Matchday {week} fixtures",
        body=f"LaLiga EA Sports Matchday {week} fixtures (official schedule). " + " ".join(days),
        published_at=datetime.now(UTC),
        kind="data",
        meta={
            "competition": "laliga",
            "type": "fixtures",
            "round": week,
            "games": [
                {
                    "date": match_day(m).isoformat(),
                    "home": team(m["home_team"]),
                    "away": team(m["away_team"]),
                }
                for m in ordered
            ],
        },
    )
