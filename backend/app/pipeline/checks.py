import re
from typing import Literal

from pydantic import BaseModel

from app.models import Language
from app.pipeline.common import Run, StageFailed
from app.pipeline.script import (
    ALLOWED_TAGS,
    MAX_TAGS,
    SPANISH_GLOSSARY,
    EpisodeSource,
    Script,
    script_sources,
    write_script,
)

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
SCORE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
TAG = re.compile(r"\[([^\]]*)\]")
URL = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|net|org|es)\b", re.IGNORECASE)
MARKDOWN = re.compile(r"[*_#`|>]|\]\(")
EMOJI = re.compile(r"[\U0001F000-\U0001FAFF☀-➿]")
SPOKEN_ID = re.compile(r"\b(?:S\d+|CTX)\b")
NUMBER_WORD = (
    r"(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen"
    r"|sixteen|seventeen|eighteen|nineteen|dozen|hundred|thousand|million"
    r"|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
    r"(?:-(?:one|two|three|four|five|six|seven|eight|nine))?)"
)
STAT = (
    r"(?:points?|rebounds?|assists?|steals?|blocks?|goals?|wins?|victories|losses|defeats"
    r"|draws?|games?|matches|minutes?|seconds?|seasons?|titles?|trophies|fouls?|turnovers?"
    r"|three-pointers?|threes|triples|percent|times|players?)"
)
NUMBER_WORDS = re.compile(rf"\b{NUMBER_WORD}(?:\s+[a-z]+)?\s+{STAT}\b", re.IGNORECASE)
MAX_TURN_CHARS = 500
LENGTH_TOLERANCE = 1.25
JUDGE_EFFORT = "medium"


Verdict = Literal[
    "supported",
    "opinion",
    "unsupported",
    "contradicted",
    "overstated",
    "misattributed",
    "wrong_time",
]


class TurnVerdict(BaseModel):
    turn: str
    verdict: Verdict
    explanation: str


class Judgement(BaseModel):
    verdicts: list[TurnVerdict]


JUDGE_INSTRUCTIONS = """\
You check a two-host podcast script against its sources, turn by turn. Each turn lists the ids
of its sources; [CTX] is the episode context (today's date) and counts as a source.
Return exactly one verdict for every turn:
- supported: every factual claim is in the turn's cited sources, about the same team or player,
  on the right day, and with no more certainty than the source.
- opinion: the turn only reacts, gives an opinion, asks a question or links two stories, and
  states no fact. A turn with no sources may only be this.
- unsupported: it states something that its cited sources do not say.
- contradicted: a cited source says otherwise.
- overstated: it states as certain what the source reports as a rumour or with a hedge.
- misattributed: it gives a fact to the wrong team, player or outlet.
- wrong_time: it places an event on the wrong day, or tells a future event as past (or the
  reverse).
Judge each turn only against its own cited sources and [CTX]. Opinions about sourced facts are
fine. Statements about the episode itself (the welcome, what it covers, the sign-off) are
transitions, not facts. [CTX] lists the dates of the days around today: use it for weekdays. Sources may be in Spanish: compare the meaning across languages, including the day of the
week. {glossary}
Explain every verdict other than supported or opinion in one sentence.
"""


def check_script(run: Run) -> dict:
    rounds: list[dict] = []
    for attempt in (1, 2):
        sources = script_sources(run)
        script = Script.model_validate(run.episode.script)
        problems = code_problems(script, run.episode.plan, sources)
        judged = attempt == 1 or not problems
        if judged:
            problems += judge_problems(run, script, sources)
        rounds.append({"problems": problems, "judged": judged})
        if not problems:
            return {"rounds": rounds}
        if attempt == 1:
            write_script(run, problems)
    first = "; ".join(rounds[-1]["problems"][:3])
    raise StageFailed(f"check: the script failed twice ({first})", {"rounds": rounds})


