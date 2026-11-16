# PowerPoint 발표자료를 1920x1080 PNG 로 내보내기 (읽기 전용으로 열어 원본 변경 없음)
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$pptx = Join-Path $root "docs\프로젝트_발표자료.pptx"
$out = Join-Path $root "docs\video\build\slides"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$app = New-Object -ComObject PowerPoint.Application
$p = $app.Presentations.Open($pptx, $true, $false, $false)
for ($i = 1; $i -le $p.Slides.Count; $i++) { $p.Slides.Item($i).Export((Join-Path $out ("slide{0:D2}.png" -f $i)), "PNG", 1920, 1080) }
"exported $($p.Slides.Count) slides -> $out"
$p.Close(); $app.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
