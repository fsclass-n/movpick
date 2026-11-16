# AGENTS.md

## Environment (Windows dev machine)
- Python 3.11 venv at `.venv` (`py -3.11 -m venv .venv`); run tools via `.venv/Scripts/python -m ...`
- Node is installed at `C:\Program Files\nodejs` but may be missing from Git Bash PATH:
  `export PATH="/c/Program Files/nodejs:$PATH"`
- Set `PYTHONIOENCODING=utf-8` when printing Korean output to the console.
- Backend Dockerfile lives at repo root (`./Dockerfile`, Render default path). Docker is not installed locally; Docker builds are verified in GitHub Actions (`docker` job in ci.yml).

## Commands
- Backend dev: `.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000` (run from repo root)
- Tests: `.venv/Scripts/python -m pytest -q` (uses temp SQLite, RPA disabled via conftest)
- RPA CLI: `.venv/Scripts/python -m rpa.runner --chain all --mode auto`
- Frontend: `cd frontend && npm run dev` / `npm run build`
- Install npm deps with `npm install --before=<7 days ago>` to avoid freshly published versions.

## Conventions
- Single `.env` at repo root (loaded by `backend/app/config.py`); document new keys in `.env.example`.
- No TiDB vars → SQLite fallback at `backend/movpick.sqlite3`.
- Timestamps are naive local time (`datetime.now`); Docker sets `TZ=Asia/Seoul`.
- Backend must run with a single worker (crawler/monitor loops live in-process).
- Tailwind v4: custom reusable classes are defined with `@utility` in `frontend/src/index.css`.

## Video (docs/video)
- Single source of truth for timing/narration: `docs/video/tools/video_scenes.py` (total must be exactly 600s).
- Pipeline: `tts.py` → `export_slides.ps1` (PowerShell scripts need UTF-8 BOM for Korean paths) → `record_demo.py` → `compose.py --rebuild` → `check_final.py` → `gen_guide.py`.
- Demo is recorded with CDP screencast frames (timestamped); Playwright's built-in video drifts vs wall clock and must not be used for cuts.
- ffmpeg comes from winget (Gyan.FFmpeg); tools locate it automatically. `build/` is git-ignored; only `movpick_final.mp4` and `movpick_highlight.mp4` are committed (keep the final ≤95MB, GitHub hard limit is 100MB).

## Documents (docs/*.hwpx → docs/pdf)
- `docs/tools/build_docs.py` fills the journal templates (only empty cells; metadata kept) and writes the deliverables, then saves HWPX/PDF via Hancom COM.
- Hancom automation needs the security module: registry `HKCU\Software\HNC\HwpAutomation\Modules\FilePathCheckerModule` → `.venv\Lib\site-packages\pyhwpx\FilePathCheckerModule.dll` (`pip install pyhwpx pywin32`).
- Kill leftover hidden `Hwp` processes if a COM call hangs.
