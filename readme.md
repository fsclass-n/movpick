# movpick

RPA 중심의 자동화 및 효율화
영화티켓 예약 추천: 상영 시간표를 자동으로 긁어오고, 명당 자리 잔여석을 실시간 체크해 알림을 보내는 RPA 기능을 넣으면 차별화됩니다.

> RPA 기반 영화 상영 시간표 자동 동기화 및 명당 자리 실시간 예매 추천 플랫폼
> Team: 박미금(조장) · 김모란 · 이오리 · 홍기흥

| 구분 | URL |
| --- | --- |
| GitHub | https://github.com/fsclass-n/movpick |
| 프로젝트 안내 (GitHub Pages) | https://fsclass-n.github.io/movpick/ |
| Frontend Staging (Netlify) | https://movpick.netlify.app |
| Frontend Production (Render) | https://movpick.onrender.com |
| Backend API (Render) | https://movpick-api.onrender.com (`/docs`, `/health`) |

## 디렉터리 구조

```
backend/app/        FastAPI 앱 (config, db, models, security, routers/, services/)
  routers/          auth(로컬·테스트·OAuth) · showtimes(시간표·좌석·통계) · watches(알림) · admin
  services/         crawler(주기 실행·DB 동기화) · monitor(잔여석 감지) · notifier(웹훅) · ws(WebSocket)
backend/tests/      pytest
rpa/                RPA 패키지 (adapters/ cgv·megabox·lotte·mock, seatmap, service, runner CLI)
frontend/           React(Vite) + Tailwind CSS v4
pages/              GitHub Pages 프로젝트 안내 페이지
.github/workflows/  ci.yml(테스트·빌드·Docker 스모크·Deploy Hook) · pages.yml
```

## 로컬 실행

```bash
# 1) 환경 변수
cp .env.example .env          # TiDB / OAuth / 웹훅 값 입력 (TiDB 미설정 시 SQLite, OAuth 키 미설정 시 해당 버튼 비활성 안내)

# 2) 백엔드 (Python 3.11)
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000

# 3) 프런트엔드 (Node 22+)
cd frontend && npm ci && npm run dev                          # http://localhost:5173

# RPA 단독 실행
.venv/Scripts/python -m rpa.runner --chain all --mode auto [--headed] [--json out.json]

# 테스트
.venv/Scripts/python -m pytest -q

# Docker Compose (백엔드 + nginx 프런트)
docker compose up --build
```

테스트 계정 (로그인 화면의 간편 로그인 버튼으로 자동 입력·로그인)

| 구분 | 이메일 | 비밀번호 |
| --- | --- | --- |
| 일반 회원 | user@movpick.app | Movpick!2026 |
| 시스템 관리자 | admin@movpick.app | Admin!2026 |

`DEMO_LOGIN_ENABLED=false` 로 비활성화할 수 있습니다.

## RPA 수집 방식

| 체인 | 방식 | 비고 |
| --- | --- | --- |
| CGV | Playwright Headless Chromium → 예매 페이지 로드 후 브라우저 컨텍스트에서 스케줄 API 호출 | 일반 HTTP 요청은 WAF가 403 차단 |
| 메가박스 | Requests → `schedulePage.do` JSON, BeautifulSoup으로 텍스트 정제 | 코엑스 · 강남 |
| 롯데시네마 | Requests → `TicketingData.aspx` JSON | 월드타워 · 가산디지털 |

- `RPA_MODE=auto` 는 실제 수집 실패 시(사이트 구조 변경·차단) 모의 데이터로 자동 대체하고, 관리자 로그에 원인을 남깁니다.
- 영화관은 **잔여석 수**만 공개하므로 좌석 단위 배치도는 해당 수치에 맞춰 추정한 값입니다(실제 수집 회차는 화면에 안내 문구 표시).
  크롤링 사이 구간의 취소표/신규 예매는 `SEAT_SIMULATION=true` 일 때 시뮬레이션되며, 다음 크롤링에서 실제 잔여석 수로 보정됩니다.
- 명당 자리: 스크린 기준 약 62% 깊이 · 중앙 열에 가까울수록 높은 점수(NumPy), 상위 18% 좌석을 명당으로 표시합니다.

### CGV 원격 수집기 (데이터센터 IP 차단 대응)

CGV는 해외 데이터센터 IP(Render)에서의 요청을 **HTTP 403**으로 차단합니다. 국내 PC에서 수집해 백엔드로 전송하는 방식으로 해결합니다.

1. 토큰 생성 후 **Render 대시보드**와 **수집기 PC의 `.env`** 에 같은 값으로 `RPA_INGEST_TOKEN` 등록
   (`python -c "import secrets;print(secrets.token_urlsafe(32))"`)
2. Render 백엔드에 `RPA_REMOTE_CHAINS=cgv` 등록 → 서버는 CGV를 직접 수집하지 않고 원격 데이터를 사용
3. 수집기 PC에서 실행 / 작업 스케줄러 등록(30분 주기)

```powershell
.venv\Scripts\python -m rpa.runner --chain cgv --mode real --days 2 --push https://movpick-api.onrender.com
schtasks /Create /SC MINUTE /MO 30 /TN "movpick-cgv-collector" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File D:\git605\movpick\scripts\cgv-collector.ps1"
```

- 해당 일자의 실데이터가 있으면 수집이 실패해도 모의 데이터와 섞지 않고 유지합니다(모든 체인 공통). `RPA_REAL_TTL_MINUTES`(기본 180분)를 넘기면 관리자 화면에 '갱신 지연'으로 표시됩니다.
- 실데이터가 전혀 없는 일자만 모의 데이터로 대체합니다.
- 대안: `RPA_PROXY_URL` 에 국내 프록시를 지정하면 서버에서 직접 수집합니다.

## 배포

- **Render**: `render.yaml` Blueprint로 `movpick-api`(루트 `Dockerfile`, Playwright+Chromium 빌드 타임 설치)와 `movpick`(Static) 두 서비스를 독립 생성합니다.
  `sync: false` 항목(TiDB·OAuth·웹훅 키)은 Render 대시보드에서 직접 입력하세요.
- **Netlify**: `netlify.toml` (base=`frontend`, SPA 리다이렉트 포함).
- **OAuth 콜백 URL**: `{BACKEND_URL}/api/auth/oauth/{google|naver|kakao}/callback` 을 각 개발자 콘솔에 등록하세요.
  로그인 완료 후에는 요청한 프런트엔드 Origin(`FRONTEND_ORIGINS` 에 포함된 경우)으로 복귀합니다.
- **GitHub Actions**: `RENDER_API_DEPLOY_HOOK`, `RENDER_WEB_DEPLOY_HOOK`, `NETLIFY_BUILD_HOOK` 시크릿이 있으면 main 푸시 후 배포 훅을 호출합니다.
- Render 무료 티어(512MB)에서 Chromium 구동 시 메모리가 빠듯할 수 있으며, 15분 유휴 후 슬립됩니다(첫 요청 지연).
