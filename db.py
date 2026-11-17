from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    traveller: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    budget_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
DatabaseSession = Session


def create_tables() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        logger.error("Database schema initialization failed")
        raise RuntimeError("Database schema initialization failed") from None


def check_database_connection() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.error("Database connection check failed")
        raise RuntimeError("Database connection check failed") from None


def get_db() -> Generator[DatabaseSession, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def dispose_database_engine() -> None:
    engine.dispose()
