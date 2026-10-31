from __future__ import annotations

import secrets
import sys
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User

settings = get_settings()

# 默认签发 12 小时
TOKEN_EXPIRE_HOURS = 12
# 游客令牌单独给短时效，够看一遍演示数据
GUEST_TOKEN_EXPIRE_HOURS = 2
ALGORITHM = "HS256"

GUEST_USERNAME = "guest"
GUEST_ROLE = "guest"

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(raw: str) -> str:
    """bcrypt 只接受 72 字节以内的密码，超长先截断"""
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    expire_at = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_guest_token(user: User) -> str:
    expire_at = datetime.now() + timedelta(hours=GUEST_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": GUEST_ROLE,
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    user = db.execute(stmt).scalars().first()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
    except jwt.PyJWTError:
        raise unauthorized

    username = payload.get("sub")
    if not username:
        raise unauthorized
    stmt = select(User).where(User.username == username)
    user = db.execute(stmt).scalars().first()
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_login(user: User = Depends(get_current_user)) -> User:
    return user


def require_editor(user: User = Depends(get_current_user)) -> User:
    """游客只能看，写操作一律拦下"""
    if user.role == GUEST_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="游客模式下不能修改数据，请登录账号后操作",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作需要管理员权限",
        )
    return user


def register_user(db: Session, username: str, email: str, password: str, display_name: str) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name or username,
        email=email,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_admin_user(db: Session) -> None:
    if not settings.admin_password or settings.admin_password == "CHANGE_ME":
        print(
            "[Resistance] 未配置 ADMIN_PASSWORD，跳过管理员账号创建",
            file=sys.stderr,
            flush=True,
        )
        return

    stmt = select(User).where(User.username == settings.admin_username)
    exists = db.execute(stmt).scalars().first()
    if exists is not None:
        return
    db.add(
        User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            display_name="管理员",
            role="admin",
        )
    )
    db.commit()


def ensure_guest_user(db: Session) -> None:
    """游客账号固定存在，密码随机生成，没有任何人能拿它登录"""
    stmt = select(User).where(User.username == GUEST_USERNAME)
    exists = db.execute(stmt).scalars().first()
    if exists is not None:
        return
    db.add(
        User(
            username=GUEST_USERNAME,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            display_name="访客",
            role=GUEST_ROLE,
        )
    )
    db.commit()
