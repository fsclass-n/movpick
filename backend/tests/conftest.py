import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp()) / "test.sqlite3"
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_db.as_posix()}",
    "RPA_ENABLED": "false",
    "DEMO_LOGIN_ENABLED": "true",
    "SECRET_KEY": "test-secret",
    # 개발자 로컬 .env 값이 테스트에 섞이지 않도록 고정
    "RPA_INGEST_TOKEN": "",
    "RPA_REMOTE_CHAINS": "",
    "RPA_PROXY_URL": "",
    "ADMIN_EMAIL": "root@movpick.app",
    "ADMIN_PASSWORD": "Root!Admin2026",
    "ADMIN_NAME": "실제 관리자",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def auth(client, kind: str) -> dict:
    if kind == "root":  # .env(ADMIN_EMAIL/ADMIN_PASSWORD) 로 생성된 실제 관리자
        res = client.post("/api/auth/login", json={"email": "root@movpick.app", "password": "Root!Admin2026"})
    else:
        res = client.post(f"/api/auth/demo/{kind}")
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
