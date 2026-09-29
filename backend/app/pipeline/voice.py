import hashlib
import json
import re
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from elevenlabs import DialogueInput, ElevenLabs
from pydantic import SecretStr

from app.pipeline import audio
from app.pipeline.checks import SCORE
from app.pipeline.common import PaidCall, Run, StageFailed
from app.pipeline.script import Script
from app.pipeline.selection import CHARS_PER_SECOND

VOICE_MODEL = "eleven_v3"
AUDIO_FORMAT = "mp3_44100_128"
SEED = 7
USD_PER_1K_CHARS = 0.10
MAX_REQUEST_CHARS = 2_000
MAX_CHARS_PER_SECOND = CHARS_PER_SECOND * 1.5
SILENT_DB = -45.0


@dataclass(frozen=True)
class Line:
    text: str
    voice_id: str


@dataclass(frozen=True)
class Request:
    segment: str
    lines: tuple[Line, ...]

    @property
    def chars(self) -> int:
        return sum(len(line.text) for line in self.lines)


class Voice(Protocol):
    model: str

    def synthesize(self, lines: Sequence[Line]) -> tuple[bytes, PaidCall | None]: ...


class ElevenLabsVoice:
    """ElevenLabs text-to-dialogue with eleven_v3, as validated in the Step 3 spike."""

    model = VOICE_MODEL

    def __init__(self, api_key: SecretStr) -> None:
        self._client = ElevenLabs(api_key=api_key.get_secret_value())

    def synthesize(self, lines: Sequence[Line]) -> tuple[bytes, PaidCall]:
        start = time.perf_counter()
        with self._client.text_to_dialogue.with_raw_response.convert(
            inputs=[DialogueInput(text=line.text, voice_id=line.voice_id) for line in lines],
            model_id=self.model,
            output_format=AUDIO_FORMAT,
            seed=SEED,
        ) as response:
            data = b"".join(response.data)
            billed = int(response.headers.get("character-cost", sum(len(l.text) for l in lines)))
        call = PaidCall(
            provider="elevenlabs",
            model=self.model,
            cost_usd=billed * USD_PER_1K_CHARS / 1000,
            latency_ms=round((time.perf_counter() - start) * 1000),
            characters=billed,
        )
        return data, call


class ToneVoice:
    """Free development voice: a tone as long as the real speech would be."""

    model = "tone-for-development"

    def synthesize(self, lines: Sequence[Line]) -> tuple[bytes, PaidCall | None]:
        chars = sum(len(line.text) for line in lines)
        seconds = round(chars / CHARS_PER_SECOND, 2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tone.mp3"
            audio.run(
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:sample_rate=44100",
                "-t",
                str(seconds),
                "-af",
                "volume=0.25",
                "-ac",
                "1",
                "-b:a",
                "128k",
                path,
            )
            data = path.read_bytes()
        return data, None


SEASON_SLASH = re.compile(r"\b(\d{4})/(\d{2})\b")
NAME_SLASH = re.compile(r"(?<=[^\W\d_])/(?=[^\W\d_])")
PRONUNCIATIONS = {
    "Bodø/Glimt": "Bodo Glimt",
    "iLERNA Lleida": "Lleida",
    "iLERNA": "Lleida",
}
PRONOUNCED = re.compile(
    r"\b(" + "|".join(map(re.escape, sorted(PRONUNCIATIONS, key=len, reverse=True))) + r")(?!\w)"
)
GOALS = ["nil", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
GOALS += ["eleven", "twelve", "thirteen", "fourteen", "fifteen"]


def spoken_pair(match: re.Match[str]) -> str:
    first, second = match.groups()
    if len(first) == 4 and len(second) == 2:
        return f"{first}-{second}"
    a, b = int(first), int(second)
    if a < len(GOALS) and b < len(GOALS):
        if a == b:
            return "nil-nil" if a == 0 else f"{GOALS[a]}-all"
        return f"{GOALS[a]}-{GOALS[b]}"
    return f"{first} to {second}"


def speakable(text: str) -> str:
    text = PRONOUNCED.sub(lambda match: PRONUNCIATIONS[match.group(1)], text)
    text = NAME_SLASH.sub(" ", SEASON_SLASH.sub(r"\1-\2", text))
    return SCORE.sub(spoken_pair, text).replace(" – ", ", ").replace(" & ", " and ")


def voice_requests(script: Script, voices: dict[str, str]) -> list[Request]:
    requests: list[Request] = []
    for segment in script.segments:
        lines: list[Line] = []
        for turn in segment.turns:
            line = Line(speakable(turn.text), voices[turn.speaker])
            if lines and sum(len(x.text) for x in lines) + len(line.text) > MAX_REQUEST_CHARS:
                requests.append(Request(segment.key, tuple(lines)))
                lines = []
            lines.append(line)
        requests.append(Request(segment.key, tuple(lines)))
    return requests


def cache_path(data_dir: Path, model: str, request: Request) -> Path:
    lines = [[line.text, line.voice_id] for line in request.lines]
    payload = json.dumps([model, AUDIO_FORMAT, SEED, lines])
    return data_dir / "voice" / f"{hashlib.sha256(payload.encode()).hexdigest()[:24]}.mp3"


def voices(run: Run) -> dict[str, str]:
    config = run.config
    return {"host": config.elevenlabs_host_voice_id, "analyst": config.elevenlabs_analyst_voice_id}


def voice_script(run: Run) -> dict:
    script = Script.model_validate(run.episode.script)
    report = []
    generated = 0
    for request in voice_requests(script, voices(run)):
        path = cache_path(run.config.data_dir, run.voice.model, request)
        cached = path.exists()
        if not cached:
            path.parent.mkdir(parents=True, exist_ok=True)
            for attempt in (1, 2):
                data, call = run.voice.synthesize(request.lines)
                generated += request.chars
                if call is not None:
                    run.calls.append(call)
                path.write_bytes(data)
                problem = chunk_problem(path, request.chars)
                if problem is None:
                    break
                path.unlink()
                if attempt == 2:
                    raise StageFailed(f"voice: a {request.segment} chunk {problem} twice")
        report.append(
            {
                "segment": request.segment,
                "chars": request.chars,
                "seconds": audio.duration(path),
                "cached": cached,
            }
        )
    return {
        "voice": run.voice.model,
        "requests": report,
        "generated_characters": generated,
        "billed_characters": sum(call.characters or 0 for call in run.calls),
        "reused_characters": sum(r["chars"] for r in report if r["cached"]),
        "cost_usd": round(sum(call.cost_usd for call in run.calls), 4),
    }


def chunk_problem(path: Path, chars: int) -> str | None:
    seconds = audio.duration(path)
    if seconds <= 0 or chars / seconds > MAX_CHARS_PER_SECOND:
        return "was cut short"
    if audio.mean_volume(path) < SILENT_DB:
        return "was silent"
    return None
