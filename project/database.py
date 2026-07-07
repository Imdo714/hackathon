import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# .env 파일을 읽어옵니다.
load_dotenv()

# .env 파일에서 PostgreSQL 접속 주소를 가져옵니다.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI 의존성 주입을 위한 DB 세션 생성 제너레이터입니다.
    요청이 끝날 때 세션을 안전하게 닫습니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
