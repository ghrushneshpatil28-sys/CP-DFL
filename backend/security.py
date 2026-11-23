"""Scrypt passwords and revocable opaque sessions. No default credentials."""
import hashlib
import hmac
import secrets
import time
import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from backend.models import AuditLog, Session, User

COOKIE = "lung_session"


def password_hash(password):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()
    return f"scrypt${salt.hex()}${value}"


def verify_password(password, encoded):
    try:
        _, salt, expected = encoded.split("$")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db, user, request, response):
    old = request.cookies.get(COOKIE)
    if old and (old_session := db.get(Session, token_hash(old))):
        db.delete(old_session)
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.add(Session(token_hash=token_hash(token), user_id=user.id, csrf_token=csrf,
                   expires_at=time.time() + 8 * 3600))
    audit(db, user, "auth.login")
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True,
                        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
                        samesite="strict", max_age=8 * 3600)
    return {"user": public_user(user, db), "csrf_token": csrf}


def get_db(request: Request):
    with request.app.state.sessions() as db:
        yield db


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE, "")
    session = db.get(Session, token_hash(token)) if token else None
    user = db.get(User, session.user_id) if session and session.expires_at > time.time() else None
    if not user or not user.active:
        raise HTTPException(401, "Authentication required or account disabled")
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(supplied, session.csrf_token):
            raise HTTPException(403, "CSRF token missing or invalid")
    request.state.auth_session = session
    return user


def require_role(role):
    def dependency(user=Depends(current_user)):
        if user.role != role:
            raise HTTPException(403, f"{role} role required")
        return user
    return dependency


admin = require_role("Admin")
doctor = require_role("Doctor")


def audit(db, actor, action, resource=None):
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action, resource=resource))


def public_user(user, db):
    from backend.models import DoctorProfile
    profile = db.get(DoctorProfile, user.id)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role,
            "active": user.active, "created_at": user.created_at,
            "profile": {k: getattr(profile, k) for k in ["specialty", "hospital", "registration"]} if profile else None}
