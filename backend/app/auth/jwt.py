import os 
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from uuid import UUID

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "240"))  # Default to 4 hours

def create_access_token(user_id: UUID) -> str:
    # Create token and define token expiration time
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),   # subject
        "iat": int(now.timestamp()),  # issued at
        "exp": int(expire.timestamp()) # expiry
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return token

def decode_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        # FastAPI Route fängt später diese Fehler ab
        raise e

