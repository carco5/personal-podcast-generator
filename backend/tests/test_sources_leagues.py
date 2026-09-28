import json

import pytest
from pydantic import SecretStr

from app.sources.acb import CALENDAR, AcbCalendarSource, calendar_data
from app.sources.guardian import SEARCH, GuardianSource
from app.sources.laliga import BASE, LaLigaSource, page_data
from tests.web import PARAGRAPH, FakeWeb

# ---------------------------------------------------------------------------------- LaLiga


def next_page(page_props: dict) -> str:
    data = json.dumps({"props": {"pageProps": page_props}})
    return f'<html><body><script id="__NEXT_DATA__" type="application/json">{data}</script>'


def team(name: str) -> dict:
    return {"nickname": name}


def match(number: int, home: str, away: str, score: tuple[int, int] | None, day: str) -> dict:
    return {
        "id": number,
        "date": f"{day}T19:00:00+00:00",
        "status": "FullTime" if score else "PreMatch",
        "home_team": team(home),
        "away_team": team(away),
        "home_score": score[0] if score else None,
        "away_score": score[1] if score else None,
    }


def standing(position: int, name: str, played: int, won: int, drawn: int, lost: int) -> dict:
    points = 3 * won + drawn
    return {
        "position": position,
        "team": team(name),
        "points": points,
        "played": played,
        "won": won,
        "drawn": drawn,
        "lost": lost,
    }


def fake_laliga() -> FakeWeb:
    return FakeWeb(
        {
            f"{BASE}/standing": next_page(
                {
                    "season": "2026",
                    "currentGameweek": {"week": 8},
                    "standings": [
                        standing(1, "FC Barcelona", 7, 7, 0, 0),
                        standing(2, "Athletic Club", 6, 3, 2, 1),
                    ],
                }
            ),
            f"{BASE}/results/2026-27/gameweek-7": next_page(
                {
                    "matches": [
                        match(1, "Sevilla FC", "FC Barcelona", (1, 3), "2026-09-19"),
                        match(2, "CA Osasuna", "Rayo Vallecano", (1, 1), "2026-09-19"),
                    ]
                }
            ),
            f"{BASE}/results/2026-27/gameweek-8": next_page(
                {"matches": [match(3, "FC Barcelona", "Getafe CF", None, "2026-10-10")]}
            ),
        }
    )


def test_laliga_results_standings_and_next_matchday() -> None:
    items = list(LaLigaSource().items(fake_laliga().fetcher(), set()))
    bodies = [item.body for item in items]

    assert bodies[0] == (
        "LaLiga EA Sports, Matchday 7, Saturday 19 September 2026: "
        "FC Barcelona beat Sevilla FC 3–1 away."
    )
    assert "CA Osasuna and Rayo Vallecano drew 1–1" in bodies[1]
    assert items[2].title == "LaLiga standings after Matchday 7"
    assert "1. FC Barcelona, 21 points from 7 games (7 wins, 0 draws, 0 losses)." in bodies[2]
    assert bodies[3] == (
        "LaLiga EA Sports Matchday 8 fixtures (official schedule). "
        "Saturday 10 October 2026: FC Barcelona host Getafe CF."
    )


def test_laliga_page_without_data_fails_clearly() -> None:
    with pytest.raises(ValueError, match="__NEXT_DATA__"):
        page_data("<html>redesigned</html>")


# -------------------------------------------------------------------------------------- ACB


def acb_page(teams: list[str], rounds: list[dict]) -> str:
    data = {"teams": [{"fullName": name} for name in teams], "rounds": rounds}
    flight = json.dumps(data, separators=(",", ":"))
    return f"<script>self.__next_f.push([1,{json.dumps('2d:' + flight)}])</script>"


def acb_match(number: int, home: int, away: int, score: tuple[int, int] | None, when: str) -> dict:
    return {
        "id": number,
        "homeTeam": f"$2d:props:data:teams:{home}",
        "awayTeam": f"$2d:props:data:teams:{away}",
        "homeTeamScore": score[0] if score else None,
        "awayTeamScore": score[1] if score else None,
        "startDateTime": when,
        "matchStatus": "FINALIZED" if score else "NOT_STARTED",
    }


ACB_TEAMS = ["Barça", "Leyma Coruña", "UCAM Murcia"]
ACB_ROUNDS = [
    {"roundNumber": 1, "matches": [acb_match(10, 0, 1, (119, 101), "2026-09-26T16:00:00Z")]},
    {"roundNumber": 2, "matches": [acb_match(20, 2, 0, None, "2026-10-04T10:00:00Z")]},
]


def test_acb_calendar_data_is_read_from_the_page() -> None:
    teams, rounds = calendar_data(acb_page(ACB_TEAMS, ACB_ROUNDS))

    assert [team["fullName"] for team in teams] == ACB_TEAMS
    assert rounds[1]["matches"][0]["matchStatus"] == "NOT_STARTED"


def test_acb_results_and_next_round() -> None:
    web = FakeWeb({CALENDAR: acb_page(ACB_TEAMS, ACB_ROUNDS)})

    items = list(AcbCalendarSource().items(web.fetcher(), set()))

    assert items[0].body == (
        "Liga ACB (Liga Endesa), Round 1, Saturday 26 September 2026: "
        "Barça beat Leyma Coruña 119–101 at home."
    )
    assert items[1].body == (
        "Liga ACB (Liga Endesa) Round 2 fixtures (official schedule). "
        "Sunday 4 October 2026: UCAM Murcia host Barça."
    )


def test_acb_page_without_data_fails_clearly() -> None:
    with pytest.raises(ValueError, match="teams and rounds"):
        calendar_data("<html>redesigned</html>")


# --------------------------------------------------------------------------------- Guardian


def test_guardian_sends_the_key_in_a_header_and_keeps_full_articles() -> None:
    body = " ".join([PARAGRAPH] * 5)

    def result(url: str, kind: str, text: str) -> dict:
        return {
            "type": kind,
            "webUrl": url,
            "webTitle": url.rsplit("/", 1)[1],
            "webPublicationDate": "2026-09-27T10:00:00Z",
            "fields": {"bodyText": text},
        }

    web = FakeWeb(
        {
            SEARCH: {
                "response": {
                    "results": [
                        result("https://g.example/football/good", "article", body),
                        result("https://g.example/football/live", "liveblog", body),
                        result("https://g.example/football/short", "article", "Too short."),
                    ]
                }
            }
        }
    )
    source = GuardianSource("guardian-laliga", "football/laligafootball", SecretStr("secret-k"))

    items = list(source.items(web.fetcher(), set()))

    assert [item.url for item in items] == ["https://g.example/football/good"]
    search = web.requests[-1]
    assert search.headers["api-key"] == "secret-k"
    assert "secret-k" not in str(search.url)
    assert search.url.params["tag"] == "football/laligafootball"
