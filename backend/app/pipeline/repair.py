from pydantic import BaseModel

from app.pipeline.common import Run
from app.pipeline.script import ALLOWED_TAGS, MAX_WRITE_CHARS, EpisodeSource, Script, Turn

REPAIR_EFFORT = "low"


class RepairedTurn(BaseModel):
    turn: str
    text: str
    source_ids: list[str]


class Repairs(BaseModel):
    turns: list[RepairedTurn]


INSTRUCTIONS = """\
You fix single turns of a two-host podcast script that failed a fact check. For each turn you get
the turns around it, what was wrong, and the sources it may cite. Rewrite only that turn:
- keep its speaker and its place in the conversation, and make it no longer than it was;
- state only what its sources say, framed exactly as they frame it (a team's best player by
  rating is not its top scorer); drop any claim the sources do not support and keep the rest;
- a turn may become a short reaction with no sources;
- digits for numbers from the sources; scores winner first with an en dash ("89–82");
- only these audio tags, at the start of the turn: {tags}; no other brackets, no markdown, no
  URLs and no source ids in the spoken text.
Return one entry per turn you were given, with its id.
"""


def turn_positions(script: Script) -> dict[str, tuple[int, int]]:
    return {
        f"{segment.key}.{number}": (s, number - 1)
        for s, segment in enumerate(script.segments)
        for number in range(1, len(segment.turns) + 1)
    }


def repair_turns(
    run: Run, script: Script, issues: dict[str, list[str]], sources: dict[str, EpisodeSource]
) -> Script:
    positions = turn_positions(script)
    lines = ["TURNS TO FIX"]
    cited: set[str] = set()
    for turn_id, problems in issues.items():
        s, t = positions[turn_id]
        turns = script.segments[s].turns
        turn = turns[t]
        cited |= {sid for sid in turn.source_ids if sid in sources}
        lines.append(f"\n[{turn_id}] {turn.speaker}, sources {turn.source_ids}: {turn.text}")
        if t > 0:
            lines.append(f"  before ({turns[t - 1].speaker}): {turns[t - 1].text}")
        if t + 1 < len(turns):
            lines.append(f"  after ({turns[t + 1].speaker}): {turns[t + 1].text}")
        lines += [f"  problem: {problem}" for problem in problems]
    lines += ["", "SOURCES"]
    for sid in sorted(cited, key=lambda s: (s != "CTX", s)):
        source = sources[sid]
        text = source.text if source.is_data else source.text[:MAX_WRITE_CHARS]
        lines += ["", f"[{sid}] {source.label}", text]
    answer, call = run.llm.parse(
        model=run.config.openai_write_model,
        instructions=INSTRUCTIONS.format(tags=", ".join(f"[{t}]" for t in ALLOWED_TAGS)),
        prompt="\n".join(lines),
        schema=Repairs,
        effort=REPAIR_EFFORT,
    )
    run.calls.append(call)
    fixed = script.model_copy(deep=True)
    for repaired in answer.turns:
        if repaired.turn in issues:
            s, t = positions[repaired.turn]
            speaker = fixed.segments[s].turns[t].speaker
            fixed.segments[s].turns[t] = Turn(
                speaker=speaker, text=repaired.text, source_ids=repaired.source_ids
            )
    return fixed


def remove_turns(script: Script, turn_ids: list[str]) -> Script:
    positions = turn_positions(script)
    fixed = script.model_copy(deep=True)
    for s, t in sorted((positions[turn_id] for turn_id in turn_ids), reverse=True):
        del fixed.segments[s].turns[t]
    return fixed
