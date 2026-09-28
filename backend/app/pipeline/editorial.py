from pydantic import BaseModel

from app.catalog import CATALOG
from app.pipeline.common import Run
from app.pipeline.script import MAX_WRITE_CHARS, script_sources

PLAN_EFFORT = "low"
MAX_ROUNDUP = 3
MAX_FACTS = 5
MAX_THREADS = 3
WEIGHT_POINTS = {"high": 3, "medium": 2, "low": 1}
MAJOR_BONUS = 1.5
BRIEF_CHARS = 120


class Fact(BaseModel):
    text: str
    source_ids: list[str]


class SectionPlan(BaseModel):
    key: str
    lead_story: int
    angle: str
    key_facts: list[Fact]
    roundup_ids: list[str]
    next_up: Fact | None
    brief: bool
    major: bool


class Thread(BaseModel):
    from_key: str
    to_key: str
    link: Fact


class EditorialPlan(BaseModel):
    hook: Fact
    sections: list[SectionPlan]
    threads: list[Thread]


INSTRUCTIONS = """\
You are the editor of "{show}", a personal sports podcast for one listener. {listener}
You receive the episode's sections in order, each with its candidate stories and its context,
and all the sources. Plan the episode; a writer will turn your plan into a conversation.

For each section, in the given order:
- lead_story: the number of its single most impactful story, to be told in depth.
- angle: one sentence on why it matters to this listener.
- key_facts: up to 5 facts for the lead story, each with the ids of the sources that state it.
  Prefer player-level detail: scorers, stat lines, quotes. Give fewer when the sources hold
  fewer: never invent and never pad.
- roundup_ids: the source ids of at most 3 other results worth one compressed line; leave the
  rest out. Only results, never the lead story's sources.
- next_up: the section's nearest upcoming game, with the day as its source labels it ([say:
  ...]), and its source ids; null if there is none.
- brief: true when nothing in the section is impactful. It then gets one short line.
- major: true only for a story clearly bigger than a normal day: a record, a result that changes
  a title race, a star's move.

Impactful means: anything involving the listener's team, records and streaks, upsets, big or
dramatic margins, results that change the table, and standout individual performances. Routine
results stay out.
A competition section looks through the eyes of a fan of the listener's team: lead with what
matters most to that team there (its rivals' results, the table, its next opponents) unless
something else is clearly bigger. Never repeat what the team's own section tells: the writer will
refer back to it. A competition the listener's team does not play in is covered on its own terms.

hook: the cold open, one sentence with its source ids: the freshest relevant story, preferring
the last 72 hours or the next 48 hours over older results. In a catch-up episode, older results
are context, not the hook.
threads: up to 3 real connections between sections (an upcoming opponent who just played, a
rival losing twice, the same storyline), each with the two section keys and one sentence with
its source ids.
Use only facts from the sources and only the ids listed. Never compute numbers.
"""


def plan_episode(run: Run) -> dict:
    plan = run.episode.plan
    sources = script_sources(run)
    prompt = planner_prompt(plan, sources)
    problems: list[str] = []
    editorial: EditorialPlan | None = None
    for _attempt in (1, 2):
        text = prompt
        if problems:
            text += "\n\nYOUR PREVIOUS PLAN had these problems; fix them:\n" + "\n".join(
                f"- {p}" for p in problems
            )
        answer, call = run.llm.parse(
            model=run.config.openai_write_model,
            instructions=planner_instructions(run),
            prompt=text,
            schema=EditorialPlan,
            effort=PLAN_EFFORT,
        )
        run.calls.append(call)
        problems = plan_problems(answer, plan, set(sources))
        if not problems:
            editorial = answer
            break
    fallback = editorial is None
    if editorial is None:
        editorial = code_plan(plan)
    shares = budget_shares(plan, editorial)
    for block in plan["blocks"]:
        block["chars"] = shares[block["key"]]
    run.episode.plan = {**plan, "editorial": editorial.model_dump(), "plan_fallback": fallback}
    run.session.flush()
    return {"fallback": fallback, "problems": problems, "shares": shares}


def planner_instructions(run: Run) -> str:
    interests = ", ".join(
        f"{CATALOG[i.topic].name if i.topic in CATALOG else i.topic}"
        f" ({CATALOG[i.topic].kind if i.topic in CATALOG else 'topic'}, weight {i.weight})"
        for i in run.interests
    )
    listener = (
        f"The listener's interests, most important first: {interests}. "
        f"This episode is {run.episode.plan['coverage']}."
    )
    return INSTRUCTIONS.format(show=run.podcast.show_name, listener=listener)