def code_problems(script: Script, plan: dict, sources: dict[str, EpisodeSource]) -> list[str]:
    problems: list[str] = []
    expected = ["intro", *[block["key"] for block in plan["blocks"]], "closing"]
    keys = [segment.key for segment in script.segments]
    if keys != expected:
        return [f"The segments must be exactly {expected}, in that order; got {keys}."]
    tags = 0
    for segment in script.segments:
        allowed = allowed_ids(segment.key, plan, sources)
        for number, turn in enumerate(segment.turns, start=1):
            where = f"{segment.key} turn {number}"
            tags += len(TAG.findall(turn.text))
            problems += [
                f"{where}: {p}" for p in turn_problems(turn.text, turn.source_ids, allowed, sources)
            ]
    if tags > MAX_TAGS:
        problems.append(f"The script has {tags} audio tags; the maximum is {MAX_TAGS}.")
    problems += structure_problems(script, plan)
    return problems


def allowed_ids(key: str, plan: dict, sources: dict[str, EpisodeSource]) -> set[str]:
    if key in ("intro", "closing"):
        return set(sources)
    block = next(block for block in plan["blocks"] if block["key"] == key)
    story_ids = {sid for story in block["stories"] for sid in story["source_ids"]}
    return story_ids | set(block["context_ids"]) | {"CTX"}


def turn_problems(
    text: str, source_ids: list[str], allowed: set[str], sources: dict[str, EpisodeSource]
) -> list[str]:
    problems = []
    unknown = [sid for sid in source_ids if sid not in allowed]
    if unknown:
        problems.append(f"cites {unknown}, which are not sources of this segment")
    cited = [sources[sid] for sid in source_ids if sid in sources]
    available = set().union(*(source_numbers(s.text, s.language) for s in cited))
    missing = sorted(numbers_in(text, "en") - available)
    if missing:
        problems.append(f"the numbers {missing} are not in its cited sources {source_ids}")
    pairs = set().union(*(score_pairs(s.text) for s in cited))
    for first, second in score_pairs(text):
        if first < second:
            problems.append(f"the score {first}–{second} must be written winner first")
        elif (first, second) not in pairs and (second, first) not in pairs:
            problems.append(f"the score {first}–{second} is not in its cited sources")
    if match := NUMBER_WORDS.search(text):
        problems.append(f'"{match.group(0)}" must use digits so it can be checked')
    for tag in TAG.findall(text):
        if tag not in ALLOWED_TAGS:
            problems.append(f"[{tag}] is not an allowed audio tag")
    for pattern, what in ((URL, "a URL"), (MARKDOWN, "markdown"), (EMOJI, "an emoji")):
        if pattern.search(TAG.sub("", text)):
            problems.append(f"contains {what}, which the voice would read aloud")
    if SPOKEN_ID.search(text):
        problems.append("says a source id aloud")
    if len(text) > MAX_TURN_CHARS:
        problems.append(f"is {len(text)} characters long; keep turns under {MAX_TURN_CHARS}")
    return problems


def structure_problems(script: Script, plan: dict) -> list[str]:
    problems = []
    cited = {
        segment.key: {sid for turn in segment.turns for sid in turn.source_ids}
        for segment in script.segments
    }
    lead = plan["blocks"][0]["stories"][0]["source_ids"]
    if not cited["intro"] & set(lead):
        problems.append(f"The intro must open with the lead story and cite {lead}.")
    for block in plan["blocks"]:
        for number, story in enumerate(block["stories"], start=1):
            if not cited[block["key"]] & set(story["source_ids"]):
                problems.append(
                    f"{block['key']}: story {number} ({story['source_ids']}) is not covered."
                )
    length = sum(len(turn.text) for segment in script.segments for turn in segment.turns)
    planned = plan["intro_chars"] + plan["closing_chars"] + sum(b["chars"] for b in plan["blocks"])
    if length > planned * LENGTH_TOLERANCE:
        problems.append(f"The script has {length} characters; the plan allows about {planned}.")
    return problems


