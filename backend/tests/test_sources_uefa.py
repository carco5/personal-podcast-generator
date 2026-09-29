from datetime import UTC, date, datetime

from app.pipeline.selection import belongs_to_team
from app.sources.registry import TOPIC_FEEDS
from app.sources.uefa import MATCHES, SITE, STANDINGS, UefaChampionsSource, season_year, team
from tests.web import FakeWeb


def match(number: int, md: int, day: str, home: str, away: str, score: tuple | None) -> dict:
    return {
        "id": str(number),
        "matchday": {"name": f"MD{md}"},
        "status": "FINISHED" if score else "UPCOMING",
        "kickOffTime": {"date": day, "dateTime": f"{day}T19:00:00Z"},
        "homeTeam": {"internationalName": home, "id": home},
        "awayTeam": {"internationalName": away, "id": away},
        "score": {"total": {"home": score[0], "away": score[1]}} if score else None,
    }


def scorer(player: str, club: str, minute: int, kind: str = "SCORED") -> dict:
    return {
        "player": {"internationalName": player},
        "teamId": club,
        "time": {"minute": minute},
        "goalType": kind,
    }


def barca_feyenoord() -> dict:
    game = match(1, 1, "2026-09-09", "Barcelona", "Feyenoord", (5, 1))
    game["playerEvents"] = {
        "scorers": [
            scorer("Raphinha", "Barcelona", 3),
            scorer("Sem Steijn", "Feyenoord", 82),
            scorer("Raphinha", "Barcelona", 57),
            scorer("Lamine Yamal", "Barcelona", 77, "PENALTY"),
            scorer("Karim Adeyemi", "Barcelona", 22),
            scorer("Gernot Trauner", "Feyenoord", 85, "OWN"),
        ]
    }
    game["playerOfTheMatch"] = {"player": {"internationalName": "Raphinha"}, "teamId": "Barcelona"}
    return game


def row(rank: int, name: str, won: int, drawn: int, lost: int) -> dict:
    return {
        "rank": rank,
        "team": {"internationalName": name},
        "points": 3 * won + drawn,
        "played": won + drawn + lost,
        "won": won,
        "drawn": drawn,
        "lost": lost,
    }


def fake_uefa() -> FakeWeb:
    return FakeWeb(
        {
            MATCHES: [
                barca_feyenoord(),
                match(2, 1, "2026-09-10", "Inter", "Arsenal", (1, 1)),
                match(3, 2, "2026-10-13", "Galatasaray", "Barcelona", None),
            ],
            STANDINGS: [{"items": [row(1, "Barcelona", 1, 0, 0), row(2, "Inter", 0, 1, 0)]}],
        }
    )


def test_season_year_is_the_year_the_season_ends() -> None:
    assert season_year(date(2026, 9, 28)) == 2027
    assert season_year(date(2027, 3, 1)) == 2027


def test_uefa_results_standings_and_next_matchday() -> None:
    items = list(UefaChampionsSource().items(fake_uefa().fetcher(), set()))
    by_title = {item.title: item for item in items}

    assert items[0].body == (
        "UEFA Champions League, league phase Matchday 1, Wednesday 9 September 2026: "
        "Barcelona beat Feyenoord 5–1 at home. Barcelona goals: Raphinha 2, a brace (3', 57'), Karim "
        "Adeyemi 1 (22'), Lamine Yamal 1 (77' penalty). Feyenoord goals: Sem Steijn 1 (82'). "
        "Own goals: Gernot Trauner (85'). Player of the match: Raphinha (Barcelona)."
    )
    assert items[0].url == f"{SITE}/match/1/"
    assert items[1].body.endswith("Inter and Arsenal drew 1–1.")
    standings = by_title["Champions League standings after Matchday 1"]
    assert "1. Barcelona, 3 points from 1 game (1 win, 0 draws, 0 losses)." in standings.body
    assert "2. Inter, 1 point from 1 game (0 wins, 1 draw, 0 losses), 2 points behind" in (
        standings.body
    )
    fixtures = by_title["Champions League Matchday 2 fixtures"]
    assert "Tuesday 13 October 2026: Galatasaray host Barcelona." in fixtures.body
    assert datetime.now(UTC) >= standings.published_at


def test_barca_is_found_in_uefa_data_but_not_confused_with_espanyol() -> None:
    items = list(UefaChampionsSource().items(fake_uefa().fetcher(), set()))
    barca = TOPIC_FEEDS["fc-barcelona-football"]

    assert all(belongs_to_team(item, barca) for item in items if "Inter" not in item.title)
    espanyol = items[0].model_copy(
        update={"meta": {"type": "standings", "teams": ["RCD Espanyol de Barcelona"]}}
    )
    assert not belongs_to_team(espanyol, barca)


def test_team_names_are_spelled_out_and_unambiguous() -> None:
    def side(name: str, short: str) -> dict:
        return {"internationalName": name, "translations": {"shortName": {"EN": short}}}

    assert team(side("S. Bratislava", "Slovan Bratislava")) == "Slovan Bratislava"
    assert team(side("Paris", "Paris")) == "PSG"
    assert team(side("Man City", "Man. City")) == "Man City"
    assert team({"internationalName": "Barcelona"}) == "Barcelona"
