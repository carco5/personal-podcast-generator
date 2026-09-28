import re
from datetime import date

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
SPOKEN_DATE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\d{1,2}) "
    rf"({'|'.join(MONTHS)}) (\d{{4}})\b"
)


def ordinal(number: int) -> str:
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def day_label(day: date, today: date) -> str:
    delta = (day - today).days
    if delta == 0:
        return "today"
    if delta == -1:
        return "yesterday"
    if delta == 1:
        return "tomorrow"
    if -6 <= delta < 0:
        return f"last {day:%A}"
    if 0 < delta <= 6:
        return f"this {day:%A}"
    return f"{day:%A} the {ordinal(day.day)}"


def with_day_labels(text: str, today: date) -> str:
    def label(match: re.Match[str]) -> str:
        day_of_month, month, year = match.groups()
        day = date(int(year), MONTHS.index(month) + 1, int(day_of_month))
        return f"{match.group(0)} [say: {day_label(day, today)}]"

    return SPOKEN_DATE.sub(label, text)
