from pathlib import Path

from sqlalchemy import func, select

from app.models import ProviderCall, StageRun
from app.pipeline import audio
from app.pipeline.common import Run, StageFailed
from app.pipeline.script import Script
from app.pipeline.selection import CHARS_PER_SECOND
from app.pipeline.voice import Request, cache_path, voice_requests, voices

LEAD_IN_SECONDS = 0.5
GAP_SECONDS = 0.4
TAIL_SECONDS = 1.0
TARGET_LUFS = -16.0
TARGET_TRUE_PEAK = -1.5
LUFS_TOLERANCE = 1.0
MAX_TRUE_PEAK = -1.0


def master_episode(run: Run) -> dict:
    script = Script.model_validate(run.episode.script)
    requests = voice_requests(script, voices(run))
    files = [cache_path(run.config.data_dir, run.voice.model, r) for r in requests]
    missing = sum(not path.exists() for path in files)
    if missing:
        raise StageFailed(f"master: {missing} voice chunks are missing")
    relative = Path("episodes") / f"{run.episode.id}.mp3"
    output = run.config.data_dir / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    join(files, output)
    integrated, peak = audio.loudness(output)
    if abs(integrated - TARGET_LUFS) > LUFS_TOLERANCE or peak > MAX_TRUE_PEAK:
        raise StageFailed(f"master: loudness {integrated} LUFS, true peak {peak} dBFS")
    chapters: list[dict] = []
    start = LEAD_IN_SECONDS
    for request, path in zip(requests, files, strict=True):
        if not chapters or chapters[-1]["key"] != request.segment:
            chapters.append({"key": request.segment, "start": round(start, 2)})
        start += audio.duration(path) + GAP_SECONDS
    return {
        "audio_path": relative.as_posix(),
        "duration_seconds": audio.duration(output),
        "chapters": chapters,
        "loudness_lufs": integrated,
        "true_peak_dbfs": peak,
        "metrics": episode_metrics(run, script, requests, files),
    }


def episode_metrics(run: Run, script: Script, requests: list[Request], files: list[Path]) -> dict:
    spoken = sum(request.chars for request in requests)
    speech = sum(audio.duration(path) for path in files)
    calls = {
        provider: (count, float(cost or 0), characters or 0)
        for provider, count, cost, characters in run.session.execute(
            select(
                ProviderCall.provider,
                func.count(),
                func.sum(ProviderCall.cost_usd),
                func.sum(ProviderCall.characters),
            )
            .join(StageRun, StageRun.id == ProviderCall.stage_run_id)
            .where(StageRun.episode_id == run.episode.id)
            .group_by(ProviderCall.provider)
        ).all()
    }
    llm = calls.get("openai", (0, 0.0, 0))
    voice = calls.get("elevenlabs", (0, 0.0, 0))
    return {
        "planned_chars": (run.episode.plan or {}).get("target_chars"),
        "script_chars": sum(len(t.text) for s in script.segments for t in s.turns),
        "spoken_chars": spoken,
        "estimated_seconds": round(spoken / CHARS_PER_SECOND, 1),
        "speech_seconds": round(speech, 1),
        "chars_per_second": round(spoken / speech, 2) if speech else None,
        "llm_calls": llm[0],
        "llm_cost_usd": round(llm[1], 4),
        "voice_calls": voice[0],
        "voice_characters": voice[2],
        "voice_cost_usd": round(voice[1], 4),
    }


def join(files: list[Path], output: Path) -> None:
    count = len(files)
    pads = "".join(f"[{i}:a]apad=pad_dur={GAP_SECONDS}[a{i}];" for i in range(count - 1))
    chain = "".join(f"[a{i}]" for i in range(count - 1)) + f"[{count - 1}:a]"
    graph = (
        f"{pads}{chain}concat=n={count}:v=0:a=1,"
        f"adelay=delays={int(LEAD_IN_SECONDS * 1000)}:all=1,apad=pad_dur={TAIL_SECONDS},"
        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK}:LRA=11[out]"
    )
    inputs = [arg for path in files for arg in ("-i", str(path))]
    audio.run(
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-b:a",
        "128k",
        output,
    )
