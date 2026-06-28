"""
Subject catalog and undergrad schools
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.national import SubjectCatalog, UndergradSchool

router = APIRouter(prefix="/catalog", tags=["目录"])


@router.get("/subjects")
async def get_subjects(db: AsyncSession = Depends(get_db)):
    """Get subject tree (一级→二级)"""
    result = await db.execute(
        select(SubjectCatalog).order_by(SubjectCatalog.code)
    )
    items = result.scalars().all()

    tree = []
    # First pass: level 1
    for item in items:
        if item.level == 1:
            tree.append({
                "code": item.code, "name": item.name, "level": 1,
                "children": [],
            })

    # Second pass: level 2
    name_to_idx = {t["name"]: i for i, t in enumerate(tree)}
    for item in items:
        if item.level == 2:
            # Find parent by code prefix (e.g. "0812" → parent "08")
            parent_code = item.code[:2] if item.code else ""
            # Try to find matching level-1
            for t in tree:
                if t["code"] == parent_code:
                    t["children"].append({
                        "code": item.code, "name": item.name, "level": 2,
                    })
                    break
    return tree


@router.get("/undergrad-schools")
async def get_undergrad_schools(
    province: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get undergrad schools in 云贵川渝"""
    query = select(UndergradSchool).order_by(UndergradSchool.province, UndergradSchool.name)
    if province:
        query = query.where(UndergradSchool.province == province)
    result = await db.execute(query)
    schools = result.scalars().all()

    # Group by province
    by_province = {}
    for s in schools:
        if s.province not in by_province:
            by_province[s.province] = []
        by_province[s.province].append({
            "name": s.name, "city": s.city, "type": s.school_type,
        })

    return {
        "provinces": list(by_province.keys()),
        "schools": by_province,
    }
