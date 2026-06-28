"""
分数线路由 — GET /score-lines/schools  GET /score-lines?school=&program=
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.score_line import ScoreLine

router = APIRouter(prefix="/score-lines", tags=["分数线"])


@router.get("/schools")
async def list_schools(db: AsyncSession = Depends(get_db)):
    """获取所有有分数线数据的院校列表"""
    result = await db.execute(
        select(
            ScoreLine.school_name,
            ScoreLine.school_province,
            ScoreLine.school_city,
            ScoreLine.school_tags,
        ).distinct()
    )
    rows = result.all()
    # 去重
    seen = set()
    schools = []
    for row in rows:
        if row[0] not in seen:
            seen.add(row[0])
            schools.append({
                "name": row[0],
                "province": row[1],
                "city": row[2],
                "tags": row[3].split(",") if row[3] else [],
            })
    return schools


@router.get("/programs")
async def list_programs(
    school: str = Query(..., description="院校名称"),
    db: AsyncSession = Depends(get_db),
):
    """获取某院校的专业列表"""
    result = await db.execute(
        select(
            ScoreLine.program_name,
            ScoreLine.degree_type,
            ScoreLine.subjects,
            ScoreLine.planned_count,
            ScoreLine.admitted_count,
        )
        .where(ScoreLine.school_name == school)
        .distinct()
    )
    rows = result.all()
    return [
        {
            "name": row[0],
            "degreeType": row[1],
            "subjects": row[2],
            "plannedCount": row[3],
            "admittedCount": row[4],
        }
        for row in rows
    ]


@router.get("")
async def get_score_lines(
    school: str = Query(..., description="院校名称"),
    program: str = Query(..., description="专业名称"),
    db: AsyncSession = Depends(get_db),
):
    """获取某院校某专业的历年分数线"""
    result = await db.execute(
        select(ScoreLine)
        .where(
            ScoreLine.school_name == school,
            ScoreLine.program_name == program,
        )
        .order_by(ScoreLine.year.asc())
    )
    lines = result.scalars().all()

    return {
        "school": school,
        "program": program,
        "degreeType": lines[0].degree_type if lines else None,
        "subjects": lines[0].subjects if lines else None,
        "lines": [
            {
                "year": line.year,
                "total": line.total_score,
                "politics": line.politics_score,
                "english": line.english_score,
                "biz1": line.biz1_score,
                "biz2": line.biz2_score,
                "plannedCount": line.planned_count,
                "admittedCount": line.admitted_count,
            }
            for line in lines
        ],
    }


@router.post("/refresh")
async def refresh_score_lines(db: AsyncSession = Depends(get_db)):
    """触发分数线数据刷新（占位 — 需要配置爬虫后可用）"""
    # TODO: 实际爬取逻辑
    return {"message": "刷新任务已提交（当前为种子数据模式，未实际爬取）"}
