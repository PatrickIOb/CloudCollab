# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User  

from app.schemas.user import UserCreate, UserLogin, UserOut
from app.schemas.auth import Token

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user # Aktuellen User zurückgeben

@router.post("/register", response_model=UserOut, status_code=201)
#User registieren

def register(data: UserCreate, db: Session = Depends(get_db)):
    # Email eindeutigkeit prüfen
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # password hashen
    pw_hash = hash_password(data.password)

    # user speichern mit gehashtem passwort 
    user = User(
        email=data.email,
        password_hash=pw_hash,
        display_name=data.display_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
#User login

def login(data: UserLogin, db: Session = Depends(get_db)):
    # User finden
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # User Passwort prüfen 
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Token erstellen
    token = create_access_token(user_id=user.id)

    return Token(access_token=token)
