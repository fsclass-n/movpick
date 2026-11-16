import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..accounts import DEMO_ACCOUNTS, DEMO_EMAILS
from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import LoginIn, SignupIn, TokenOut, UserOut
from ..security import (
    ALGORITHM, create_access_token, get_current_user, hash_password, validate_password, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("movpick.auth")
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


OAUTH = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "profile": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "naver": {
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "profile": "https://openapi.naver.com/v1/nid/me",
        "scope": "",
    },
    "kakao": {
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "profile": "https://kapi.kakao.com/v2/user/me",
        "scope": "profile_nickname account_email",
    },
}
Provider = Literal["google", "naver", "kakao"]


def _token_response(db: Session, user: User) -> TokenOut:
    user.last_login_at = datetime.now()
    db.commit()
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


def ensure_demo_user(db: Session, kind: str) -> User:
    spec = DEMO_ACCOUNTS[kind]
    user = db.scalar(select(User).where(User.email == spec["email"]))
    if not user:
        user = User(email=spec["email"], name=spec["name"], password_hash=hash_password(spec["password"]), role=spec["role"])
        db.add(user)
    if kind == "admin":
        user.role = "admin"
    user.is_active = True
    db.commit()
    return user


def ensure_env_admin(db: Session) -> User | None:
    """ADMIN_EMAIL / ADMIN_PASSWORD 로 지정한 실제 관리자 계정을 생성·동기화 (기동 시 호출)."""
    email, password = settings.admin_email.lower(), settings.admin_password
    if not email or not password:
        return None
    if email in DEMO_EMAILS:
        log.error("ADMIN_EMAIL 에 테스트 계정은 사용할 수 없습니다: %s", email)
        return None
    if not validate_password(password):
        log.error("ADMIN_PASSWORD 가 비밀번호 규칙을 만족하지 않아 관리자 계정을 생성하지 않았습니다.")
        return None
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, name=settings.admin_name or "관리자")
        db.add(user)
    if not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)
    user.role, user.is_active = "admin", True
    db.commit()
    log.info("환경 변수 관리자 계정 동기화: %s", email)
    return user


@router.post("/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "이미 가입된 이메일입니다.")
    user = User(email=body.email.lower(), name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return _token_response(db, user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.is_active:
        raise HTTPException(403, "비활성화된 계정입니다.")
    return _token_response(db, user)


@router.post("/demo/{kind}", response_model=TokenOut)
def demo_login(kind: Literal["user", "admin"], db: Session = Depends(get_db)):
    if not settings.demo_login_enabled:
        raise HTTPException(404, "테스트 로그인이 비활성화되어 있습니다.")
    return _token_response(db, ensure_demo_user(db, kind))


@router.get("/demo-accounts")
def demo_accounts():
    if not settings.demo_login_enabled:
        return {}
    return {k: {"email": v["email"], "password": v["password"]} for k, v in DEMO_ACCOUNTS.items()}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------- OAuth 2.0
def _client(provider: str) -> tuple[str, str]:
    return getattr(settings, f"{provider}_client_id"), getattr(settings, f"{provider}_client_secret")


def _redirect_uri(provider: str, request: Request) -> str:
    """OAuth 콜백 URL. BACKEND_URL 이 비었거나 localhost 인데 실제 요청 호스트가 다르면(배포 환경 설정 누락)
    요청 기준 주소(프록시 헤더 반영)를 사용해 redirect_uri_mismatch 를 방지한다."""
    base = settings.backend_url
    if not base or (urlsplit(base).hostname in LOCAL_HOSTS and request.url.hostname not in LOCAL_HOSTS):
        base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/oauth/{provider}/callback"


def _safe_origin(origin: str | None) -> str:
    origin = (origin or "").rstrip("/")
    return origin if origin in settings.frontend_origins else settings.frontend_url


@router.get("/providers")
def providers():
    return {p: bool(_client(p)[0]) for p in OAUTH}


@router.get("/oauth/{provider}/login")
def oauth_login(provider: Provider, request: Request, redirect: str | None = Query(None)):
    client_id, _ = _client(provider)
    if not client_id:
        raise HTTPException(501, f"{provider} OAuth 키가 설정되지 않았습니다.")
    state = jwt.encode(
        {"origin": _safe_origin(redirect), "nonce": secrets.token_urlsafe(8),
         "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        settings.secret_key, algorithm=ALGORITHM,
    )
    params = {"client_id": client_id, "redirect_uri": _redirect_uri(provider, request), "response_type": "code", "state": state}
    if OAUTH[provider]["scope"]:
        params["scope"] = OAUTH[provider]["scope"]
    return RedirectResponse(f"{OAUTH[provider]['authorize']}?{urlencode(params)}")


async def _fetch_profile(provider: str, code: str, state: str, redirect_uri: str) -> tuple[str, str, str | None]:
    """(provider_id, name, email)"""
    client_id, client_secret = _client(provider)
    data = {"grant_type": "authorization_code", "client_id": client_id, "client_secret": client_secret,
            "code": code, "redirect_uri": redirect_uri, "state": state}
    async with httpx.AsyncClient(timeout=10) as c:
        tok = (await c.post(OAUTH[provider]["token"], data=data, headers={"Accept": "application/json"})).json()
        access = tok.get("access_token")
        if not access:
            raise HTTPException(400, f"OAuth 토큰 발급 실패: {tok.get('error_description') or tok.get('error')}")
        prof = (await c.get(OAUTH[provider]["profile"], headers={"Authorization": f"Bearer {access}"})).json()
    if provider == "google":
        return prof["sub"], prof.get("name") or "Google 사용자", prof.get("email")
    if provider == "naver":
        r = prof.get("response") or {}
        return r["id"], r.get("name") or r.get("nickname") or "네이버 사용자", r.get("email")
    acc = prof.get("kakao_account") or {}
    return str(prof["id"]), (acc.get("profile") or {}).get("nickname") or "카카오 사용자", acc.get("email")


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: Provider, request: Request, code: str | None = None, state: str = "", error: str | None = None,
                         db: Session = Depends(get_db)):
    try:
        origin = _safe_origin(jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM]).get("origin"))
    except jwt.PyJWTError:
        raise HTTPException(400, "유효하지 않은 OAuth state 입니다.")
    if error or not code:
        return RedirectResponse(f"{origin}/#oauth_error={error or 'cancelled'}")

    pid, name, email = await _fetch_profile(provider, code, state, _redirect_uri(provider, request))
    user = db.scalar(select(User).where(User.provider == provider, User.provider_id == pid))
    if not user and email:
        user = db.scalar(select(User).where(User.email == email.lower()))
    if not user:
        user = User(email=(email or f"{provider}_{pid}@oauth.movpick.app").lower(), name=name,
                    provider=provider, provider_id=pid)
        db.add(user)
    elif not user.provider_id:
        user.provider, user.provider_id = provider, pid
    token = _token_response(db, user).access_token
    # 루트(/)로 복귀: SPA 리라이트 규칙이 없는 정적 호스팅(Render Static 등)에서도 항상 index.html 이 응답됨
    return RedirectResponse(f"{origin}/#oauth_token={token}")
