import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp()) / "test.sqlite3"
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_db.as_posix()}",
    "RPA_ENABLED": "false",
    "DEMO_LOGIN_ENABLED": "true",
    "SECRET_KEY": "test-secret",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def auth(client, kind: str) -> dict:
    token = client.post(f"/api/auth/demo/{kind}").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
