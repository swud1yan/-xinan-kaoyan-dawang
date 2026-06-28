"""Phase 5 transfer information APIs."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.phase2_5 import TransferInfo, UserTransferAlert
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(tags=["Transfer"])
settings = get_settings()


class TransferAlertRequest(BaseModel):
    keywords: str = Field(..., min_length=1, max_length=200)
    provinces: str | None = Field(None, max_length=200)
    min_level: str | None = Field(None, max_length=10)
    max_score: int | None = Field(None, ge=0, le=500)
    is_active: bool = True


class TransferInfoRequest(BaseModel):
    schoolName: str = Field(..., min_length=1, max_length=100)
    major: str = Field(..., min_length=1, max_length=200)
    degreeType: str = "学硕"
    requirement: str | None = None
    minScore: int | None = None
    contact: str | None = None
    sourceUrl: str | None = None
    publishDate: str | None = None


def _require_admin(token: str) -> None:
    if token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="invalid admin token")


async def ensure_transfer_seed(db: AsyncSession) -> None:
    exists = (await db.execute(select(TransferInfo).limit(1))).scalar_one_or_none()
    if exists:
        return
    samples = [
        ("重庆邮电大学", "计算机科学与技术", "学硕", 315, "关注官网调剂公告，优先本科计算机相关背景。"),
        ("西南科技大学", "软件工程", "专硕", 300, "接收一志愿计算机、软件工程、电子信息方向考生。"),
        ("云南大学", "电子信息", "专硕", 320, "需通过国家A区线，复试含专业综合问答。"),
    ]
    for school, major, degree, score, req in samples:
        db.add(
            TransferInfo(
                school_name=school,
                major=major,
                degree_type=degree,
                min_score=score,
                requirement=req,
                contact="请以学校研招网为准",
                source_url="https://yz.chsi.com.cn/",
                publish_date=date.today(),
                is_active=True,
            )
        )
    await db.commit()


def _info_payload(item: TransferInfo) -> dict:
    return {
        "id": item.id,
        "schoolName": item.school_name,
        "schoolId": item.school_id,
        "major": item.major,
        "degreeType": item.degree_type,
        "requirement": item.requirement,
        "minScore": item.min_score,
        "contact": item.contact,
        "sourceUrl": item.source_url,
        "publishDate": item.publish_date.isoformat() if item.publish_date else None,
        "isActive": item.is_active,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
    }


def _alert_payload(item: UserTransferAlert) -> dict:
    return {
        "id": item.id,
        "keywords": item.keywords,
        "provinces": item.provinces,
        "minLevel": item.min_level,
        "maxScore": item.max_score,
        "isActive": item.is_active,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/transfer/infos")
async def transfer_infos(
    keyword: str | None = None,
    province: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_transfer_seed(db)
    stmt = select(TransferInfo).where(TransferInfo.is_active == True)  # noqa: E712
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(TransferInfo.school_name.like(like), TransferInfo.major.like(like), TransferInfo.requirement.like(like)))
    if province:
        stmt = stmt.where(TransferInfo.school_name.like(f"%{province}%"))
    items = (await db.execute(stmt.order_by(TransferInfo.publish_date.desc(), TransferInfo.created_at.desc()).limit(100))).scalars().all()
    return {"items": [_info_payload(i) for i in items]}


@router.get("/transfer/infos/{info_id}/ai-analysis")
async def transfer_ai_analysis(info_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(TransferInfo, info_id)
    if not item:
        raise HTTPException(status_code=404, detail="transfer info not found")
    score_text = user.estimated_score or "未填写"
    # Call DeepSeek for real analysis
    analysis = f"你的预估分数为{score_text}。若满足国家线，可重点核对该专业调剂要求，并提前准备本科成绩单、个人陈述和项目材料。"
    try:
        from app.config import get_settings
        import httpx
        st = get_settings()
        if st.DEEPSEEK_API_KEY:
            prompt = f"用户预估考研分数{score_text}，关注调剂：{item.school_name} {item.major} {item.degree_type}，要求{user.estimated_score or '不限'}分。请给出80字以内的调剂成功率分析和准备建议。"
            async with httpx.AsyncClient(timeout=12.0) as cl:
                r = await cl.post(f"{st.DEEPSEEK_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {st.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}, json={"model": st.DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 150, "temperature": 0.5})
                if r.status_code == 200: analysis = r.json()["choices"][0]["message"]["content"]
    except Exception: pass
    return {"info": _info_payload(item), "analysis": analysis}


@router.get("/transfer/infos/{info_id}")
async def transfer_info_detail(info_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(TransferInfo, info_id)
    if not item:
        raise HTTPException(status_code=404, detail="transfer info not found")
    return _info_payload(item)


@router.get("/transfer/alerts")
async def transfer_alerts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alerts = (
        await db.execute(select(UserTransferAlert).where(UserTransferAlert.user_id == user.id).order_by(UserTransferAlert.created_at.desc()))
    ).scalars().all()
    return {"items": [_alert_payload(a) for a in alerts]}


@router.post("/transfer/alerts")
async def create_transfer_alert(req: TransferAlertRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = UserTransferAlert(
        user_id=user.id,
        keywords=req.keywords,
        provinces=req.provinces,
        min_level=req.min_level,
        max_score=req.max_score,
        is_active=req.is_active,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _alert_payload(item)


@router.delete("/transfer/alerts/{alert_id}")
async def delete_transfer_alert(alert_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(UserTransferAlert, alert_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="alert not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


@router.get("/transfer/matches")
async def transfer_matches(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_transfer_seed(db)
    keyword = user.major or user.direction or ""
    stmt = select(TransferInfo).where(TransferInfo.is_active == True)  # noqa: E712
    if keyword:
        stmt = stmt.where(or_(TransferInfo.major.like(f"%{keyword}%"), TransferInfo.requirement.like(f"%{keyword}%")))
    items = (await db.execute(stmt.order_by(TransferInfo.publish_date.desc()).limit(30))).scalars().all()
    return {
        "items": [
            {**_info_payload(i), "matchScore": 88 if keyword and keyword in (i.major or "") else 70, "reason": "专业方向相关" if keyword else "可关注调剂信息"}
            for i in items
        ]
    }


@router.post("/admin/transfer/infos")
async def admin_create_transfer_info(
    req: TransferInfoRequest,
    token: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(token)
    publish_date = date.fromisoformat(req.publishDate[:10]) if req.publishDate else date.today()
    item = TransferInfo(
        school_name=req.schoolName,
        major=req.major,
        degree_type=req.degreeType,
        requirement=req.requirement,
        min_score=req.minScore,
        contact=req.contact,
        source_url=req.sourceUrl,
        publish_date=publish_date,
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _info_payload(item)
