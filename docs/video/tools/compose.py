"""장면 합성 → movpick_final.mp4 (1920x1080, 30fps, H.264 + AAC 스테레오, ≤95MB)

    .venv/Scripts/python docs/video/tools/compose.py [--rebuild]

1) 장면별 클립: 슬라이드/정지 이미지 루프 또는 녹화 구간(대기 cuts 제거) → 프레임 단위(초×30) 길이 고정
2) 구간 라벨(슬라이드 오른쪽 위 · 시연 왼쪽 아래), 노란 안내 태그, 슬라이드 강조 테두리(0.3초 페이드)
3) 내레이션: 장면 음성 이어 붙이기 → 저역 제거·압축·명료도 보강 → −16 LUFS(2-pass loudnorm)
4) 자막: 한 줄 30자 이내로 나눠 ASS 로 화면에 입히고, SRT 별도 저장
5) 2-pass x264(평균 1100k, maxrate 3000k, 키프레임 5초) → 하이라이트(60초 ≤10MB) · 썸네일
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import BUILD, VIDEO, duration, load_json, run, scene_starts
from video_scenes import FPS, SCENES, TOTAL

CLIPS, OV = BUILD / "clips", BUILD / "overlays"
FONT_R, FONT_B = r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"
OUT = VIDEO / "movpick_final.mp4"
SRT = VIDEO / "movpick_final.srt"
HIGHLIGHT = VIDEO / "movpick_highlight.mp4"
THUMB = VIDEO / "video-thumbnail.png"
REBUILD = "--rebuild" in sys.argv
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS)]


# ----------------------------------------------------------------------------- overlay images
def pill(text: str, path: Path, fg, bg, size=26, bold=True, pad=(22, 10), border=None) -> Path:
    font = ImageFont.truetype(FONT_B if bold else FONT_R, size)
    l, t, r, b = font.getbbox(text)
    w, h = r - l + pad[0] * 2, b - t + pad[1] * 2
    im = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((2, 2, w + 1, h + 1), radius=h // 2, fill=bg, outline=border, width=2 if border else 0)
    d.text((2 + pad[0] - l, 2 + pad[1] - t), text, font=font, fill=fg)
    im.save(path)
    return path


def label_png(text: str) -> Path:
    path = OV / f"label_{hashlib.md5(text.encode()).hexdigest()[:12]}.png"
    return pill(text, path, (236, 235, 245, 255), (7, 7, 12, 200), 24, True, border=(255, 61, 87, 230))


def tag_png(text: str) -> Path:
    path = OV / f"tag_{hashlib.md5(text.encode()).hexdigest()[:12]}.png"
    return pill(text, path, (20, 16, 0, 255), (245, 197, 24, 240), 26, True)


def highlight_png(sid: str, rect) -> Path:
    x, y, w, h = rect
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, a in enumerate((60, 110, 255)):  # 은은한 광택 + 3px 테두리
        o = 6 - i * 2
        d.rounded_rectangle((x - o, y - o, x + w + o, y + h + o), radius=16, outline=(34, 211, 238, a), width=2 if i < 2 else 3)
    path = OV / f"hl_{sid}.png"
    im.save(path)
    return path


# ----------------------------------------------------------------------------- scene clips
def keep_intervals(mark) -> list:
    keep, cur = [], mark["start"]
    for a, b in sorted(mark["cuts"]):
        if a > cur:
            keep.append((cur, a))
        cur = max(cur, b)
    keep.append((cur, mark["end"]))
    return keep


def recordings() -> dict:
    out = {}
    for name in ("main", "docs", "health", "actions"):
        data = load_json(BUILD / "rec" / f"{name}.json")
        if data:
            for sid, mark in data["scenes"].items():
                out[sid] = (data, mark)
    return out


def frame_list(sid: str, data: dict, mark: dict) -> Path:
    """타임스탬프가 있는 스크린캐스트 프레임 → 구간별 정확한 표시 시간을 가진 ffconcat 목록."""
    base = Path(data["dir"])
    frames = data["frames"]
    lines, last = ["ffconcat version 1.0"], None
    for a, b in keep_intervals(mark):
        idx = [i for i, (t, _) in enumerate(frames) if t < b]
        if not idx:
            continue
        first = max([i for i in idx if frames[i][0] <= a] or [idx[0]])
        for i in range(first, idx[-1] + 1):
            t0 = max(frames[i][0], a)
            t1 = min(frames[i + 1][0] if i + 1 < len(frames) else b, b)
            if t1 - t0 <= 0.0005:
                continue
            last = (base / frames[i][1]).as_posix()
            lines += [f"file '{last}'", f"duration {t1 - t0:.4f}"]
    lines.append(f"file '{last}'")
    path = CLIPS / f"{sid}_frames.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_clip(scene, rec, fade_in: bool, fade_out: bool) -> Path:
    sid, dur = scene["id"], scene["dur"]
    frames = dur * FPS
    out = CLIPS / f"{sid}.mp4"
    if out.exists() and not REBUILD:
        return out
    inputs, chain = [], []
    if scene["kind"] in ("slide", "still"):
        img = BUILD / "slides" / f"slide{scene['ref']:02d}.png" if scene["kind"] == "slide" else OV / "compare.png"
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", img]
        chain.append(f"[0:v]scale=1920:1080,setsar=1,fps={FPS},format=yuv420p[base]")
    else:
        data, mark = rec[sid]
        inputs += ["-f", "concat", "-safe", "0", "-i", frame_list(sid, data, mark)]
        chain.append(f"[0:v]fps={FPS},scale=1920:1080,setsar=1,"
                     f"tpad=stop_mode=clone:stop_duration={dur},trim=end_frame={frames},setpts=PTS-STARTPTS,format=yuv420p[base]")
    last = "base"
    n = 1
    if scene["hl"]:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", highlight_png(sid, scene["hl"])]
        t_in = round(dur * 0.32, 2)
        chain.append(f"[{n}:v]format=rgba,fade=in:st={t_in}:d=0.3:alpha=1,fade=out:st={dur - 0.7}:d=0.3:alpha=1[h]")
        chain.append(f"[{last}][h]overlay=0:0[v{n}]")
        last, n = f"v{n}", n + 1
    on_slide = scene["kind"] == "slide"
    lab = label_png(scene["label"] if not on_slide else f"{scene['label']}  ·  {scene['ref']}/16")
    inputs += ["-i", lab]
    pos = "W-w-36:30" if on_slide else "36:H-h-34"
    chain.append(f"[{last}][{n}:v]overlay={pos}[v{n}]")
    last, n = f"v{n}", n + 1
    if scene["tag"]:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", tag_png(scene["tag"])]
        chain.append(f"[{n}:v]format=rgba,fade=in:st=0.3:d=0.3:alpha=1[t]")
        chain.append(f"[{last}][t]overlay=W-w-36:H-h-118[v{n}]")
        last, n = f"v{n}", n + 1
    fades = []
    if fade_in:
        fades.append("fade=in:st=0:d=0.45")
    if fade_out:
        fades.append(f"fade=out:st={dur - 0.5}:d=0.5")
    chain.append(f"[{last}]{','.join(fades) or 'null'},trim=end_frame={frames}[out]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[out]", "-frames:v", frames, *X264, "-an", out])
    got = round(duration(out) * FPS)
    assert abs(got - frames) <= 1, (sid, got, frames)
    return out


def build_video() -> Path:
    rec = recordings()
    missing = [s["id"] for s in SCENES if s["kind"] == "demo" and s["id"] not in rec]
    if missing:
        raise SystemExit(f"녹화되지 않은 장면: {missing} (record_demo.py 실행)")
    ids = [s["id"] for s in SCENES]
    lst = []
    for i, s in enumerate(SCENES):
        nxt = SCENES[i + 1] if i + 1 < len(SCENES) else None
        prv = SCENES[i - 1] if i else None
        fin = s["fade_in"] or (prv is not None and prv["fade_out"])
        fout = s["fade_out"] or (nxt is not None and nxt["fade_in"])
        clip = build_clip(s, rec, fin, fout)
        lst.append(f"file '{clip.as_posix()}'")
        print(f"  clip {s['id']} ({ids.index(s['id']) + 1}/{len(ids)})")
    (BUILD / "concat.txt").write_text("\n".join(lst), encoding="utf-8")
    master = BUILD / "video_master.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", BUILD / "concat.txt", "-c", "copy", master])
    return master


# ----------------------------------------------------------------------------- narration
def build_audio() -> Path:
    out = BUILD / "narration.wav"
    tj = BUILD / "tts" / "timings.json"
    if out.exists() and out.stat().st_mtime > tj.stat().st_mtime and "--rebuild-audio" not in sys.argv:
        print("  narration: reuse", out.name)
        return out
    timings = {t["id"]: t for t in load_json(tj)}
    inputs, labels = [], []
    for i, s in enumerate(SCENES):
        inputs += ["-i", timings[s["id"]]["wav"]]
        labels.append(f"[{i}:a]atrim=0:{s['dur']},apad=whole_dur={s['dur']},asetpts=PTS-STARTPTS[a{i}]")
    raw = BUILD / "narration_raw.wav"
    graph = ";".join(labels) + ";" + "".join(f"[a{i}]" for i in range(len(SCENES))) + f"concat=n={len(SCENES)}:v=0:a=1[out]"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-ac", "2", raw])
    voice = "highpass=f=80,acompressor=threshold=-21dB:ratio=2.5:attack=8:release=120:makeup=2,equalizer=f=3000:t=q:w=1.2:g=2.5"
    res = run(["ffmpeg", "-y", "-i", raw, "-af", f"{voice},loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    stats = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S).group(0))
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
          f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-i", raw, "-af", f"{voice},{ln}", "-ar", "48000", "-ac", "2", out])
    return out


# ----------------------------------------------------------------------------- subtitles
def chunks(text: str, limit: int = 30) -> list:
    if len(text) <= limit:
        return [text]
    words, out, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > limit:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    out.append(cur)
    # 너무 짧은 마지막 조각은 앞에 붙이기
    if len(out) > 1 and len(out[-1]) < 6:
        out[-2] = f"{out[-2]} {out[-1]}"
        out.pop()
    return out


def cues() -> list:
    starts = scene_starts(SCENES)
    items = []
    for t in load_json(BUILD / "tts" / "timings.json"):
        base = starts[t["id"]]
        for c in t["cues"]:
            parts = chunks(c["text"])
            total = sum(len(p) for p in parts)
            a = base + c["start"]
            span = c["end"] - c["start"]
            for p in parts:
                b = a + span * len(p) / total
                items.append((a, b + (0.25 if p is parts[-1] else 0.0), p))
                a = b
    return items


def ts(sec: float, sep=",") -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", sep) if sep == "," else f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_subtitles(items) -> Path:
    SRT.write_text("\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(items, 1)), encoding="utf-8")
    ass = BUILD / "subs.ass"
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Malgun Gothic,36,&H00FFFFFF,&H00FFFFFF,&H6A000000,&H00000000,-1,0,0,0,100,100,0,0,3,10,0,2,320,320,26,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "\n".join(f"Dialogue: 0,{ts(a, '.')},{ts(min(b, TOTAL), '.')},Sub,,0,0,0,,{t}" for a, b, t in items)
    ass.write_text(head + body + "\n", encoding="utf-8-sig")
    return ass


# ----------------------------------------------------------------------------- final encode
def encode(master: Path, audio: Path, ass: Path) -> None:
    vf = f"subtitles={ass.name}:fontsdir=C\\\\:/Windows/Fonts"
    common = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
              "-b:v", "1100k", "-maxrate", "3000k", "-bufsize", "6000k", "-x264-params", "keyint=150:min-keyint=30:scenecut=0"]
    cwd_args = {"cwd": str(BUILD)}
    import subprocess
    from common import FFMPEG
    p1 = [FFMPEG, "-hide_banner", "-nostats", "-y", "-i", str(master), "-vf", vf, *common, "-pass", "1", "-passlogfile", "x264pass", "-an", "-f", "mp4", "NUL"]
    p2 = [FFMPEG, "-hide_banner", "-nostats", "-y", "-i", str(master), "-i", str(audio), "-vf", vf, *common, "-pass", "2", "-passlogfile", "x264pass",
          "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
          "-metadata:s:a:0", "language=kor", "-metadata", "title=movpick 10분 발표·시연", "-t", str(TOTAL),
          "-movflags", "+faststart", str(OUT)]
    for cmd in (p1, p2):
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **cwd_args)
        if res.returncode:
            raise RuntimeError(res.stderr[-2000:])
    size = OUT.stat().st_size / 1e6
    print(f"  final: {OUT.name}  {duration(OUT):.2f}s  {size:.1f}MB")
    assert size <= 95, size


def extras() -> None:
    starts = scene_starts(SCENES)
    hs = starts["d04"]
    run(["ffmpeg", "-y", "-ss", hs, "-t", 60, "-i", OUT, "-vf", "scale=1280:-2", "-c:v", "libx264", "-preset", "slow",
         "-b:v", "1000k", "-maxrate", "2000k", "-bufsize", "4000k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", HIGHLIGHT])
    run(["ffmpeg", "-y", "-ss", starts["d06"] + 5, "-i", OUT, "-frames:v", 1, THUMB])
    print(f"  highlight: {HIGHLIGHT.stat().st_size / 1e6:.1f}MB from {hs // 60}:{hs % 60:02d}, thumbnail @ {starts['d06'] + 5}s")


if __name__ == "__main__":
    master = build_video()
    audio = build_audio()
    ass = write_subtitles(cues())
    encode(master, audio, ass)
    extras()
