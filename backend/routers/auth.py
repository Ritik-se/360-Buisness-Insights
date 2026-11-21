import re

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/signup")
def signup(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try signing in.")

    user = User(email=email, password_hash=auth_service.hash_password(password),
                session_token=auth_service.generate_session_token())
    db.add(user)
    db.commit()

    return {"token": user.session_token, "email": user.email}


@router.post("/login")
def login(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    user = db.query(User).filter(User.email == email).first()
    if not user or not auth_service.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    user.session_token = auth_service.generate_session_token()
    db.commit()

    return {"token": user.session_token, "email": user.email}
