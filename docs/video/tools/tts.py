"""문장 단위 신경망 합성 → 자연스러운 쉼으로 장면 음성 생성.

    .venv/Scripts/python docs/video/tools/tts.py

- 문장마다 따로 합성하고 문장 사이에 0.35초(쉼표형 0.25초) 숨 쉬는 쉼을 넣는다.
- 장면 길이(dur - 0.6초)를 넘으면 그 장면만 속도를 조금씩 올려 다시 합성한다(최대 +12%).
- 결과: build/tts/<scene>.wav (48kHz 스테레오, 무보정), build/tts/timings.json (자막용 문장 시각)
  목소리 보정(저역 제거·압축·명료도·−16 LUFS)은 compose 단계에서 전체 트랙에 한 번에 적용한다.
"""

import asyncio
import hashlib
import sys

import edge_tts

from common import BUILD, duration, run, save_json, scene_starts
from video_scenes import PITCH, RATE, SCENES, VOICE

LEAD, GAP = 0.3, 0.35
OUT = BUILD / "tts"


async def synth(text: str, rate: str) -> str:
    key = hashlib.sha1(f"{VOICE}|{rate}|{PITCH}|{text}".encode()).hexdigest()[:16]
    mp3 = OUT / f"s_{key}.mp3"
    if not mp3.exists():
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, VOICE, rate=rate, pitch=PITCH).save(str(mp3))
                break
            except Exception as e:  # noqa: BLE001 - 네트워크 일시 오류 재시도
                if attempt == 3:
                    raise
                print("  retry", type(e).__name__, e)
                await asyncio.sleep(2 + attempt * 2)
    return str(mp3)


def pct(rate: str) -> int:
    return int(rate.replace("%", ""))


async def build_scene(scene) -> dict:
    budget = scene["dur"] - 0.6 - LEAD
    rate = RATE
    while True:
        parts = []
        for shown, spoken in scene["lines"]:
            mp3 = await synth(spoken or shown, rate)
            parts.append((shown, mp3, duration(mp3)))
        total = sum(d for *_, d in parts) + GAP * (len(parts) - 1)
        if total <= budget or pct(rate) >= 12:
            break
        need = int((total / budget - 1) * 100) + 2
        rate = f"{min(12, pct(rate) + max(2, need)):+d}%"
        print(f"  {scene['id']}: {total:.1f}s > {budget:.1f}s → rate {rate}")

    wav = OUT / f"{scene['id']}.wav"
    inputs, filters, t, cues = [], [], LEAD, []
    for i, (shown, mp3, d) in enumerate(parts):
        inputs += ["-i", mp3]
        delay = int(t * 1000)
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={delay}|{delay}[a{i}]")
        cues.append({"text": shown, "start": round(t, 3), "end": round(t + d, 3)})
        t += d + GAP
    mix = "".join(f"[a{i}]" for i in range(len(parts)))
    filters.append(f"{mix}amix=inputs={len(parts)}:normalize=0,apad,atrim=0:{scene['dur']}[out]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2", wav])
    speech = sum(d for *_, d in parts)
    if total > budget:
        print(f"  !! {scene['id']} 음성 {total:.1f}s 가 장면 {scene['dur']}s 에 비해 깁니다")
    return {"id": scene["id"], "wav": str(wav), "rate": rate, "speech": round(speech, 2), "cues": cues}


async def main(only=None) -> None:
    starts = scene_starts(SCENES)
    results = []
    for scene in SCENES:
        if only and scene["id"] not in only:
            continue
        r = await build_scene(scene)
        for c in r["cues"]:
            c["abs_start"] = round(starts[scene["id"]] + c["start"], 3)
            c["abs_end"] = round(starts[scene["id"]] + c["end"], 3)
        results.append(r)
        print(f"{scene['id']}  dur={scene['dur']:>3}s  speech={r['speech']:5.1f}s  rate={r['rate']}")
    if not only:
        save_json(OUT / "timings.json", results)
        print("total speech", round(sum(r["speech"] for r in results), 1), "s / 600 s")


if __name__ == "__main__":
    asyncio.run(main(set(sys.argv[1:]) or None))
