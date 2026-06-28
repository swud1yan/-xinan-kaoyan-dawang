"""
真题模型 — 对应前端 ExamPaper
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200))  # 来源

    # 真题内容（文本形式，无需上传文件）
    content: Mapped[str | None] = mapped_column(Text)        # 题目内容/要点
    answer: Mapped[str | None] = mapped_column(Text)         # 答案与解析

    # 文件存储（可选，用户也可以上传PDF）
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_url: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)

    download_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