def planner_prompt(plan: dict, sources: dict) -> str:
    lines = [f"[CTX] {sources['CTX'].text}", "", "SECTIONS"]
    for block in plan["blocks"]:
        lines.append(f'- Section "{block["key"]}" ({block["title"]}; weight {block["weight"]}):')
        for number, story in enumerate(block["stories"], start=1):
            titles = " | ".join(
                sources[sid].text.splitlines()[0] for sid in story["source_ids"] if sid in sources
            )
            lines.append(f"  Story {number}: {', '.join(story['source_ids'])} — {titles}")
        if block["context_ids"]:
            lines.append(f"  Context: {', '.join(block['context_ids'])}")
    lines += ["", "SOURCES"]
    for source in sources.values():
        if source.source_id != "CTX":
            text = source.text if source.is_data else source.text[:MAX_WRITE_CHARS]
            lines += ["", f"[{source.source_id}] {source.label}", text]
    return "\n".join(lines)


def plan_problems(answer: EditorialPlan, plan: dict, known: set[str]) -> list[str]:
    blocks = {block["key"]: block for block in plan["blocks"]}
    problems = []
    if [s.key for s in answer.sections] != list(blocks):
        return [f"The sections must be exactly {list(blocks)}, in that order."]
    for section in answer.sections:
        block = blocks[section.key]
        stories = block["stories"]
        allowed = {sid for story in stories for sid in story["source_ids"]}
        allowed |= set(block["context_ids"]) | {"CTX"}
        if not 1 <= section.lead_story <= len(stories):
            problems.append(f"{section.key}: lead_story must be between 1 and {len(stories)}.")
            continue
        lead = set(stories[section.lead_story - 1]["source_ids"])
        others = {sid for story in stories for sid in story["source_ids"]} - lead
        if len(section.roundup_ids) > MAX_ROUNDUP or not set(section.roundup_ids) <= others:
            problems.append(
                f"{section.key}: roundup_ids must be at most {MAX_ROUNDUP} ids of its other stories."
            )
        low = 0 if section.brief else 1
        if not low <= len(section.key_facts) <= MAX_FACTS:
            problems.append(f"{section.key}: give {low} to {MAX_FACTS} key facts.")
        for fact in section.key_facts:
            if not fact.source_ids or not set(fact.source_ids) <= allowed:
                problems.append(f"{section.key}: key fact '{fact.text}' must cite its own sources.")
        if section.next_up and not set(section.next_up.source_ids) <= allowed:
            problems.append(f"{section.key}: next_up must cite this section's context.")
    if not answer.hook.source_ids or not set(answer.hook.source_ids) <= known:
        problems.append("hook must cite sources of this episode.")
    if len(answer.threads) > MAX_THREADS:
        problems.append(f"Give at most {MAX_THREADS} threads.")
    for thread in answer.threads:
        if thread.from_key not in blocks or thread.to_key not in blocks:
            problems.append("Each thread must join two section keys.")
        elif not set(thread.link.source_ids) <= known:
            problems.append(f"Thread '{thread.link.text}' must cite sources of this episode.")
    return problems


def code_plan(plan: dict) -> EditorialPlan:
    sections = []
    for block in plan["blocks"]:
        lead = block["stories"][0]["source_ids"]
        sections.append(
            SectionPlan(
                key=block["key"],
                lead_story=1,
                angle="",
                key_facts=[Fact(text=block["title"], source_ids=lead)],
                roundup_ids=[],
                next_up=None,
                brief=False,
                major=False,
            )
        )
    hook = Fact(
        text=plan["blocks"][0]["title"], source_ids=plan["blocks"][0]["stories"][0]["source_ids"]
    )
    return EditorialPlan(hook=hook, sections=sections, threads=[])


def budget_shares(plan: dict, editorial: EditorialPlan) -> dict[str, int]:
    body = plan["target_chars"] - plan["intro_chars"] - plan["closing_chars"]
    sections = {section.key: section for section in editorial.sections}
    brief = [b["key"] for b in plan["blocks"] if sections[b["key"]].brief]
    points = {
        b["key"]: WEIGHT_POINTS[b["weight"]] * (MAJOR_BONUS if sections[b["key"]].major else 1)
        for b in plan["blocks"]
        if b["key"] not in brief
    }
    shares = {key: BRIEF_CHARS for key in brief}
    rest = body - BRIEF_CHARS * len(brief)
    total = sum(points.values()) or 1
    exact = {key: rest * value / total for key, value in points.items()}
    for key, value in exact.items():
        shares[key] = int(value)
    leftover = body - sum(shares.values())
    for key in sorted(exact, key=lambda k: exact[k] - int(exact[k]), reverse=True)[:leftover]:
        shares[key] += 1
    return {b["key"]: shares[b["key"]] for b in plan["blocks"]}
