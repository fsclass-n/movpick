#!/usr/bin/env bash
# movpick CGV 수집기 - 국내 클라우드 VM 원클릭 설치 (Ubuntu/Debian/Oracle Linux)
#
#   CGV 는 국외 IP(Render 등)를 차단하므로 국내 리전 VM 에서 수집 → movpick-api 로 전송합니다.
#   예) Oracle Cloud Free Tier (서울/춘천 리전), AWS Lightsail/EC2 서울, NCP, KT Cloud
#
#   사용법 (VM 에서):
#     curl -fsSL https://raw.githubusercontent.com/fsclass-n/movpick/main/scripts/setup-collector-vm.sh -o setup.sh
#     RPA_INGEST_TOKEN='<Render 와 같은 값>' bash setup.sh
#
#   옵션 환경변수: MOVPICK_API_URL(기본 https://movpick-api.onrender.com), CGV_EVERY_MINUTES(기본 30), MOVPICK_DIR(기본 ~/movpick)
set -euo pipefail

: "${RPA_INGEST_TOKEN:?RPA_INGEST_TOKEN 을 지정하세요 (Render 의 RPA_INGEST_TOKEN 과 같은 값)}"
API="${MOVPICK_API_URL:-https://movpick-api.onrender.com}"
EVERY="${CGV_EVERY_MINUTES:-30}"
DIR="${MOVPICK_DIR:-$HOME/movpick}"
REPO="https://github.com/fsclass-n/movpick.git"
SUDO=$([ "$(id -u)" -eq 0 ] && echo "" || echo "sudo")

echo "▶ 1/5 CGV 접근 사전 점검 (이 VM 의 IP 가 차단되는지 확인)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 15 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
  -H "Accept: application/json, text/plain, */*" -H "Referer: https://cgv.co.kr/cnm/movieBook" -H "Origin: https://cgv.co.kr" \
  -H "Sec-Fetch-Site: same-origin" -H "Sec-Fetch-Mode: cors" -H "Sec-Fetch-Dest: empty" \
  "https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd=A420&siteNo=0056&scnYmd=$(date +%Y%m%d)&rtctlScopCd=08" || true)
if [ "$CODE" != "200" ]; then
  echo "✖ CGV 응답 HTTP $CODE — 이 VM 의 IP 는 CGV 에서 차단됩니다. 국내 리전/다른 IP 의 서버를 사용하세요." >&2
  exit 1
fi
echo "  ✔ CGV 접근 가능 (HTTP 200)"

echo "▶ 2/5 백엔드 수신 토큰 확인 ($API)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 90 "$API/api/rpa/ping" -H "X-RPA-Token: $RPA_INGEST_TOKEN" || true)
case "$CODE" in
  200) echo "  ✔ 토큰 인증 성공" ;;
  401) echo "✖ 토큰 불일치 — Render 의 RPA_INGEST_TOKEN 과 같은 값을 넣으세요." >&2; exit 1 ;;
  404) echo "✖ 백엔드에 RPA_INGEST_TOKEN 이 설정되지 않았습니다 (Render 환경 변수 확인)." >&2; exit 1 ;;
  *)   echo "  ! 백엔드 응답 HTTP $CODE (Render 슬립 상태일 수 있음) — 계속 진행합니다." ;;
esac

echo "▶ 3/5 Docker · Git 설치"
if ! command -v git >/dev/null; then
  if command -v apt-get >/dev/null; then $SUDO apt-get update -y && $SUDO apt-get install -y git; else $SUDO dnf install -y git || $SUDO yum install -y git; fi
fi
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | $SUDO sh
fi
$SUDO systemctl enable --now docker >/dev/null 2>&1 || true

echo "▶ 4/5 소스 받기 → $DIR"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone --depth 1 "$REPO" "$DIR"; fi
umask 077
cat > "$DIR/.env" <<ENV
# movpick CGV 수집기 (setup-collector-vm.sh 생성)
RPA_INGEST_TOKEN=$RPA_INGEST_TOKEN
MOVPICK_API_URL=$API
CGV_EVERY_MINUTES=$EVERY
TZ=Asia/Seoul
ENV

echo "▶ 5/5 수집기 컨테이너 빌드·기동 (${EVERY}분 주기, 재부팅 시 자동 시작)"
cd "$DIR"
$SUDO docker compose --profile collector up -d --build cgv-collector
sleep 20
$SUDO docker logs --tail 20 movpick-cgv-collector || true
echo
echo "✔ 완료. 로그: sudo docker logs -f movpick-cgv-collector"
echo "  업데이트: cd $DIR && git pull && sudo docker compose --profile collector up -d --build cgv-collector"
echo "  중지:     cd $DIR && sudo docker compose --profile collector stop cgv-collector"
