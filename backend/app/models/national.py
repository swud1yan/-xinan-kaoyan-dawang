"""
National school models - 全国院校 + 专业 + 分数线
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class NationalSchool(Base):
    __tablename__ = "national_schools"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    province: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[str | None] = mapped_column(String(200))  # 985,211,双一流,自划线,C9
    school_type: Mapped[str | None] = mapped_column(String(20))  # 综合/理工/师范/医药/农林/政法/语言/艺术/体育/民族
    level: Mapped[str | None] = mapped_column(String(10))  # 教育部直属/省属/部省合建
    website: Mapped[str | None] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NationalProgram(Base):
    __tablename__ = "national_programs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("national_schools.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str | None] = mapped_column(String(20))  # 学硕/专硕
    subjects: Mapped[str | None] = mapped_column(String(300))  # 考试科目，逗号分隔
    is_unified: Mapped[bool] = mapped_column(
        default=False
    )  # 是否统考（如408统考）
    unified_name: Mapped[str | None] = mapped_column(
        String(50)
    )  # 统考名称（如"408计算机学科专业基础综合"）
    planned_count: Mapped[int | None] = mapped_column(Integer)
    admitted_count: Mapped[int | None] = mapped_column(Integer)


class NationalScoreLine(Base):
    __tablename__ = "national_score_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("national_programs.id"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    politics_score: Mapped[int | None] = mapped_column(Integer)
    english_score: Mapped[int | None] = mapped_column(Integer)
    biz1_score: Mapped[int | None] = mapped_column(Integer)
    biz2_score: Mapped[int | None] = mapped_column(Integer)
    planned_count: Mapped[int | None] = mapped_column(Integer)
    admitted_count: Mapped[int | None] = mapped_column(Integer)


class SubjectCatalog(Base):
    __tablename__ = "subject_catalog"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(36), index=True
    )  # None = 一级学科
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(10))  # 学科代码，如 0812
    level: Mapped[int] = mapped_column(
        Integer, default=1
    )  # 1=一级, 2=二级


class UndergradSchool(Base):
    __tablename__ = "undergrad_schools"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 重庆/四川/云南/贵州
    city: Mapped[str | None] = mapped_column(String(50))
    school_type: Mapped[str | None] = mapped_column(String(20))
