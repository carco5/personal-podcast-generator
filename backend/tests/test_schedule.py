from datetime import UTC, datetime
from datetime import time as clock

from app.models import PodcastSettings
from app.schedule import latest_slot, next_slot

NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
SEVEN_AM_MADRID = datetime(2026, 9, 29, 5, 0, tzinfo=UTC)


def seven_am(days: list[int]) -> PodcastSettings:
    return PodcastSettings(schedule_days=days, schedule_time=clock(7, 0), timezone="Europe/Madrid")


def test_the_slot_follows_the_listeners_time_zone() -> None:
    podcast = seven_am([1, 2, 3, 4, 5, 6, 7])

    assert latest_slot(podcast, NOW) == SEVEN_AM_MADRID
    winter = datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
    assert latest_slot(podcast, winter) == datetime(2026, 10, 27, 6, 0, tzinfo=UTC)


def test_the_slot_is_the_last_one_that_has_arrived() -> None:
    podcast = seven_am([1])

    assert latest_slot(podcast, NOW) == datetime(2026, 9, 28, 5, 0, tzinfo=UTC)
    monday_early = datetime(2026, 9, 28, 4, 0, tzinfo=UTC)
    assert latest_slot(podcast, monday_early) == datetime(2026, 9, 21, 5, 0, tzinfo=UTC)
    podcast.schedule_days = []
    assert latest_slot(podcast, NOW) is None


def test_the_next_slot_is_the_first_one_still_to_come() -> None:
    daily = seven_am([1, 2, 3, 4, 5, 6, 7])

    assert next_slot(daily, NOW) == datetime(2026, 9, 30, 5, 0, tzinfo=UTC)
    early = datetime(2026, 9, 29, 4, 0, tzinfo=UTC)
    assert next_slot(daily, early) == SEVEN_AM_MADRID
    assert next_slot(seven_am([1]), NOW) == datetime(2026, 10, 5, 5, 0, tzinfo=UTC)
    saturday = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
    assert next_slot(daily, saturday) == datetime(2026, 10, 25, 6, 0, tzinfo=UTC)
    assert next_slot(seven_am([]), NOW) is None
