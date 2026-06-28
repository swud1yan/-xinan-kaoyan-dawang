"""
分数线模型 — 对应前端 ScoreLine + School + Program
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ScoreLine(Base):
    __tablename__ = "score_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # 院校信息
    school_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    school_province: Mapped[str | None] = mapped_column(String(50))
    school_city: Mapped[str | None] = mapped_column(String(50))
    school_tags: Mapped[str | None] = mapped_column(String(200))  # 逗号分隔：985,211,双一流

    # 专业信息
    program_name: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str | None] = mapped_column(String(20))    # 学硕 / 专硕
    subjects: Mapped[str | None] = mapped_column(String(200))      # 考试科目

    # 招生信息
    planned_count: Mapped[int | None] = mapped_column(Integer)      # 计划招生
    admitted_count: Mapped[int | None] = mapped_column(Integer)     # 实际录取

    # 分数线
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    politics_score: Mapped[int | None] = mapped_column(Integer)
    english_score: Mapped[int | None] = mapped_column(Integer)
    biz1_score: Mapped[int | None] = mapped_column(Integer)        # 业务课一
    biz2_score: Mapped[int | None] = mapped_column(Integer)        # 业务课二

    # 备注
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
