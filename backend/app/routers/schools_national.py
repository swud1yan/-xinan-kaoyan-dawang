"""
National schools router - search and detail for 150+ schools
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models.national import NationalSchool, NationalProgram, NationalScoreLine
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/schools", tags=["全国院校"])


@router.get("")
async def list_schools(
    province: str | None = Query(None),
    tag: str | None = Query(None),  # 985, 211, 双一流, C9
    school_type: str | None = Query(None),  # 综合, 理工, 师范...
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List/search national schools with filters"""
    query = select(NationalSchool)
    if province:
        query = query.where(NationalSchool.province == province)
    if tag:
        query = query.where(NationalSchool.tags.contains(tag))
    if school_type:
        query = query.where(NationalSchool.school_type == school_type)
    if search:
        query = query.where(NationalSchool.name.contains(search))

    # Count
    count_q = select(func.count()).select_from(NationalSchool)
    if province: count_q = count_q.where(NationalSchool.province == province)
    if tag: count_q = count_q.where(NationalSchool.tags.contains(tag))
    if school_type: count_q = count_q.where(NationalSchool.school_type == school_type)
    if search: count_q = count_q.where(NationalSchool.name.contains(search))
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(NationalSchool.name))
    schools = result.scalars().all()

    return {
        "total": total, "page": page, "pageSize": page_size,
        "schools": [{
            "id": s.id, "name": s.name, "province": s.province, "city": s.city,
            "tags": s.tags.split(",") if s.tags else [],
            "schoolType": s.school_type, "level": s.level,
        } for s in schools],
    }


@router.get("/provinces")
async def list_provinces(db: AsyncSession = Depends(get_db)):
    """Get all provinces with schools"""
    from sqlalchemy import distinct
    result = await db.execute(select(distinct(NationalSchool.province)).order_by(NationalSchool.province))
    return [r[0] for r in result.all()]


