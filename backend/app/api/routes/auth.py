from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.measurement import LoginRequest, LoginResponse, RegisterRequest
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    register_user,
)
from app.models.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.post("/register", summary="注册账号")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if db.execute(select(User).where(User.username == payload.username)).scalars().first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.execute(select(User).where(User.email == email)).scalars().first():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    user = register_user(
        db,
        username=payload.username,
        email=email,
        password=payload.password,
        display_name=payload.display_name or payload.username,
    )
    return {"status": "ok", "username": user.username, "display_name": user.display_name}


@router.post("/login", response_model=LoginResponse, summary="账号登录")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return LoginResponse(
        access_token=create_access_token(user),
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@router.get("/me", summary="获取当前登录用户信息")
def current_user(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }
