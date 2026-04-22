"""
Phase 6.1 — Auth manager (MVP)
File-backed users + HS256 JWT-like tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path


DATA_DIR = Path("data")
USERS_PATH = DATA_DIR / "users.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _secret() -> bytes:
    return (os.getenv("SECRET_KEY") or "dev-secret-key").encode("utf-8")


def _load_users() -> list[dict]:
    if not USERS_PATH.exists():
        return []
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_users(users: list[dict]):
    USERS_PATH.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def list_users_by_tenant(tenant_id: str) -> list[dict]:
    return [u for u in _load_users() if u.get("tenant_id") == tenant_id]


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def register_user(email: str, password: str, tenant_id: str, name: str = "", role: str = "owner") -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    if len(password or "") < 6:
        raise ValueError("Password must be at least 6 characters")
    users = _load_users()
    if any(u.get("email") == email and u.get("tenant_id") == tenant_id for u in users):
        raise ValueError("User already exists for this tenant")
    salt = uuid.uuid4().hex
    user = {
        "id": uuid.uuid4().hex,
        "email": email,
        "name": name or email.split("@")[0],
        "tenant_id": tenant_id,
        "role": role if role in ("owner", "admin", "editor", "viewer") else "viewer",
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "created_at": int(time.time()),
    }
    users.append(user)
    _save_users(users)
    return {"id": user["id"], "email": user["email"], "name": user["name"], "tenant_id": tenant_id, "role": user["role"]}


def authenticate_user(email: str, password: str, tenant_id: str) -> dict | None:
    email = (email or "").strip().lower()
    users = _load_users()
    user = next((u for u in users if u.get("email") == email and u.get("tenant_id") == tenant_id), None)
    if not user:
        return None
    if _hash_password(password, user.get("salt", "")) != user.get("password_hash"):
        return None
    return {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "tenant_id": tenant_id, "role": user.get("role", "viewer")}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def create_token(user: dict, ttl_seconds: int = 60 * 60 * 24 * 7) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "tenant_id": user["tenant_id"],
        "role": user.get("role", "viewer"),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    h = _b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    p = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(_secret(), f"{h}.{p}".encode("utf-8"), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def verify_token(token: str) -> dict | None:
    try:
        h, p, s = token.split(".")
        expected = _b64url(hmac.new(_secret(), f"{h}.{p}".encode("utf-8"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, s):
            return None
        payload = json.loads(_b64url_decode(p).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