@router.get("/compare")
async def compare_schools(
    ids: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    id_list = [x.strip() for x in ids.split(",") if x.strip()]
    limit = 3 if (user.vip_level or 0) == 0 else 5 if (user.vip_level or 0) in (1, 17) else 10
    if len(id_list) > limit:
        raise HTTPException(status_code=403, detail=f"当前等级最多对比{limit}所院校")
    schools = []
    for school_id in id_list:
        school = await db.get(NationalSchool, school_id)
        if not school:
            continue
        programs = (await db.execute(select(NationalProgram).where(NationalProgram.school_id == school.id))).scalars().all()
        latest_line = None
        planned = None
        admitted = None
        if programs:
            lines = (await db.execute(select(NationalScoreLine).where(NationalScoreLine.program_id == programs[0].id).order_by(NationalScoreLine.year.desc()))).scalars().all()
            if lines:
                latest_line = {"year": lines[0].year, "total": lines[0].total_score}
                planned = lines[0].planned_count
                admitted = lines[0].admitted_count
        schools.append({
            "id": school.id,
            "name": school.name,
            "province": school.province,
            "city": school.city,
            "tags": school.tags.split(",") if school.tags else [],
            "schoolType": school.school_type,
            "level": school.level,
            "programCount": len(programs),
            "latestLine": latest_line,
            "plannedCount": planned,
            "admittedCount": admitted,
            "website": school.website,
        })
    return {"limit": limit, "schools": schools}


@router.get("/compare/ai-tip")
async def ai_compare_tip(
    ids: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if (user.vip_level or 0) not in (2, 3, 99):
        raise HTTPException(status_code=403, detail="AI对比建议需要金卡及以上VIP")
    data = await compare_schools(ids, user, db)
    names = "、".join(s["name"] for s in data["schools"])
    return {"tip": f"{names} 可以从城市、复试线稳定性和招生规模三项比较；优先选择与你专业方向匹配且复试线波动较小的院校。"}


@router.get("/unified/{exam_name}")
async def schools_by_exam_fast(
    exam_name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NationalProgram).where(NationalProgram.unified_name.contains(exam_name))
    )
    programs = result.scalars().all()
    data = []
    for p in programs:
        school = await db.get(NationalSchool, p.school_id)
        data.append({
            "programId": p.id, "programName": p.name, "degreeType": p.degree_type,
            "subjects": p.subjects,
            "schoolId": school.id if school else "", "schoolName": school.name if school else "",
            "province": school.province if school else "",
            "tags": school.tags.split(",") if school and school.tags else [],
        })
    return data


@router.get("/{school_id}")
async def get_school_detail(
    school_id: str,
    user_major: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get school detail with all programs and score lines"""
    school = await db.get(NationalSchool, school_id)
    if not school:
        raise HTTPException(404, "School not found")

    result = await db.execute(
        select(NationalProgram).where(NationalProgram.school_id == school_id)
    )
    programs = result.scalars().all()

    # If only 1-2 programs (seed data), enrich with scraped/generated data
    if len(programs) <= 2:
        try:
            from app.services.school_scraper import scrape_school_programs
            extra = await scrape_school_programs(school.name, user_major)
            # Add extra programs that don't exist yet
            existing_names = {p.name for p in programs}
            import uuid
            for ep in extra:
                if ep["name"] not in existing_names:
                    pid = str(uuid.uuid4())
                    p = NationalProgram(
                        id=pid, school_id=school_id,
                        name=ep["name"], degree_type=ep.get("degree", "学硕"),
                        subjects=ep.get("subjects"),
                        is_unified=ep.get("is_unified", False),
                        unified_name=ep.get("unified_name"),
                        planned_count=ep.get("planned"),
                        admitted_count=ep.get("admitted"),
                    )
                    db.add(p)
                    for line in ep.get("lines", []):
                        db.add(NationalScoreLine(
                            program_id=pid, year=line["year"],
                            total_score=line["total"], politics_score=line.get("pol"),
                            english_score=line.get("eng"), biz1_score=line.get("b1"),
                            biz2_score=line.get("b2"),
                        ))
                    existing_names.add(ep["name"])
            await db.commit()
            # Re-fetch programs
            result = await db.execute(
                select(NationalProgram).where(NationalProgram.school_id == school_id)
            )
            programs = result.scalars().all()
        except Exception as e:
            logging.warning(f"Scrape fallback for {school.name}: {e}")

    programs_data = []
    for p in programs:
        lines_result = await db.execute(
            select(NationalScoreLine)
            .where(NationalScoreLine.program_id == p.id)
            .order_by(NationalScoreLine.year.desc())
        )
        lines = lines_result.scalars().all()
        programs_data.append({
            "id": p.id, "name": p.name, "degreeType": p.degree_type,
            "subjects": p.subjects, "isUnified": p.is_unified,
            "unifiedName": p.unified_name,
            "plannedCount": p.planned_count, "admittedCount": p.admitted_count,
            "lines": [{
                "year": l.year, "total": l.total_score,
                "politics": l.politics_score, "english": l.english_score,
                "biz1": l.biz1_score, "biz2": l.biz2_score,
                "plannedCount": l.planned_count, "admittedCount": l.admitted_count,
            } for l in lines],
        })

    return {
        "id": school.id, "name": school.name, "province": school.province,
        "city": school.city, "tags": school.tags.split(",") if school.tags else [],
        "schoolType": school.school_type, "level": school.level,
        "website": school.website,
        "programs": programs_data,
    }


@router.post("/{school_id}/scrape")
async def scrape_school(school_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger scraping for a school"""
    school = await db.get(NationalSchool, school_id)
    if not school:
        raise HTTPException(404, "School not found")
    from app.services.school_scraper import scrape_school_programs
    programs = await scrape_school_programs(school.name)
    return {"school": school.name, "programsFound": len(programs), "programs": programs}


@router.get("/unified/{exam_name}")
async def schools_by_exam(
    exam_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Find all schools/programs that use a specific unified exam (e.g. 408)"""
    result = await db.execute(
        select(NationalProgram).where(NationalProgram.unified_name.contains(exam_name))
    )
    programs = result.scalars().all()
    data = []
    for p in programs:
        school = await db.get(NationalSchool, p.school_id)
        data.append({
            "programId": p.id, "programName": p.name, "degreeType": p.degree_type,
            "subjects": p.subjects,
            "schoolId": school.id if school else "", "schoolName": school.name if school else "",
            "province": school.province if school else "",
            "tags": school.tags.split(",") if school and school.tags else [],
        })
    return data
