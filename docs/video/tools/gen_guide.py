"""영상 대본·연출 가이드 생성 → docs/video/영상_대본_및_연출가이드.md

    .venv/Scripts/python docs/video/tools/gen_guide.py
"""

from common import BUILD, VIDEO, load_json, scene_starts
from video_scenes import PITCH, RATE, SCENES, SHOWTIME_ID, TOTAL, VOICE

ACTIONS = {
    "d00": "홈(비로그인) 상단 회차 요약 강조 → 첫 영화 카드",
    "d01": "헤더 `로그인` → 오늘의 No.1 히어로 강조 → `회원가입` 탭 → 비밀번호 `Movpick2026!` 입력(규칙 체크리스트 초록 전환) → `로그인` 탭",
    "d02": "`일반 회원 테스트 로그인` (계정 자동 입력 애니메이션) → 홈 이동, 환영 토스트",
    "d03": "헤더 메뉴(상영작·알림 설정만) 강조 → 영화관 칩 `메가박스` → 검색 `투어스` → 영화 카드 펼침",
    "d04": f"회차(`/showtimes/{SHOWTIME_ID}`) 클릭 → 좌석 맵 강조 → 명당 좌석 → `명당 히트맵` 켜기/끄기 → 추천 좌석 → 하단 '추정값' 안내",
    "d05": "`명당 자리 전체 감시` → '감시를 시작했습니다' 토스트",
    "d06": "실제 WebSocket 취소표 알림 수신(대기 구간은 편집으로 제거) → 팝업 좌석 칩 · 토스트 강조 → `좌석 배치도`",
    "d07": "헤더 `알림 설정` → 감시 회차 카드 · 이번 세션 알림 기록 → `삭제`(시연 데이터 정리)",
    "d08": "헤더 메뉴 강조(관리자 없음) → 주소 `/admin` 직접 접근 → **'관리자 전용 화면입니다'**",
    "d09": "헤더 `로그아웃` → 로그인 화면",
    "d10": "`시스템 관리자 테스트 로그인` → 관리자 메뉴 강조 → '읽기 전용 모드' 안내",
    "d11": "지표 카드 4개 → 크롤러 상태(모드·주기·다음 실행·원격 수집기) → Plotly 크롤링 성능 리포트",
    "d12": "수집 진단 `CGV`(국외 IP 차단 → 실패) → `메가박스`(성공 · 건수 · 소요시간), 대기 구간 편집 제거",
    "d13": "자물쇠 표시 `전체` 실행 버튼 → 서버 403 토스트 '읽기 전용입니다'",
    "d14": "`회원 권한` 탭 → 검색 `movpick` → 일반 회원 행 `관리자` → 서버 403 토스트",
    "c00": "계정 비교표(일반 회원 · 테스트 관리자 · 실제 관리자) 정지 화면",
    "d15": "`movpick-api.onrender.com/docs` Swagger: auth → showtimes → admin → rpa 태그 순서로 이동",
    "d16": "`/health` 응답(배포 커밋 해시 · DB 종류 · 회차 수) — 값은 그대로, 들여쓰기만 적용",
    "d17": "GitHub Actions 최근 실행(초록 체크) 강조",
}


def mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def main() -> None:
    starts = scene_starts(SCENES)
    timings = {t["id"]: t for t in (load_json(BUILD / "tts" / "timings.json") or [])}
    rows, detail = [], []
    for s in SCENES:
        a, b = starts[s["id"]], starts[s["id"]] + s["dur"]
        screen = f"발표자료 {s['ref']}장" if s["kind"] == "slide" else ("계정 비교 카드" if s["kind"] == "still" else "movpick.onrender.com")
        action = ACTIONS.get(s["id"], "슬라이드 표시" + (" · 강조 테두리" if s["hl"] else ""))
        text = " ".join(shown for shown, _ in s["lines"])
        rows.append(f"| {mmss(a)}–{mmss(b)} | {s['label']} | {screen} | {action} | {text} | {s['tag'] or ''} |")
        spoken = [sp for _, sp in s["lines"] if sp]
        detail.append(f"### {mmss(a)} · {s['id']} · {s['label']} ({s['dur']}초)\n\n- 화면: {screen}\n- 동작: {action}\n"
                      + (f"- 안내 태그: `{s['tag']}`\n" if s["tag"] else "")
                      + (f"- 합성 속도: {timings[s['id']]['rate']} · 실제 발화 {timings[s['id']]['speech']}초\n" if s["id"] in timings else "")
                      + "\n" + "\n".join(f"> {shown}" for shown, _ in s["lines"])
                      + ("\n\n발음용 문장: " + " / ".join(spoken) if spoken else "") + "\n")
    speech = sum(t["speech"] for t in timings.values()) if timings else 0
    md = f"""# movpick 10분 발표·시연 영상 — 대본 및 연출 가이드

> 자동 생성 문서 (`docs/video/tools/gen_guide.py`). 대본·시간은 `video_scenes.py` 에서만 수정합니다.

| 항목 | 내용 |
|---|---|
| 파일 | `movpick_final.mp4` (1920×1080 · 30fps · H.264 High · AAC 160k 스테레오 · 한국어) |
| 길이 | {mmss(TOTAL)} · 장면 {len(SCENES)}개 · 실제 발화 약 {speech:.0f}초 |
| 구성 | PPT 1~14장 → 일반 회원 시연 → 관리자(읽기 전용) 시연 → 계정 비교 → 운영 근거(/docs · /health · CI) → 클로징 15·16장 |
| 시연 환경 | 운영 서비스 `https://movpick.onrender.com` (테스트 계정 2개 비교) |
| 내레이션 | 신경망 합성 음성 `{VOICE}` (속도 {RATE}, 톤 {PITCH}), 문장 단위 합성 + 문장 사이 0.35초 쉼, 저역 제거·압축·명료도 보강 후 −16 LUFS |
| 자막 | 화면 자막(한 줄 30자 이내) + `movpick_final.srt` |
| 연출 | 노란 원형 커서·클릭 링, 시안 테두리 강조(0.3초 페이드), 구간 라벨(슬라이드 오른쪽 위 · 시연 왼쪽 아래), 노란 안내 태그 |

## 시연 데이터 원칙

- 일반 회원 시연에서 감시 1건을 등록했다가 장면 안에서 직접 삭제합니다(운영 DB 에 남지 않음).
- 취소표 알림은 **실제 서버가 보낸 WebSocket 알림**입니다. 좌석 변동은 수집 주기 사이를 시뮬레이션한 값이라고 대본과 태그로 밝힙니다.
  첫 알림 이후 이어지는 중복 팝업만 화면에서 생략했습니다.
- 관리자 쓰기 시도(크롤러 실행·권한 변경)는 테스트 관리자 계정이라 **서버가 403 으로 거부**하므로 데이터가 바뀌지 않습니다.
- 수집 진단은 저장하지 않는 읽기 전용 기능입니다. 네트워크 대기 구간은 편집으로 잘라 냈습니다.
- 화면에 토큰·비밀번호·환경 변수·개발자 도구는 나오지 않습니다(테스트 계정 비밀번호는 로그인 화면에 공개된 값).

## 타임라인

| 시간 | 구간 | 화면 | 동작 | 대본 | 안내 태그 |
|---|---|---|---|---|---|
""" + "\n".join(rows) + "\n\n## 장면별 상세\n\n" + "\n".join(detail) + """
## 다시 만들기

```bash
.venv/Scripts/python docs/video/tools/tts.py            # 1) 문장 단위 합성
powershell -File docs/video/tools/export_slides.ps1      # 2) 슬라이드 PNG (읽기 전용으로 열기)
.venv/Scripts/python docs/video/tools/record_demo.py     # 3) 운영 서비스 시연 녹화 (CDP 스크린캐스트)
.venv/Scripts/python docs/video/tools/compose.py --rebuild   # 4) 합성 · 자막 · 2-pass 인코딩 · 하이라이트 · 썸네일
.venv/Scripts/python docs/video/tools/check_final.py     # 5) 형식 · 음성 · 깜박임 검사
.venv/Scripts/python docs/video/tools/gen_guide.py       # 6) 이 문서 갱신
```

실제 사람 목소리로 바꾸려면 장면별 녹음을 `docs/video/build/tts/<장면ID>.wav` 로 저장하고(장면 길이보다 0.6초 이상 짧게)
`compose.py --rebuild-audio` 를 실행합니다.
"""
    (VIDEO / "영상_대본_및_연출가이드.md").write_text(md, encoding="utf-8")
    print("saved 영상_대본_및_연출가이드.md")


if __name__ == "__main__":
    main()
