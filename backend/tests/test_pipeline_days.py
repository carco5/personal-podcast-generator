from datetime import date

from app.pipeline.days import day_label, ordinal, with_day_labels

MONDAY = date(2026, 9, 28)


def test_ordinals() -> None:
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 31)] == [
        "1st",
        "2nd",
        "3rd",
        "4th",
        "11th",
        "12th",
        "13th",
        "21st",
        "22nd",
        "23rd",
        "31st",
    ]


def test_day_labels_relative_to_the_episode_day() -> None:
    assert day_label(date(2026, 9, 28), MONDAY) == "today"
    assert day_label(date(2026, 9, 27), MONDAY) == "yesterday"
    assert day_label(date(2026, 9, 29), MONDAY) == "tomorrow"
    assert day_label(date(2026, 9, 26), MONDAY) == "last Saturday"
    assert day_label(date(2026, 10, 4), MONDAY) == "this Sunday"
    assert day_label(date(2026, 9, 19), MONDAY) == "Saturday the 19th"
    assert day_label(date(2026, 10, 10), MONDAY) == "Saturday the 10th"


def test_dates_in_a_source_get_their_label() -> None:
    text = (
        "Liga ACB, Round 1, Saturday 26 September 2026: Barça beat Leyma Coruña 119–101. "
        "Next: Tuesday 29 September 2026."
    )

    assert with_day_labels(text, MONDAY) == (
        "Liga ACB, Round 1, Saturday 26 September 2026 [say: last Saturday]: Barça beat Leyma "
        "Coruña 119–101. Next: Tuesday 29 September 2026 [say: tomorrow]."
    )
