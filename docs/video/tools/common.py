import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
VIDEO = TOOLS.parent
ROOT = VIDEO.parents[1]
BUILD = VIDEO / "build"
for sub in ("tts", "slides", "rec", "clips", "overlays"):
    (BUILD / sub).mkdir(parents=True, exist_ok=True)


def _find(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    pattern = os.path.expandvars(rf"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\{name}.exe")
    hits = glob.glob(pattern)
    if not hits:
        raise SystemExit(f"{name} 를 찾을 수 없습니다. (winget install Gyan.FFmpeg)")
    return hits[0]


FFMPEG, FFPROBE = _find("ffmpeg"), _find("ffprobe")


def run(args: list, quiet: bool = True) -> subprocess.CompletedProcess:
    cmd = [FFMPEG if args[0] == "ffmpeg" else FFPROBE if args[0] == "ffprobe" else args[0], *map(str, args[1:])]
    if args[0] == "ffmpeg":
        cmd[1:1] = ["-hide_banner", "-nostats"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)[:300]}\n{res.stderr[-1500:]}")
    if not quiet:
        print(res.stderr[-800:])
    return res


def duration(path) -> float:
    res = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(res.stdout.strip())


def load_json(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(path, data) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def scene_starts(scenes) -> dict:
    t, out = 0, {}
    for s in scenes:
        out[s["id"]] = t
        t += s["dur"]
    return out
