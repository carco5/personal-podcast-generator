"""Step 3 spike: real news -> short two-host script -> v3 dialogue audio, with measurements.

Throwaway code that measures cost, latency and audio behaviour before the real pipeline is
built. The findings are in docs/spike.md. The `write` and `voice` stages make PAID API calls.

Run from backend/, one stage at a time (each stage reads the previous stage's output):
    python scripts/spike.py fetch              # free: news and results -> sources.json
    python scripts/spike.py write [--dry-run]  # OpenAI: two-host script -> script.json
    python scripts/spike.py voice [--dry-run]  # ElevenLabs: one request per segment
    python scripts/spike.py master             # free: join and normalise -> spike.mp3
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import feedparser
import httpx
import trafilatura
from elevenlabs import DialogueInput, ElevenLabs
from openai import OpenAI
from openai.types.responses import ResponseUsage
from pydantic import BaseModel, SecretStr

from app.config import get_settings

OUT = Path(__file__).resolve().parents[2] / "data" / "spike"

# An honest User-Agent. These sources' robots.txt allowed it when checked on 2026-09-26.
HEADERS = {"User-Agent": "PersonalPodcastBot/0.1 (+https://github.com/carco5)"}

EUROLEAGUE_GAMES = "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"
EUROHOOPS_FEED = "https://www.eurohoops.net/en/category/euroleague/feed/"
ESPN_NBA_FEED = "https://www.espn.com/espn/rss/nba/news"
MAX_SOURCE_CHARS = 6_000

# USD per 1M tokens (input, cached input, cache write, output):
# developers.openai.com/api/docs/pricing
OPENAI_PRICES = {"gpt-6-sol": (2.00, 0.20, 2.50, 10.00)}
REASONING_EFFORT = "low"
MAX_OUTPUT_ESTIMATE = 3_000

VOICE_MODEL = "eleven_v3"
AUDIO_FORMAT = "mp3_44100_128"
SEED = 7
V3_USD_PER_1K_CHARS = 0.10
# Loudness per Apple Podcasts' audio requirements: -16 LKFS +/- 1 dB, true peak <= -1 dBFS.
LEAD_IN_SECONDS = 0.5
GAP_SECONDS = 0.4
TAIL_SECONDS = 1.0
TARGET_LUFS = -16
TRUE_PEAK_DB = -1.5

PROBE = [
    ("host", "Final score in Barcelona: 89–82."),
    ("host", "Final score in Barcelona: 89 to 82."),
    ("analyst", "Žalgiris and Fenerbahçe both looked sharp."),
]

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
SCORE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")


class Turn(BaseModel):
    speaker: Literal["host", "analyst"]
    text: str
    source_ids: list[str]


class Segment(BaseModel):
    title: str
    turns: list[Turn]


class Script(BaseModel):
    segments: list[Segment]


INSTRUCTIONS = """\
You write the script of "Hoops Daily", a short daily basketball news podcast with two hosts.
- George (speaker "host") leads: he introduces each story and gives the key fact.
- Sarah (speaker "analyst") adds context, an opinion or a question.
The tone is casual and analytical, like two friends who know the game.

Length: about 30 seconds of audio, so 450 to 550 characters of spoken text in total.
Structure: exactly 3 segments.
1. "Cold open": hook with the strongest story, then a one-line welcome to Hoops Daily.
2. "EuroLeague": the round's standout results and one story.
3. "NBA and sign-off": one NBA story, then a goodbye that says what comes next.

Write for the ear: sentences under 20 words, one idea and at most one number per sentence,
the role before the name ("Real Madrid coach ..."), and contractions. Keep turns short and
never put two long turns in a row.

Facts: use only facts from the sources. A turn that states a fact lists the ids of its sources
in source_ids; any other turn has an empty list. Write numbers in digits, and scores winner
first with an en dash ("89–82").

