from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import RefreshToken, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": subject, "type": "access", "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


def create_refresh_token(db: Session, user: User) -> str:
    jti = uuid4().hex
    expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires, revoked=False))
    db.commit()
    return jwt.encode(
        {"sub": user.email, "type": "refresh", "jti": jti, "exp": expires},
        settings.secret_key,
        algorithm="HS256",
    )


def issue_token_pair(db: Session, user: User) -> dict:
    return {
        "access_token": create_access_token(user.email),
        "refresh_token": create_refresh_token(db, user),
        "token_type": "bearer",
    }


def rotate_refresh_token(db: Session, refresh_token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise credentials_exception
        email = payload.get("sub")
        jti = payload.get("jti")
        if not email or not jti:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not stored or stored.revoked or stored.expires_at < datetime.utcnow():
        raise credentials_exception

    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        raise credentials_exception

    stored.revoked = True
    db.commit()
    return issue_token_pair(db, user)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") not in {None, "access"}:
            raise credentials_exception
        email = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role not in {"admin", "engineer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user
