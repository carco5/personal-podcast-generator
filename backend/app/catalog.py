from typing import Literal

from pydantic import BaseModel, ConfigDict

Sport = Literal["football", "basketball"]
SPORTS: tuple[Sport, ...] = ("football", "basketball")


class Topic(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    kind: Literal["competition", "team"]
    sport: Sport


# Topics with verified sources; each one is wired to its providers in app/sources/registry.py.
CATALOG: dict[str, Topic] = {
    topic.key: topic
    for topic in (
        Topic(
            key="fc-barcelona-football", name="FC Barcelona football", kind="team", sport="football"
        ),
        Topic(
            key="fc-barcelona-basketball",
            name="FC Barcelona basketball",
            kind="team",
            sport="basketball",
        ),
        Topic(key="laliga", name="LaLiga", kind="competition", sport="football"),
        Topic(
            key="champions-league",
            name="UEFA Champions League",
            kind="competition",
            sport="football",
        ),
        Topic(key="euroleague", name="EuroLeague", kind="competition", sport="basketball"),
        Topic(key="liga-acb", name="Liga ACB", kind="competition", sport="basketball"),
        Topic(key="nba", name="NBA", kind="competition", sport="basketball"),
    )
}
