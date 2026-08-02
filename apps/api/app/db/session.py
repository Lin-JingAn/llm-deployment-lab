from collections.abc import Generator

from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    echo=False,
)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    为每次API请求提供独立数据库会话。
    """

    database_session = SessionLocal()

    try:
        yield database_session

    finally:
        database_session.close()


def check_database_connection() -> dict[str, str]:
    """
    检查数据库连接，并返回当前数据库和用户。
    """

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT "
                "current_database() AS database_name, "
                "current_user AS database_user"
            )
        ).mappings().one()

    return {
        "database_name": row["database_name"],
        "database_user": row["database_user"],
    }