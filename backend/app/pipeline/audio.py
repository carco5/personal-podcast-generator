import re
import subprocess
from pathlib import Path


def run(program: str, *args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [program, "-hide_banner", *map(str, args)], capture_output=True, text=True, check=True
    )


def duration(path: Path) -> float:
    result = run(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path
    )
    return round(float(result.stdout), 2)


def mean_volume(path: Path) -> float:
    result = run("ffmpeg", "-nostats", "-i", path, "-af", "volumedetect", "-f", "null", "-")
    return float(re.findall(r"mean_volume:\s+(-?[\d.]+) dB", result.stderr)[-1])


def loudness(path: Path) -> tuple[float, float]:
    result = run("ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-")
    integrated = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", result.stderr)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", result.stderr)[-1])
    return integrated, peak
