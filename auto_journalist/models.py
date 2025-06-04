import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class PlanEnum(enum.Enum):
    BASIC = "basic"
    PREMIUM = "premium"


class FrequencyEnum(enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class FactStatusEnum(enum.Enum):
    VERIFIED = "verified"
    DISPUTED = "disputed"
    NOT_VERIFIABLE = "not_verifiable"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    plan = Column(
        SAEnum(PlanEnum, name="plan"), nullable=False, default=PlanEnum.BASIC
    )

    preferences = relationship(
        "Preference", back_populates="user", cascade="all, delete-orphan"
    )
    user_sources = relationship(
        "UserSource", back_populates="user", cascade="all, delete-orphan"
    )


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String, nullable=False)
    frequency = Column(SAEnum(FrequencyEnum, name="frequency"), nullable=False)
    last_sent = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="preferences")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    is_social = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_sources = relationship(
        "UserSource", back_populates="source", cascade="all, delete-orphan"
    )


class UserSource(Base):
    __tablename__ = "user_sources"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    user = relationship("User", back_populates="user_sources")
    source = relationship("Source", back_populates="user_sources")

    __table_args__ = (
        sa.UniqueConstraint("user_id", "source_id", name="uix_user_source"),
    )


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    source = Column(String, nullable=False)
    raw_json = Column(JSONB, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    summary = relationship(
        "Summary", back_populates="article", uselist=False, cascade="all, delete-orphan"
    )


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    author = Column(String, nullable=True)
    publish_date = Column(DateTime, nullable=True)
    topic = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("Article", back_populates="summary")
    factcheck = relationship(
        "FactCheck", back_populates="summary", uselist=False, cascade="all, delete-orphan"
    )
    commentary = relationship(
        "Commentary", back_populates="summary", uselist=False, cascade="all, delete-orphan"
    )


class FactCheck(Base):
    __tablename__ = "factchecks"

    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey("summaries.id"), nullable=False, unique=True)
    status = Column(SAEnum(FactStatusEnum, name="factstatus"), nullable=False)
    citations = Column(JSONB, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    summary = relationship("Summary", back_populates="factcheck")


class Commentary(Base):
    __tablename__ = "commentaries"

    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey("summaries.id"), nullable=False, unique=True)
    commentary_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    summary = relationship("Summary", back_populates="commentary")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, unique=True, nullable=False)
    filename_html = Column(String, nullable=False)
    filename_txt = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StreamItem(Base):
    __tablename__ = "stream_items"

    id = Column(Integer, primary_key=True)
    summary_id = Column(
        Integer, ForeignKey("summaries.id"), nullable=False, unique=True
    )
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    summary = relationship("Summary")
