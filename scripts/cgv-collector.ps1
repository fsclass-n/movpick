# movpick 원격 CGV 수집기 (국내 PC에서 실행)
#  - CGV는 해외 데이터센터 IP(Render)를 차단하므로 국내 PC에서 수집 후 백엔드로 전송합니다.
#  - 루트 .env 에 RPA_INGEST_TOKEN (Render 와 동일 값) 이 필요합니다.
#  - 작업 스케줄러 등록(30분 주기):
#      schtasks /Create /SC MINUTE /MO 30 /TN "movpick-cgv-collector" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File <repo>\scripts\cgv-collector.ps1"
param(
  [string]$Api = $(if ($env:MOVPICK_API_URL) { $env:MOVPICK_API_URL } else { "https://movpick-api.onrender.com" })
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$log = Join-Path $root "rpa\output\cgv-collector.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Push-Location $root
try {
  "[$(Get-Date -Format s)] start -> $Api" | Out-File -Append -Encoding utf8 $log
  & "$root\.venv\Scripts\python.exe" -m rpa.runner --chain cgv --mode real --days 2 --push $Api 2>&1 |
    Out-File -Append -Encoding utf8 $log
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
