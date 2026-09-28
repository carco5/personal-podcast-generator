import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.pipeline import audio, master
from app.pipeline.common import PaidCall, Run, StageFailed
from app.pipeline.master import master_episode
from app.pipeline.script import Script
from app.pipeline.voice import (
    MAX_REQUEST_CHARS,
    ElevenLabsVoice,
    Line,
    ToneVoice,
    cache_path,
    speakable,
    voice_requests,
    voice_script,
)
from tests.fakes import make_listener, make_run
from tests.test_pipeline_checks import GOOD

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
VOICES = {"host": "george", "analyst": "sarah"}


class BrokenVoice(ToneVoice):
    def __init__(self, fault: str, bad: int) -> None:
        self.fault, self.bad = fault, bad

    def synthesize(self, lines: Sequence[Line]) -> tuple[bytes, PaidCall]:
        if self.bad == 0:
            return super().synthesize(lines)
        self.bad -= 1
        chars = sum(len(line.text) for line in lines)
        shortened = [Line(line.text[: len(line.text) // 3], line.voice_id) for line in lines]
        data, _ = super().synthesize(shortened)
        if self.fault == "silent":
            data = silence(chars)
        return data, PaidCall("elevenlabs", self.model, 0.0, 0, characters=chars)


def silence(chars: int) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "silence.mp3"
        seconds = str(chars / 12.4)
        audio.run("ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", seconds, path)
        return path.read_bytes()


def voiced_run(session: Session, tmp_path: Path, voice: ToneVoice | None = None) -> Run:
    user, podcast, interests = make_listener(session, [("euroleague", "high")])
    run = make_run(session, user, podcast, interests, voice=voice)
    run.config.data_dir = tmp_path
    run.episode.script = GOOD
    return run


def test_scores_are_made_speakable() -> None:
    assert speakable("They won 89–82 – a big night.") == "They won 89 to 82, a big night."


def test_one_request_per_segment_split_between_turns() -> None:
    script = Script.model_validate(GOOD)
    long_turn = script.segments[1].turns[0].model_copy(update={"text": "A long line. " * 38})
    script.segments[1].turns = [long_turn] * 5

    requests = voice_requests(script, VOICES)

    assert [r.segment for r in requests] == ["intro", "euroleague", "euroleague", "closing"]
    assert [len(r.lines) for r in requests] == [2, 4, 1, 1]
    assert all(r.chars <= MAX_REQUEST_CHARS for r in requests)


def test_cache_key_includes_the_voice_model(tmp_path: Path) -> None:
    request = voice_requests(Script.model_validate(GOOD), VOICES)[0]

    assert cache_path(tmp_path, ToneVoice.model, request) != cache_path(
        tmp_path, ElevenLabsVoice.model, request
    )


def test_voice_uses_the_cache(session: Session, tmp_path: Path) -> None:
    run = voiced_run(session, tmp_path)

    first = voice_script(run)
    run.calls.clear()
    second = voice_script(run)

    assert first["generated_characters"] > 0 and not any(r["cached"] for r in first["requests"])
    assert second["generated_characters"] == 0 and all(r["cached"] for r in second["requests"])


@pytest.mark.parametrize(
    ("fault", "reason"), [("short", "was cut short"), ("silent", "was silent")]
)
def test_a_bad_chunk_fails_after_one_retry(
    session: Session, tmp_path: Path, fault: str, reason: str
) -> None:
    run = voiced_run(session, tmp_path, BrokenVoice(fault, bad=2))

    with pytest.raises(StageFailed, match=f"intro chunk {reason} twice"):
        voice_script(run)


@pytest.mark.parametrize("fault", ["short", "silent"])
def test_one_bad_chunk_is_fixed_by_the_retry(session: Session, tmp_path: Path, fault: str) -> None:
    run = voiced_run(session, tmp_path, BrokenVoice(fault, bad=1))

    report = voice_script(run)

    assert len(run.calls) == len(report["requests"]) + 1


def test_master_joins_normalises_and_marks_chapters(session: Session, tmp_path: Path) -> None:
    run = voiced_run(session, tmp_path)
    report = voice_script(run)["requests"]

    result = master_episode(run)

    assert abs(result["loudness_lufs"] + 16) <= 1 and result["true_peak_dbfs"] <= -1
    expected = 0.5 + sum(r["seconds"] for r in report) + 0.4 * (len(report) - 1) + 1.0
    assert abs(result["duration_seconds"] - expected) < 0.3
    starts = [chapter["start"] for chapter in result["chapters"]]
    assert [c["key"] for c in result["chapters"]] == ["intro", "euroleague", "closing"]
    assert starts[0] == 0.5 and starts[1] == round(0.5 + report[0]["seconds"] + 0.4, 2)
    assert (tmp_path / result["audio_path"]).exists()


def test_master_fails_on_missing_chunks_or_bad_loudness(
    session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = voiced_run(session, tmp_path)
    with pytest.raises(StageFailed, match="voice chunks are missing"):
        master_episode(run)

    voice_script(run)
    monkeypatch.setattr(master.audio, "loudness", lambda path: (-20.0, -3.0))
    with pytest.raises(StageFailed, match="loudness -20.0 LUFS"):
        master_episode(run)
