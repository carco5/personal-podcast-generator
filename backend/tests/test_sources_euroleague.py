from datetime import UTC, date, datetime

from app.sources.euroleague import (
    API,
    STANDINGS,
    EuroleagueSource,
    club_name,
    player_name,
    season_code,
)
from tests.web import FakeWeb

SEASON = season_code(datetime.now(UTC).date())
GAMES = f"{API}/v2/competitions/E/seasons/{SEASON}/games"


def side(name: str, score: int, quarters: tuple[int, ...], overtime: int | None = None) -> dict:
    partials = {f"partials{number}": points for number, points in enumerate(quarters, start=1)}
    partials["extraPeriods"] = {"1": overtime} if overtime is not None else {}
    return {"club": {"abbreviatedName": name}, "score": score, "partials": partials}


def game(code: int, number: int, played: bool, day: str, home: dict, road: dict) -> dict:
    return {
        "gameCode": code,
        "round": number,
        "roundAlias": f"Round {number}",
        "played": played,
        "date": f"{day}T20:30:00",
        "utcDate": f"{day}T18:30:00Z",
        "local": home,
        "road": road,
    }


def player(name: str, points: float, rebounds: float, assists: float, pir: float) -> dict:
    return {
        "player": {"person": {"name": name}},
        "stats": {
            "points": points,
            "totalRebounds": rebounds,
            "assistances": assists,
            "valuation": pir,
        },
    }


ROUND_1 = [
    game(
        1,
        1,
        True,
        "2026-09-24",
        side("FC Barcelona", 89, (16, 29, 18, 26)),
        side("Anadolu Efes", 82, (25, 19, 23, 15)),
    ),
    game(
        2,
        1,
        True,
        "2026-09-25",
        side("Baskonia", 95, (20, 20, 20, 25), overtime=10),
        side("Olympiacos", 106, (25, 20, 20, 20), overtime=21),
    ),
]
ROUND_2 = [
    game(
        3,
        2,
        True,
        "2026-09-29",
        side("Dubai", 70, (20, 20, 15, 15)),
        side("FC Barcelona", 80, (20, 20, 20, 20)),
    ),
    game(
        4,
        2,
        False,
        "2026-09-30",
        side("Panathinaikos", 0, (0, 0, 0, 0)),
        side("LDLC ASVEL", 0, (0, 0, 0, 0)),
    ),
]


def stats(home: list[dict], road: list[dict]) -> dict:
    return {"local": {"players": home}, "road": {"players": road}}


def stats_url(code: int) -> str:
    return f"{API}/v3/competitions/E/seasons/{SEASON}/games/{code}/stats"


def fake_api() -> FakeWeb:
    return FakeWeb(
        {
            GAMES: {"data": ROUND_1 + ROUND_2},
            stats_url(1): stats(
                [player("PUNTER, KEVIN", 19.0, 1.0, 1.0, 22.0)],
                [
                    player("SARIC, DARIO", 17.0, 5.0, 2.0, 26.0),
                    player("JAMES, MIKE", 22.0, 4.0, 5.0, 24.0),
                ],
            ),
            stats_url(2): stats(
                [player("A, B", 10.0, 1.0, 1.0, 9.0)], [player("C, D", 20.0, 2.0, 2.0, 25.0)]
            ),
            stats_url(3): stats(
                [player("E, F", 12.0, 3.0, 3.0, 15.0)], [player("G, H", 14.0, 6.0, 3.0, 18.0)]
            ),
            STANDINGS.format(season=SEASON, round=1): {
                "teams": [
                    {
                        "position": 1,
                        "gamesWon": 1,
                        "gamesLost": 0,
                        "club": {"abbreviatedName": "FC Barcelona"},
                    },
                    {
                        "position": 2,
                        "gamesWon": 0,
                        "gamesLost": 1,
                        "club": {"abbreviatedName": "Anadolu Efes"},
                    },
                ]
            },
        }
    )


def test_season_code_follows_the_season_not_the_year() -> None:
    assert season_code(date(2026, 9, 28)) == "E2026"
    assert season_code(date(2027, 3, 1)) == "E2026"


def test_player_names_are_written_for_speech() -> None:
    assert player_name("JONES, CARLIK") == "Carlik Jones"
    assert player_name("ALSTON JR. , DERRICK") == "Derrick Alston Jr."


def test_result_text_is_winner_first_with_each_teams_best_player() -> None:
    items = {item.url: item for item in EuroleagueSource().items(fake_api().fetcher(), set())}
    barca = items[stats_url(1)]

    assert barca.kind == "data"
    assert barca.body == (
        "EuroLeague Round 1, Thursday 24 September 2026: FC Barcelona beat Anadolu Efes 89–82 "
        "at home, winning by 7 points. Points by quarter: FC Barcelona 16, 29, 18, 26; Anadolu Efes "
        "25, 19, 23, 15. Best player of each team by valuation (PIR): Kevin Punter (FC "
        "Barcelona): 19 points, 1 rebound, 1 assist, PIR 22; Dario Saric (Anadolu Efes): 17 "
        "points, 5 rebounds, 2 assists, PIR 26."
    )
    assert barca.meta["teams"] == ["FC Barcelona", "Anadolu Efes"]


def test_away_win_and_overtime() -> None:
    items = {item.url: item for item in EuroleagueSource().items(fake_api().fetcher(), set())}

    assert "Olympiacos beat Baskonia 106–95 away, winning by 11 points" in items[stats_url(2)].body
    assert "Olympiacos 25, 20, 20, 20, plus 21 in overtime" in items[stats_url(2)].body


def test_standings_of_the_last_complete_round_and_pending_fixtures() -> None:
    items = list(EuroleagueSource().items(fake_api().fetcher(), set()))
    by_type = {item.meta["type"]: item for item in items if item.meta["type"] != "result"}

    assert by_type["standings"].title == "EuroLeague standings after Round 1"
    assert "2. Anadolu Efes, 0 wins and 1 loss." in by_type["standings"].body
    assert by_type["fixtures"].body == (
        "EuroLeague Round 2 fixtures (official schedule). "
        "Wednesday 30 September 2026: Panathinaikos host LDLC ASVEL."
    )
    assert by_type["fixtures"].meta["games"] == [
        {"date": "2026-09-30", "home": "Panathinaikos", "away": "LDLC ASVEL"}
    ]


def test_known_results_are_not_downloaded_again() -> None:
    web = fake_api()
    known = {stats_url(1), stats_url(2), stats_url(3), STANDINGS.format(season=SEASON, round=1)}

    items = list(EuroleagueSource().items(web.fetcher(), known))

    assert [item.meta["type"] for item in items] == ["fixtures"]
    assert not any("/stats" in url or "standings" in url for url in web.urls())


def test_club_names_keep_the_sport_clear() -> None:
    assert club_name({"abbreviatedName": "Paris", "name": "Paris Basketball"}) == "Paris Basketball"
    assert (
        club_name({"abbreviatedName": "Valencia", "name": "Valencia Basket"}) == "Valencia Basket"
    )
    assert club_name({"abbreviatedName": "Partizan", "name": "Partizan Mozzart Bet Belgrade"}) == (
        "Partizan"
    )
    assert club_name({"abbreviatedName": "FC Barcelona"}) == "FC Barcelona"
