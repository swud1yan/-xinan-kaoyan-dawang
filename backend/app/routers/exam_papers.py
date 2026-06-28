"""
真题路由 — 真题列表 / 上传 / 下载
"""
import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.exam_paper import ExamPaper

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

router = APIRouter(prefix="/exam-papers", tags=["真题"])


@router.get("")
async def list_papers(
    subject: str | None = Query(None, description="科目筛选"),
    year: int | None = Query(None, description="年份筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取真题列表"""
    query = select(ExamPaper).order_by(ExamPaper.year.desc(), ExamPaper.subject.asc())

    if subject:
        query = query.where(ExamPaper.subject == subject)
    if year:
        query = query.where(ExamPaper.year == year)

    result = await db.execute(query)
    papers = result.scalars().all()

    return [
        {
            "id": p.id,
            "subject": p.subject,
            "year": p.year,
            "title": p.title,
            "source": p.source,
            "hasContent": bool(p.content),
            "hasAnswer": bool(p.answer),
            "fileUrl": p.file_url,
            "fileSize": p.file_size,
            "downloadCount": p.download_count,
        }
        for p in papers
    ]


@router.get("/subjects")
async def list_subjects(db: AsyncSession = Depends(get_db)):
    """获取所有科目列表"""
    from sqlalchemy import distinct
    result = await db.execute(select(distinct(ExamPaper.subject)))
    return [row[0] for row in result.all()]


@router.get("/years")
async def list_years(db: AsyncSession = Depends(get_db)):
    """获取所有年份列表"""
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(ExamPaper.year)).order_by(ExamPaper.year.desc())
    )
    return [row[0] for row in result.all()]


@router.get("/{paper_id}")
async def get_paper_detail(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单条真题的完整内容（含题目+答案）"""
    result = await db.execute(select(ExamPaper).where(ExamPaper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "真题不存在")
    return {
        "id": paper.id,
        "subject": paper.subject,
        "year": paper.year,
        "title": paper.title,
        "source": paper.source,
        "content": paper.content,
        "answer": paper.answer,
        "fileUrl": paper.file_url,
        "fileSize": paper.file_size,
        "downloadCount": paper.download_count,
    }


@router.post("/upload")
async def upload_paper(
    subject: str = Query(...),
    year: int = Query(...),
    title: str = Query(...),
    source: str | None = Query(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传真题文件（PDF 或图片）"""
    # 检查文件类型
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(400, f"不支持的文件类型: {ext}，仅支持 PDF/图片")

    # 保存文件
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 数据库记录
    paper = ExamPaper(
        subject=subject,
        year=year,
        title=title,
        source=source,
        file_path=file_path,
        file_url=f"/exam-papers/download/{filename}",
        file_size=len(content),
    )
    db.add(paper)
    await db.flush()
    await db.refresh(paper)

    return {
        "id": paper.id,
        "subject": paper.subject,
        "year": paper.year,
        "title": paper.title,
        "fileUrl": paper.file_url,
        "fileSize": paper.file_size,
    }


@router.get("/download/{filename}")
async def download_paper(filename: str, db: AsyncSession = Depends(get_db)):
    """下载真题文件"""
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 安全检查：防止路径遍历
    real_path = os.path.realpath(file_path)
    upload_real = os.path.realpath(UPLOAD_DIR)
    if not real_path.startswith(upload_real):
        raise HTTPException(403, "禁止访问")

    if not os.path.isfile(real_path):
        raise HTTPException(404, "文件不存在")

    # 更新下载计数
    result = await db.execute(
        select(ExamPaper).where(ExamPaper.file_url == f"/exam-papers/download/{filename}")
    )
    paper = result.scalar_one_or_none()
    if paper:
        paper.download_count += 1

    return FileResponse(real_path)
