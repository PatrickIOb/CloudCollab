import uuid
from jose import JWTError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.auth.jwt import decode_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Token has no sub")

        user_id = uuid.UUID(sub)
    except (JWTError, TypeError, ValueError) as e:
        raise HTTPException(status_code=401, detail=f"Token error: {e}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:

    """
    Wie get_current_user, aber:
    - kein Authorization Header -> None (kein Fehler)
    - gültiger Token -> User
    - ungültiger Token -> 401
    """

    auth = request.headers.get("Authorization")

    if not auth:
        return None

    # Erwartet: "Bearer <token>"
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = parts[1]

    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Token has no sub")
        user_id = uuid.UUID(sub)
    except (JWTError, TypeError, ValueError) as e:
        raise HTTPException(status_code=401, detail=f"Token error: {e}")

    user = db.query(User).filter(User.id == user_id).first()

    return user
