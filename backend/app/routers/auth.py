from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.database import get_db
from app.models.user import User

from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import Token

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user

from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    identifier: str  # email OR username
    password: str


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    # username unique
    existing_username = db.scalar(select(User).where(User.username == data.username))
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already taken")

    # email unique
    existing_email = db.scalar(select(User).where(User.email == data.email))
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(data.password)

    user = User(
        email=data.email,
        password_hash=pw_hash,
        display_name=data.display_name,
        username=data.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    ident = data.identifier.strip()

    # Find by email OR username
    stmt = select(User).where(or_(User.email == ident, User.username == ident))
    user = db.scalar(stmt)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user_id=user.id)
    return Token(access_token=token)
