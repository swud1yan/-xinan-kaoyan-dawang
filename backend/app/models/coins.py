"""Coins, VIP, Redeem, Sign-in, XP models"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RedeemCode(Base):
    __tablename__ = "redeem_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)  # silver|gold|black|yanwang|coin_pack
    product_id: Mapped[str | None] = mapped_column(String(50))
    vip_level: Mapped[int | None] = mapped_column(Integer)
    vip_days: Mapped[int | None] = mapped_column(Integer)
    coins: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(50), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[str | None] = mapped_column(String(36))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RedeemHistory(Base):
    __tablename__ = "redeem_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20))
    product_type: Mapped[str] = mapped_column(String(20))
    product_name: Mapped[str] = mapped_column(String(100))
    coins_added: Mapped[int] = mapped_column(Integer, default=0)
    vip_level_before: Mapped[int] = mapped_column(Integer, default=0)
    vip_level_after: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SignInRecord(Base):
    __tablename__ = "sign_in_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    streak_day: Mapped[int] = mapped_column(Integer, default=0)
    bonus_type: Mapped[str | None] = mapped_column(String(20))  # coins|vip_trial|badge|avatar_frame
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class XpHistory(Base):
    __tablename__ = "xp_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # sign_in|post|comment|like_give|like_receive|pomodoro_25|pomodoro_45
    description: Mapped[str] = mapped_column(String(200))
    related_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
