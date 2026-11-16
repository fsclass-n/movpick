import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

ALGORITHM = "HS256"
PASSWORD_RULE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S{8,64}$")
PASSWORD_RULE_MESSAGE = "비밀번호는 영문 대·소문자, 숫자, 특수문자를 모두 포함한 8자 이상이어야 합니다."

bearer = HTTPBearer(auto_error=False)


def validate_password(password: str) -> bool:
    return bool(PASSWORD_RULE.match(password or ""))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    return bool(hashed) and bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def user_from_token(db: Session, token: str | None) -> User | None:
    payload = decode_token(token) if token else None
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    return user if user and user.is_active else None


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    user = user_from_token(db, creds.credentials if creds else None)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자 권한이 필요합니다.")
    return user


def require_admin_write(user: User = Depends(require_admin)) -> User:
    if user.read_only:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "테스트 관리자 계정은 읽기 전용입니다. 조회만 가능합니다.")
    return user