def numbers_in(text: str, language: Language) -> set[str]:
    return {normalize(raw, language) for raw in NUMBER.findall(text)}


def normalize(raw: str, language: Language) -> str:
    plain = raw.replace(".", "").replace(",", ".") if language == "es" else raw.replace(",", "")
    whole, _, decimals = plain.partition(".")
    return f"{int(whole)}.{decimals}" if decimals else str(int(whole))


EN_TEENS = ["two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
            "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen"]  # fmt: skip
ES_TEENS = ["dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once",
            "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho",
            "diecinueve"]  # fmt: skip
EN_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ES_TENS = ["veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
EN_DIGITS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
ES_DIGITS = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
ES_TWENTIES = ["veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
               "veintiséis", "veintisiete", "veintiocho", "veintinueve"]  # fmt: skip


def build_number_words() -> dict[Language, dict[str, int]]:
    words: dict[Language, dict[str, int]] = {"en": {"zero": 0}, "es": {"cero": 0}}
    words["en"] |= {word: n for n, word in enumerate(EN_TEENS, start=2)}
    words["es"] |= {word: n for n, word in enumerate(ES_TEENS, start=2)}
    words["es"] |= {word: n for n, word in enumerate(ES_TWENTIES, start=21)}
    for tens, (en, es) in enumerate(zip(EN_TENS, ES_TENS, strict=True), start=2):
        words["en"][en], words["es"][es] = tens * 10, tens * 10
        for unit, (en_digit, es_digit) in enumerate(zip(EN_DIGITS, ES_DIGITS, strict=True), 1):
            words["en"][f"{en}-{en_digit}"] = tens * 10 + unit
            if tens > 2:
                words["es"][f"{es} y {es_digit}"] = tens * 10 + unit
    return words


NUMBER_WORD_VALUES = build_number_words()
NUMBER_WORD_PATTERNS = {
    language: re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, values), key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    for language, values in NUMBER_WORD_VALUES.items()
}


def source_numbers(text: str, language: Language) -> set[str]:
    words = NUMBER_WORD_PATTERNS[language].findall(text)
    return numbers_in(text, language) | {
        str(NUMBER_WORD_VALUES[language][word.lower()]) for word in words
    }


def score_pairs(text: str) -> set[tuple[int, int]]:
    return {(int(a), int(b)) for a, b in SCORE.findall(text)}


def judge_prompt(script: Script, sources: dict[str, EpisodeSource]) -> tuple[list[str], str]:
    turns = {
        f"{segment.key}.{number}": turn
        for segment in script.segments
        for number, turn in enumerate(segment.turns, start=1)
    }
    lines = ["SOURCES"]
    for source in sources.values():
        lines += ["", f"[{source.source_id}] {source.label}", source.text]
    lines += ["", "TURNS"]
    for turn_id, turn in turns.items():
        lines.append(f"[{turn_id}] sources {turn.source_ids}: {turn.text}")
    return list(turns), "\n".join(lines)


def judge_problems(run: Run, script: Script, sources: dict[str, EpisodeSource]) -> list[str]:
    turn_ids, prompt = judge_prompt(script, sources)
    judgement, call = run.llm.parse(
        model=run.config.openai_judge_model,
        instructions=JUDGE_INSTRUCTIONS.format(glossary=SPANISH_GLOSSARY),
        prompt=prompt,
        schema=Judgement,
        effort=JUDGE_EFFORT,
    )
    run.calls.append(call)
    verdicts = {verdict.turn: verdict for verdict in judgement.verdicts}
    problems = []
    for turn_id in turn_ids:
        verdict = verdicts.get(turn_id)
        if verdict is None:
            problems.append(f"{turn_id}: the fact check did not review this turn")
        elif verdict.verdict not in ("supported", "opinion"):
            problems.append(f"{turn_id}: {verdict.verdict}: {verdict.explanation}")
    return problems
