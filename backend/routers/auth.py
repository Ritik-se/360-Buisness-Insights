import os
import re
import uuid

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "avatars")
AVATAR_DIR = os.path.abspath(AVATAR_DIR)
os.makedirs(AVATAR_DIR, exist_ok=True)
MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    token = authorization.removeprefix("Bearer ").strip()
    user = db.query(User).filter(User.session_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return user


def _user_out(user: User) -> dict:
    return {
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "avatar_url": f"/api/auth/avatar/{user.id}" if user.avatar_path else None,
    }


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

    return {"token": user.session_token, **_user_out(user)}


@router.post("/login")
def login(body: dict = Body(...), db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    user = db.query(User).filter(User.email == email).first()
    if not user or not auth_service.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    user.session_token = auth_service.generate_session_token()
    db.commit()

    return {"token": user.session_token, **_user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.put("/profile")
def update_profile(body: dict = Body(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    user.name = name[:100]
    db.commit()
    return _user_out(user)


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="Upload a PNG, JPG, WEBP or GIF image.")

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Image exceeds the 3MB limit.")

    old_path = user.avatar_path
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(AVATAR_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(contents)

    user.avatar_path = stored_path
    db.commit()

    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except OSError:
            pass

    return _user_out(user)


@router.get("/avatar/{user_id}")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_path or not os.path.exists(user.avatar_path):
        raise HTTPException(status_code=404, detail="No avatar set.")
    return FileResponse(user.avatar_path)
