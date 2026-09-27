import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuthToken, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{digest}"


def verify_password(password, stored):
    salt, expected = stored.split(":")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(expected, actual)


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(db, user):
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            digest=token_digest(token),
            user_id=user.id,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
        )
    )
    db.commit()
    return token


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    token = db.get(AuthToken, token_digest(credentials.credentials)) if credentials else None
    if token is None or datetime.fromisoformat(token.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Faça login para continuar.")
    return db.get(User, token.user_id)


def manager(user: User = Depends(current_user)):
    if user.role != "manager":
        raise HTTPException(403, "Ação exclusiva do gestor.")
    return user
