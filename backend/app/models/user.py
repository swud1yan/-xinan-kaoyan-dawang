"""
User model - complete user profile
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Core identity
    dawang_id: Mapped[str] = mapped_column(
        String(15), unique=True, nullable=False, index=True
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(11))

    # Profile
    avatar: Mapped[str | None] = mapped_column(String(500))
    school: Mapped[str | None] = mapped_column(String(100))

    # Gamification
    level: Mapped[int] = mapped_column(Integer, default=1)
    vip_level: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    vip_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monthly_coins: Mapped[int] = mapped_column(Integer, default=0)
    monthly_coins_max: Mapped[int] = mapped_column(Integer, default=100)
    purchased_coins: Mapped[int] = mapped_column(Integer, default=0)
    coins_reset_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deep_think_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sign_in_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_sign_in_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pomodoro_count: Mapped[int] = mapped_column(Integer, default=0)

    # Registration survey
    grade: Mapped[str | None] = mapped_column(String(20))
    major: Mapped[str | None] = mapped_column(String(100))
    has_target: Mapped[bool] = mapped_column(Boolean, default=False)
    target_school: Mapped[str | None] = mapped_column(String(100))
    direction: Mapped[str | None] = mapped_column(String(50))
    progress: Mapped[str | None] = mapped_column(String(30))
    estimated_score: Mapped[str | None] = mapped_column(String(20))
    study_style: Mapped[str | None] = mapped_column(String(20))

    # Undergraduate
    undergrad_province: Mapped[str | None] = mapped_column(String(20))
    undergrad_school: Mapped[str | None] = mapped_column(String(100))
    undergrad_private: Mapped[bool] = mapped_column(Boolean, default=False)

    # Admin
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_whitelist: Mapped[bool] = mapped_column(Boolean, default=False)
    token_used: Mapped[int] = mapped_column(Integer, default=0)
    token_limit: Mapped[int] = mapped_column(Integer, default=100000)

    # Tracking
    dawang_id_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_ip: Mapped[str | None] = mapped_column(String(50))
    last_login_ip: Mapped[str | None] = mapped_column(String(50))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    posts = relationship("Post", back_populates="author", lazy="dynamic")
    comments = relationship("Comment", back_populates="author", lazy="dynamic")
    likes = relationship("Like", back_populates="user", lazy="dynamic")
    chat_messages = relationship("ChatMessage", back_populates="user", lazy="dynamic")
