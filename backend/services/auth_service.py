"""Account creation and login. Passwords are hashed with bcrypt — never
stored or logged in plain text. Signup is instant (no email verification
step)."""

import secrets

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