Voice tags: at most 2 in the whole script, chosen from [excited], [laughs], [curious] and
[sarcastic], at the start of a turn's text. No other markup.
"""


def save(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load(name: str) -> dict:
    path = OUT / name
    if not path.exists():
        sys.exit(f"{path} not found: run the previous stage first")
    return json.loads(path.read_text(encoding="utf-8"))


def http_get(url: str) -> httpx.Response:
    response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response


def require_key(secret: SecretStr | None, name: str) -> str:
    if secret is None:
        sys.exit(f"{name} is not set: add it to .env")
    return secret.get_secret_value()


def spoken_date(moment: datetime) -> str:
    return f"{moment:%A} {moment.day} {moment:%B}"


def fetch_euroleague() -> list[dict]:
    games = http_get(EUROLEAGUE_GAMES).json()["data"]
    last_round = max(game["round"] for game in games if game["played"])
    played = [game for game in games if game["round"] == last_round and game["played"]]
    upcoming = [game for game in games if game["round"] == last_round + 1]

    lines = []
    for game in played:
        home, away = game["local"], game["road"]
        winner, loser = (home, away) if home["score"] > away["score"] else (away, home)
        lines.append(
            f"{winner['club']['abbreviatedName']} beat {loser['club']['abbreviatedName']} "
            f"{winner['score']}–{loser['score']} (home team: {home['club']['abbreviatedName']})."
        )

    played_days = sorted({datetime.fromisoformat(game["utcDate"]) for game in played})
    next_days = sorted({datetime.fromisoformat(game["utcDate"]).date() for game in upcoming})
    first_day, last_day = played_days[0], played_days[-1]
    return [
        {
            "id": "S1",
            "title": f"EuroLeague Round {last_round} results, official EuroLeague API "
            f"({spoken_date(first_day)} to {spoken_date(last_day)})",
            "url": EUROLEAGUE_GAMES,
            "text": "\n".join(lines),
        },
        {
            "id": "CTX",
            "title": "Episode context",
            "url": None,
            "text": f"Today is {spoken_date(datetime.now(UTC))}. EuroLeague Round "
            f"{last_round + 1} is played on {' and '.join(map(spoken_date, next_days))}.",
        },
    ]


def fetch_article(source_id: str, feed_url: str) -> dict:
    feed = feedparser.parse(http_get(feed_url).content)
    entry = max(feed.entries, key=lambda item: item.published_parsed)
    html = entry.content[0].value if "content" in entry else http_get(entry.link).text
    text = trafilatura.extract(html) or ""
    return {
        "id": source_id,
        "title": entry.title,
        "url": entry.link,
        "published": entry.published,
        "text": text[:MAX_SOURCE_CHARS],
    }


def stage_fetch() -> None:
    start = time.perf_counter()
    sources = [
        *fetch_euroleague(),
        fetch_article("S2", EUROHOOPS_FEED),
        fetch_article("S3", ESPN_NBA_FEED),
    ]
    seconds = round(time.perf_counter() - start, 2)
    save(
        "sources.json",
        {"fetched_at": datetime.now(UTC).isoformat(), "seconds": seconds, "sources": sources},
    )
    for source in sources:
        print(f"{source['id']:>3}  {len(source['text']):>5} chars  {source['title']}")
    print(f"fetch: {seconds} s")


def sources_prompt(sources: list[dict]) -> str:
    return "\n\n".join(f"[{s['id']}] {s['title']}\n{s['text']}" for s in sources)


# Assumes cached and cache-written tokens are both counted in input_tokens (the upper bound).
def openai_cost(model: str, usage: ResponseUsage) -> float:
    price_in, price_cached, price_write, price_out = OPENAI_PRICES[model]
    cached = usage.input_tokens_details.cached_tokens
    written = usage.input_tokens_details.cache_write_tokens
    return (
        (usage.input_tokens - cached - written) * price_in
        + cached * price_cached
        + written * price_write
        + usage.output_tokens * price_out
    ) / 1_000_000


def report_script(script: dict, sources: list[dict]) -> None:
    texts = {source["id"]: source["text"] for source in sources}
    for segment in script["segments"]:
        chars = sum(len(turn["text"]) for turn in segment["turns"])
        print(f"\n## {segment['title']} ({chars} chars)")
        for turn in segment["turns"]:
            print(f"  {turn['speaker']:>7}: {turn['text']}  {turn['source_ids']}")
            cited = " ".join(texts.get(source_id, "") for source_id in turn["source_ids"])
            missing = set(NUMBER.findall(turn["text"])) - set(NUMBER.findall(cited))
            unknown = [source_id for source_id in turn["source_ids"] if source_id not in texts]
            if missing or unknown:
                print(
                    f"           ! not in cited sources: numbers {sorted(missing)}, ids {unknown}"
                )


def stage_write(dry_run: bool) -> None:
    settings = get_settings()
    sources = load("sources.json")["sources"]
    prompt = sources_prompt(sources)
    model = settings.openai_write_model
    _, _, price_write, price_out = OPENAI_PRICES[model]

    input_estimate = (len(INSTRUCTIONS) + len(prompt)) // 4
    cost_estimate = (input_estimate * price_write + MAX_OUTPUT_ESTIMATE * price_out) / 1_000_000
    print(f"{model}: ~{input_estimate} input tokens, at most ~${cost_estimate:.3f}")
    if dry_run:
        return

    client = OpenAI(api_key=require_key(settings.openai_api_key, "OPENAI_API_KEY"))
    start = time.perf_counter()
    response = client.responses.parse(
        model=model,
        instructions=INSTRUCTIONS,
        input=prompt,
        text_format=Script,
        reasoning={"effort": REASONING_EFFORT},
    )
    seconds = round(time.perf_counter() - start, 2)
    if response.output_parsed is None:
        sys.exit(f"No script returned (status: {response.status})")

    script = response.output_parsed.model_dump()
    cost = openai_cost(model, response.usage)
    save(
        "script.json",
        {
            "model": model,
            "reasoning_effort": REASONING_EFFORT,
            "seconds": seconds,
            "usage": response.usage.model_dump(),
            "cost_usd": round(cost, 4),
            "script": script,
        },
    )
    report_script(script, sources)
    usage = response.usage
    print(
        f"\nwrite: {seconds} s · {usage.input_tokens} in / {usage.output_tokens} out "
        f"({usage.output_tokens_details.reasoning_tokens} reasoning) · ${cost:.4f}"
    )


def speakable(text: str) -> str:
    return SCORE.sub(r"\1 to \2", text)


def voice_requests(script: dict, voices: dict[str, str]) -> list[dict]:
    requests = [
        {
            "name": f"segment_{number}",
            "inputs": [
                {"text": speakable(turn["text"]), "voice_id": voices[turn["speaker"]]}
                for turn in segment["turns"]
            ],
        }
        for number, segment in enumerate(script["segments"], start=1)
    ]
    probe = [{"text": text, "voice_id": voices[speaker]} for speaker, text in PROBE]
    requests.append({"name": "probe", "inputs": probe})
    return requests


def cache_key(inputs: list[dict]) -> str:
    payload = json.dumps([VOICE_MODEL, AUDIO_FORMAT, SEED, inputs], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return round(float(result.stdout), 2)


def synthesize(client: ElevenLabs, inputs: list[dict]) -> tuple[bytes, dict]:
    start = time.perf_counter()
    with client.text_to_dialogue.with_raw_response.convert(
        inputs=[DialogueInput(**turn) for turn in inputs],
        model_id=VOICE_MODEL,
        output_format=AUDIO_FORMAT,
        seed=SEED,
    ) as response:
        audio = b"".join(response.data)
        headers = response.headers
    return audio, {
        "seconds": round(time.perf_counter() - start, 2),
        "character_cost": int(headers["character-cost"]),
        "tts_latency_ms": int(headers["tts-latency-ms"]),
    }


def stage_voice(dry_run: bool) -> None:
    settings = get_settings()
    voices = {
        "host": settings.elevenlabs_host_voice_id,
        "analyst": settings.elevenlabs_analyst_voice_id,
    }
    requests = voice_requests(load("script.json")["script"], voices)
    cache = OUT / "voice"

    to_pay = 0
    for request in requests:
        request["key"] = cache_key(request["inputs"])
        request["chars"] = sum(len(turn["text"]) for turn in request["inputs"])
        cached = (cache / f"{request['key']}.mp3").exists()
        to_pay += 0 if cached else request["chars"]
        print(f"{request['name']}: {request['chars']} chars{' (cached)' if cached else ''}")
        for turn in request["inputs"]:
            print(f"    {turn['text']}")
    print(f"to pay: {to_pay} chars, about ${to_pay * V3_USD_PER_1K_CHARS / 1000:.3f}")
    if dry_run:
        return

    client = ElevenLabs(api_key=require_key(settings.elevenlabs_api_key, "ELEVENLABS_API_KEY"))
    cache.mkdir(parents=True, exist_ok=True)
    for request in requests:
        audio_path = cache / f"{request['key']}.mp3"
        meta_path = cache / f"{request['key']}.json"
        if not audio_path.exists():
            audio, meta = synthesize(client, request["inputs"])
            audio_path.write_bytes(audio)
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
        request |= json.loads(meta_path.read_text(encoding="utf-8"))
        request["duration"] = duration(audio_path)
        request["chars_per_second"] = round(request["chars"] / request["duration"], 1)
        print(
            f"{request['name']}: {request['chars']} sent · {request['character_cost']} billed · "
            f"{request['seconds']} s ({request['tts_latency_ms']} ms first byte) · "
            f"{request['duration']} s of audio · {request['chars_per_second']} chars/s"
        )
    save("voice.json", {"requests": requests})


def loudness(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", result.stderr)[-1])


def stage_master() -> None:
    segments = [r for r in load("voice.json")["requests"] if r["name"].startswith("segment")]
    files = [OUT / "voice" / f"{segment['key']}.mp3" for segment in segments]
    count = len(files)

    pads = "".join(f"[{i}:a]apad=pad_dur={GAP_SECONDS}[a{i}];" for i in range(count - 1))
    chain = "".join(f"[a{i}]" for i in range(count - 1)) + f"[{count - 1}:a]"
    graph = (
        f"{pads}{chain}concat=n={count}:v=0:a=1,"
        f"adelay=delays={int(LEAD_IN_SECONDS * 1000)}:all=1,apad=pad_dur={TAIL_SECONDS},"
        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DB}:LRA=11[out]"
    )
    output = OUT / "spike.mp3"
    inputs = [argument for file in files for argument in ("-i", file)]

    # loudnorm resamples to 192 kHz internally, so the output rate is set explicitly.
    start = time.perf_counter()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            graph,
            "-map",
            "[out]",
            "-ar",
            "44100",
            "-b:a",
            "128k",
            output,
        ],
        check=True,
    )
    seconds = round(time.perf_counter() - start, 2)

    starts, position = [], LEAD_IN_SECONDS
    for segment in segments:
        starts.append(round(position, 2))
        position += segment["duration"] + GAP_SECONDS

    result = {
        "seconds": seconds,
        "duration": duration(output),
        "loudness_lufs": loudness(output),
        "segment_loudness_lufs": [loudness(file) for file in files],
        "segment_starts": starts,
    }
    save("master.json", result)
    print(json.dumps(result, indent=2))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("stage", choices=["fetch", "write", "voice", "master"])
    parser.add_argument(
        "--dry-run", action="store_true", help="show what a paid stage would send, and stop"
    )
    args = parser.parse_args()
    if args.stage == "fetch":
        stage_fetch()
    elif args.stage == "write":
        stage_write(args.dry_run)
    elif args.stage == "voice":
        stage_voice(args.dry_run)
    else:
        stage_master()


if __name__ == "__main__":
    main()
