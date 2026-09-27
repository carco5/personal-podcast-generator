from typing import Literal

from pydantic import BaseModel, ConfigDict


class Topic(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    kind: Literal["competition", "team"]


# Topics with verified sources; each one is wired to its providers in Step 5.
CATALOG: dict[str, Topic] = {
    topic.key: topic
    for topic in (
        Topic(key="fc-barcelona", name="FC Barcelona", kind="team"),
        Topic(key="euroleague", name="EuroLeague", kind="competition"),
        Topic(key="liga-acb", name="Liga ACB", kind="competition"),
        Topic(key="nba", name="NBA", kind="competition"),
        Topic(key="laliga", name="LaLiga", kind="competition"),
        Topic(key="champions-league", name="UEFA Champions League", kind="competition"),
    )
}
