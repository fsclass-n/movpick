"""완성본 검사: 형식 · 장면별 음성 · 깜박임(프레임 밝기) · 주요 프레임 추출

    .venv/Scripts/python docs/video/tools/check_final.py
"""

import json
import re

from common import BUILD, VIDEO, run, scene_starts
from video_scenes import FPS, SCENES, TOTAL

FINAL = VIDEO / "movpick_final.mp4"


def streams() -> None:
    res = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_name,profile,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels:stream_tags=language:format=duration,size",
               "-of", "json", FINAL])
    info = json.loads(res.stdout)
    v = next(s for s in info["streams"] if s.get("width"))
    a = next(s for s in info["streams"] if s.get("sample_rate"))
    dur, size = float(info["format"]["duration"]), int(info["format"]["size"]) / 1e6
    print(f"video {v['codec_name']} {v.get('profile')} {v['width']}x{v['height']} r={v['r_frame_rate']} avg={v['avg_frame_rate']}")
    print(f"audio {a['codec_name']} {a['sample_rate']}Hz ch={a['channels']} lang={a.get('tags', {}).get('language')}")
    print(f"duration {dur:.3f}s  size {size:.1f}MB")
    assert v["codec_name"] == "h264" and v["width"] == 1920 and v["height"] == 1080 and v["avg_frame_rate"] == "30/1"
    assert a["codec_name"] == "aac" and a["channels"] == 2 and a["sample_rate"] == "48000"
    assert abs(dur - TOTAL) < 0.05 and size <= 95


def audio_levels() -> None:
    starts, quiet = scene_starts(SCENES), []
    for s in SCENES:
        res = run(["ffmpeg", "-ss", starts[s["id"]] + 0.3, "-t", s["dur"] - 0.6, "-i", FINAL, "-vn", "-af", "volumedetect", "-f", "null", "-"])
        mean = float(re.search(r"mean_volume: (-?[\d.]+) dB", res.stderr).group(1))
        if mean < -35:
            quiet.append((s["id"], mean))
    print(f"audio: {len(SCENES)} scenes checked, quiet(<-35dB): {quiet or 'none'}")
    assert not quiet


def flicker() -> None:
    res = run(["ffmpeg", "-i", FINAL, "-vf", "scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
               "-an", "-f", "null", "-"])
    y = [float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", res.stdout)]
    starts = sorted(scene_starts(SCENES).values())
    fades = set()
    for s in SCENES:
        st = scene_starts(SCENES)[s["id"]]
        for t in range(int((st - 0.6) * FPS), int((st + 0.6) * FPS)):  # 장면 전환 ±0.6초 제외
            fades.add(t)
    spikes = [i for i in range(1, len(y) - 1)
              if i not in fades and (y[i] - y[i - 1]) * (y[i + 1] - y[i]) < 0 and min(abs(y[i] - y[i - 1]), abs(y[i + 1] - y[i])) >= 4]
    print(f"flicker: {len(y)} frames, single-frame spikes outside transitions: {len(spikes)} {[round(i / FPS, 2) for i in spikes[:10]]}")
    _ = starts


def frames(points) -> None:
    out = BUILD / "check"
    out.mkdir(exist_ok=True)
    for name, t in points:
        run(["ffmpeg", "-y", "-ss", t, "-i", FINAL, "-frames:v", 1, out / f"{name}.png"])
    print("frames:", ", ".join(n for n, _ in points))


if __name__ == "__main__":
    streams()
    audio_levels()
    flicker()
    st = scene_starts(SCENES)
    frames([("slide04", st["p04"] + 10), ("d01", st["d01"] + 20), ("d04", st["d04"] + 14), ("d06", st["d06"] + 6),
            ("d08", st["d08"] + 10), ("d10", st["d10"] + 12), ("d12", st["d12"] + 20), ("d14", st["d14"] + 19),
            ("c00", st["c00"] + 8), ("d16", st["d16"] + 6), ("e16", st["e16"] + 8)])
