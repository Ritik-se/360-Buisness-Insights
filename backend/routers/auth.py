import re
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/status")
def auth_status():
    return {"email_configured": auth_service.is_email_configured()}


@router.post("/signup")
def signup(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    user = db.query(User).filter(User.email == email).first()
    if user and user.is_verified:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try signing in.")

    otp = auth_service.generate_otp()
    if user:
        user.password_hash = auth_service.hash_password(password)
        user.otp_code = otp
        user.otp_expires_at = auth_service.otp_expiry()
    else:
        user = User(
            email=email,
            password_hash=auth_service.hash_password(password),
            otp_code=otp,
            otp_expires_at=auth_service.otp_expiry(),
        )
        db.add(user)
    db.commit()

    try:
        auth_service.send_otp_email(email, otp)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"message": "Verification code sent to your email."}


@router.post("/resend-otp")
def resend_otp(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or user.is_verified:
        raise HTTPException(status_code=404, detail="No pending signup found for this email.")

    otp = auth_service.generate_otp()
    user.otp_code = otp
    user.otp_expires_at = auth_service.otp_expiry()
    db.commit()

    try:
        auth_service.send_otp_email(email, otp)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"message": "Verification code resent."}


@router.post("/verify-otp")
def verify_otp(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    otp = (body.get("otp") or "").strip()

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.otp_code:
        raise HTTPException(status_code=400, detail="No verification pending for this email.")
    if user.otp_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This code has expired. Request a new one.")
    if otp != user.otp_code:
        raise HTTPException(status_code=400, detail="Incorrect code.")

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    user.session_token = auth_service.generate_session_token()
    db.commit()

    return {"token": user.session_token, "email": user.email}


@router.post("/login")
def login(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_verified or not auth_service.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    user.session_token = auth_service.generate_session_token()
    db.commit()

    return {"token": user.session_token, "email": user.email}
