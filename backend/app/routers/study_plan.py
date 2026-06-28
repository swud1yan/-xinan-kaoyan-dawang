"""Phase 5 AI study plan APIs."""
import json
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import StudyPlan
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/study-plan", tags=["Study Plan"])


class GeneratePlanRequest(BaseModel):
    type: str = Field("weekly", max_length=10)
    goal: str | None = Field(None, max_length=200)
    days: int = Field(7, ge=1, le=14)


class TaskUpdateRequest(BaseModel):
    completed: bool = True


def _week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def _plan_payload(plan: StudyPlan) -> dict:
    return {
        "id": plan.id,
        "type": plan.type,
        "weekStart": plan.week_start.isoformat() if plan.week_start else None,
        "date": plan.date.isoformat() if plan.date else None,
        "content": json.loads(plan.content or "{}"),
        "generatedBy": plan.generated_by,
        "isCompleted": plan.is_completed,
        "completionRate": plan.completion_rate,
        "createdAt": plan.created_at.isoformat() if plan.created_at else None,
    }


def _make_tasks(user: User, goal: str | None, days: int) -> list[dict]:
    subjects = [user.major or "专业课", "英语", "政治", "复盘"]
    tasks = []
    for i in range(days):
        day = date.today() + timedelta(days=i)
        for j, subject in enumerate(subjects[:3], start=1):
            tasks.append(
                {
                    "id": str(uuid.uuid4()),
                    "date": day.isoformat(),
                    "title": f"{subject} 第{j}轮推进",
                    "detail": goal or "完成一个小节学习并记录错题",
                    "minutes": 45 if subject != "复盘" else 25,
                    "completed": False,
                }
            )
    return tasks


async def _latest_plan(db: AsyncSession, user_id: str) -> StudyPlan | None:
    return (
        await db.execute(select(StudyPlan).where(StudyPlan.user_id == user_id).order_by(StudyPlan.created_at.desc()).limit(1))
    ).scalar_one_or_none()


def _recalc(plan: StudyPlan) -> None:
    content = json.loads(plan.content or "{}")
    tasks = content.get("tasks", [])
    done = len([t for t in tasks if t.get("completed")])
    total = max(len(tasks), 1)
    plan.completion_rate = round(done / total, 3)
    plan.is_completed = done >= total
    plan.content = json.dumps(content, ensure_ascii=False)


@router.post("/generate")
async def generate_plan(
    req: GeneratePlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    content = {
        "goal": req.goal or f"围绕{user.target_school or '目标院校'}稳步推进",
        "summary": "本计划按小任务拆解，优先保障真题、复盘和错题整理。",
        "tasks": _make_tasks(user, req.goal, req.days),
    }
    plan = StudyPlan(
        user_id=user.id,
        type=req.type if req.type in ("weekly", "daily") else "weekly",
        week_start=_week_start(today),
        date=today,
        content=json.dumps(content, ensure_ascii=False),
        generated_by="ai",
        is_completed=False,
        completion_rate=0,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_payload(plan)


@router.get("/current")
async def current_plan(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await _latest_plan(db, user.id)
    return {"plan": _plan_payload(plan) if plan else None}


@router.get("/history")
async def plan_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plans = (
        await db.execute(select(StudyPlan).where(StudyPlan.user_id == user.id).order_by(StudyPlan.created_at.desc()).limit(30))
    ).scalars().all()
    return {"items": [_plan_payload(p) for p in plans]}


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _latest_plan(db, user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    content = json.loads(plan.content or "{}")
    found = False
    for task in content.get("tasks", []):
        if task.get("id") == task_id:
            task["completed"] = req.completed
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="task not found")
    plan.content = json.dumps(content, ensure_ascii=False)
    _recalc(plan)
    await db.commit()
    return _plan_payload(plan)


@router.get("/weekly-report/latest")
async def latest_weekly_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await weekly_report(user, db)


@router.get("/weekly-report")
async def weekly_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await _latest_plan(db, user.id)
    if not plan:
        return {"report": None}
    content = json.loads(plan.content or "{}")
    tasks = content.get("tasks", [])
    done = len([t for t in tasks if t.get("completed")])
    return {
        "report": {
            "planId": plan.id,
            "completionRate": plan.completion_rate,
            "doneTasks": done,
            "totalTasks": len(tasks),
            "summary": "完成率不错时继续保持；若低于预期，建议明天只保留三件最关键任务。",
        }
    }
