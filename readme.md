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

- **테스트 관리자는 읽기 전용**입니다. 관리자 화면 조회·수집 진단만 가능하고 크롤러 실행/설정, 회원 권한 변경은 403으로 거부됩니다.
- **실제 관리자**는 `.env`(Render 환경 변수)의 `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` 으로 기동 시 생성·동기화됩니다.
  비밀번호는 서비스 비밀번호 규칙을 만족해야 하며, 이 계정은 다른 관리자가 권한을 해제할 수 없습니다.

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

### CGV 원격 수집기 (국외 IP 차단 대응)

> **현재 운영: CGV는 데모 데이터** (`RPA_MOCK_CHAINS=cgv`). 화면에 `DEMO` 로 표시되며 인기 순위에서는 제외됩니다.
> 국내 수집 환경이 준비되면 `RPA_MOCK_CHAINS` 를 비우고 아래 방식 중 하나로 전환하세요.

CGV 스케줄 API는 Cloudflare WAF가 **국외 IP를 403으로 차단**합니다(진단 결과: 국내 `ray=ICN` 허용, Render·GitHub 호스티드 러너 `ray=PDX` 차단 — 브라우저 헤더/Playwright 모두 동일).
따라서 CGV는 **국내 IP**에서 수집해 백엔드로 전송합니다. 메가박스·롯데시네마는 Render에서 직접 수집됩니다.
관리자 화면의 **수집 진단** 버튼으로 현재 서버에서의 접속 가능 여부를 언제든 확인할 수 있습니다.

공통 설정: 토큰을 생성해 **Render**와 **수집기 환경의 `.env`**(또는 GitHub secret)에 같은 값으로 `RPA_INGEST_TOKEN` 등록, Render에 `RPA_REMOTE_CHAINS=cgv` 등록
(`python -c "import secrets;print(secrets.token_urlsafe(32))"`)

| 방식 | PC 의존 | 설정 |
| --- | --- | --- |
| **국내 클라우드 VM + Docker** (권장: Oracle Cloud Free Tier 서울/춘천, AWS 서울 등) | 없음 | VM에서 `RPA_INGEST_TOKEN='...' bash setup.sh` 한 번 실행 (아래) → 30분 상주 수집, 재부팅 시 자동 시작 |
| 국내 VM + GitHub self-hosted runner | 없음 | 러너 등록(라벨 예: `kr`) → repo variable `CGV_RUNNER=kr`, secret `RPA_INGEST_TOKEN` → `CGV Collector` 워크플로가 30분마다 실행 |
| 국내 프록시 | 없음 | Render에 `RPA_PROXY_URL=http://user:pass@host:port` 등록, `RPA_REMOTE_CHAINS` 제거 → 서버가 직접 수집 |
| 국내 PC 작업 스케줄러 (임시) | 있음 | `scripts\cgv-collector.ps1` 를 30분 주기로 등록 |

```bash
# 국내 VM 원클릭 설치: CGV 접근·토큰 사전 점검 → Docker 설치 → 경량 수집기 컨테이너 기동
curl -fsSL https://raw.githubusercontent.com/fsclass-n/movpick/main/scripts/setup-collector-vm.sh -o setup.sh
RPA_INGEST_TOKEN='<Render 와 같은 값>' bash setup.sh

# 수동 실행 / 상주 실행
python -m rpa.runner --chain cgv --mode real --days 2 --push https://movpick-api.onrender.com
python -m rpa.runner --chain cgv --mode real --days 2 --push https://movpick-api.onrender.com --every 30
```

- `movpick-api.onrender.com`(Render)은 **수신 서버**로만 사용합니다. Render에는 국내 리전이 없어 수집기 자체는 Render에서 실행할 수 없습니다.
- 해당 일자의 실데이터가 있으면 수집이 실패해도 모의 데이터와 섞지 않고 유지합니다(모든 체인 공통). `RPA_REAL_TTL_MINUTES`(기본 180분)를 넘기면 관리자 화면에 '갱신 지연'으로 표시됩니다.
- 실데이터가 전혀 없는 일자만 모의 데이터로 대체합니다.

## 배포

- **Render**: `render.yaml` Blueprint로 `movpick-api`(루트 `Dockerfile`, Playwright+Chromium 빌드 타임 설치)와 `movpick`(Static) 두 서비스를 독립 생성합니다.
  `sync: false` 항목(TiDB·OAuth·웹훅 키)은 Render 대시보드에서 직접 입력하세요.
- **Netlify**: `netlify.toml` (base=`frontend`, SPA 리다이렉트 포함).
- **OAuth 콜백 URL**: `{BACKEND_URL}/api/auth/oauth/{google|naver|kakao}/callback` 을 각 개발자 콘솔에 등록하세요.
  로그인 완료 후에는 요청한 프런트엔드 Origin(`FRONTEND_ORIGINS` 에 포함된 경우)으로 복귀합니다.
- **GitHub Actions**: `RENDER_API_DEPLOY_HOOK`, `RENDER_WEB_DEPLOY_HOOK`, `NETLIFY_BUILD_HOOK` 시크릿이 있으면 main 푸시 후 배포 훅을 호출합니다.
- Render 무료 티어(512MB)에서 Chromium 구동 시 메모리가 빠듯할 수 있으며, 15분 유휴 후 슬립됩니다(첫 요청 지연).
