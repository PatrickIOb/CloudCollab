from app.database import engine
from app.models import Base
import app.models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
