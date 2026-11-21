"""Email + OTP account creation and login. Passwords are hashed with bcrypt —
never stored or logged in plain text. OTP codes are sent via Resend's email
API and expire after 10 minutes; a code is single-use (cleared once verified)."""

import os
import secrets
from datetime import datetime, timedelta

import bcrypt
import requests

OTP_TTL_MINUTES = 10
RESEND_API_URL = "https://api.resend.com/emails"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)


def is_email_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def send_otp_email(to_email: str, otp: str) -> None:
    """Sends the OTP via Resend. Raises RuntimeError with a clear message on
    any failure (missing key, Resend error) so the caller can surface it."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Email sending isn't configured. Set RESEND_API_KEY on the backend to enable account signup."
        )

    from_address = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": f"Business Insights 360 <{from_address}>",
            "to": [to_email],
            "subject": "Your verification code",
            "html": (
                f"<p>Your verification code is:</p>"
                f"<h2 style='letter-spacing:4px'>{otp}</h2>"
                f"<p>This code expires in {OTP_TTL_MINUTES} minutes.</p>"
            ),
        },
        timeout=15,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Could not send the verification email: {response.text}")
