"""Client config APIs."""
from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["配置"])

MOTTOS = [
    "慢慢来，比较快。",
    "今天多做一点，明天少慌一点。",
    "真正拉开差距的，是稳定重复。",
    "把难题拆小，把时间用实。",
    "你不是在等状态，你是在训练状态。",
]


@router.get("/exam-date")
async def get_exam_date():
    exam_date = date(2026, 12, 26)
    today = date.today()
    return {
        "exam_date": exam_date.isoformat(),
        "days_remaining": max(0, (exam_date - today).days),
        "title": "2027年全国硕士研究生招生考试",
    }


@router.get("/motto")
async def get_daily_motto():
    idx = date.today().toordinal() % len(MOTTOS)
    return {"motto": MOTTOS[idx]}
