"""Daily question APIs."""
import json
import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import ErrorNote, Question, UserAnswer
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.xp_service import add_xp

router = APIRouter(tags=["每日一题"])

SEED_QUESTIONS = [
    ("408", "数据结构", "single_choice", 3, "下列排序算法中，最好情况下时间复杂度为 O(n) 的是？", ["A. 快速排序", "B. 冒泡排序", "C. 堆排序", "D. 简单选择排序"], "B", "冒泡排序在已有序时只需一趟扫描，最好情况为 O(n)。", 2021, "408统考"),
    ("408", "组成原理", "single_choice", 2, "CPU 中用于暂存下一条指令地址的寄存器是？", ["A. IR", "B. MAR", "C. PC", "D. MDR"], "C", "PC 程序计数器保存下一条将要执行的指令地址。", 2020, "408统考"),
    ("math", "高等数学", "single_choice", 2, "若 f'(x)>0，则 f(x) 在该区间内通常表现为？", ["A. 单调递增", "B. 单调递减", "C. 恒为0", "D. 不连续"], "A", "导数大于0说明函数在区间内单调递增。", 2019, "数学真题"),
    ("math", "线性代数", "single_choice", 3, "n 阶矩阵 A 可逆的充要条件是？", ["A. |A|=0", "B. rank(A)<n", "C. |A|≠0", "D. A 有零行"], "C", "方阵可逆当且仅当行列式不为0。", 2022, "数学真题"),
    ("politics", "马原", "single_choice", 2, "马克思主义哲学认为，实践是认识的？", ["A. 唯一内容", "B. 来源和检验标准", "C. 最终形式", "D. 主观想象"], "B", "实践是认识的来源，也是检验真理的唯一标准。", 2023, "政治真题"),
    ("politics", "史纲", "single_choice", 2, "新文化运动高举的两面旗帜是民主和？", ["A. 科学", "B. 富强", "C. 共和", "D. 法治"], "A", "新文化运动提倡民主与科学。", 2020, "政治真题"),
    ("english", "阅读", "single_choice", 2, "单词 abundant 最接近的含义是？", ["A. 稀少的", "B. 充足的", "C. 昂贵的", "D. 脆弱的"], "B", "abundant 表示大量的、充足的。", 2021, "英语真题"),
    ("english", "词汇", "single_choice", 2, "Which word means 'to make something better'?", ["A. improve", "B. ignore", "C. imply", "D. import"], "A", "improve 表示改善、提高。", 2018, "英语真题"),
]


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=200)


async def ensure_question_seed(db: AsyncSession) -> None:
    count = (await db.execute(select(func.count()).select_from(Question))).scalar() or 0
    if count:
        return
    for subject, sub, qtype, diff, content, options, answer, explanation, year, source in SEED_QUESTIONS:
        db.add(
            Question(
                subject=subject,
                sub_subject=sub,
                type=qtype,
                difficulty=diff,
                content=content,
                options=json.dumps(options, ensure_ascii=False),
                answer=answer,
                explanation=explanation,
                year=year,
                source=source,
            )
        )
    await db.commit()


def _question_payload(q: Question, answer: UserAnswer | None = None) -> dict:
    options = json.loads(q.options) if q.options else None
    data = {
        "id": q.id,
        "subject": q.subject,
        "subSubject": q.sub_subject,
        "type": q.type,
        "difficulty": q.difficulty,
        "content": q.content,
        "options": options,
        "year": q.year,
        "source": q.source,
        "usageCount": q.usage_count,
        "correctRate": round((q.correct_count or 0) / max(q.usage_count or 0, 1), 3),
    }
    if answer:
        data.update({
            "answered": True,
            "userChoice": answer.user_choice,
            "isCorrect": answer.is_correct,
            "answer": q.answer,
            "explanation": q.explanation,
        })
    else:
        data["answered"] = False
    return data


@router.get("/questions/daily")
async def get_daily_question(
    subject: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_question_seed(db)
    today_start = datetime.combine(date.today(), datetime.min.time())
    answered_stmt = (
        select(UserAnswer, Question)
        .join(Question, UserAnswer.question_id == Question.id)
        .where(UserAnswer.user_id == user.id, UserAnswer.answered_at >= today_start)
        .order_by(UserAnswer.answered_at.desc())
    )
    if subject:
        answered_stmt = answered_stmt.where(Question.subject == subject)
    answered = (await db.execute(answered_stmt)).first()
    if answered:
        ua, q = answered
        return _question_payload(q, ua)

    stmt = select(Question).where(Question.is_active == True)  # noqa: E712
    if subject:
        stmt = stmt.where(Question.subject == subject)
    questions = list((await db.execute(stmt.order_by(Question.usage_count.asc(), Question.created_at.asc()))).scalars().all())
    if not questions:
        raise HTTPException(status_code=404, detail="暂无题目")
    q = questions[0] if subject else random.choice(questions[: min(4, len(questions))])
    q.usage_count = (q.usage_count or 0) + 1
    await db.commit()
    return _question_payload(q)


@router.post("/questions/{question_id}/answer")
async def submit_answer(
    question_id: str,
    req: AnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    normalized = req.answer.strip().upper()
    correct = normalized == q.answer.strip().upper()
    if correct:
        q.correct_count = (q.correct_count or 0) + 1
    answer = UserAnswer(user_id=user.id, question_id=q.id, user_choice=normalized, is_correct=correct)
    db.add(answer)
    xp_result = {"xp_added": 0}
    if correct:
        xp_result = await add_xp(db, user.id, "daily_question", q.id)
    else:
        existing = await db.execute(
            select(ErrorNote).where(ErrorNote.user_id == user.id, ErrorNote.question_id == q.id)
        )
        note = existing.scalar_one_or_none()
        if note:
            note.wrong_answer = normalized
            note.wrong_count = (note.wrong_count or 0) + 1
            note.is_mastered = False
            note.next_review_at = datetime.now() + timedelta(days=1)
        else:
            db.add(
                ErrorNote(
                    user_id=user.id,
                    question_id=q.id,
                    source="daily_question",
                    wrong_answer=normalized,
                    wrong_count=1,
                    next_review_at=datetime.now() + timedelta(days=1),
                )
            )
    await db.commit()
    return {
        "is_correct": correct,
        "answer": q.answer,
        "explanation": q.explanation,
        "xp_earned": xp_result.get("xp_added", 0),
        "total_xp": xp_result.get("total_xp", user.xp or 0),
        "leveled_up": xp_result.get("leveled_up", False),
        "correct_rate": round((q.correct_count or 0) / max(q.usage_count or 1, 1), 3),
    }


@router.get("/questions/history")
async def question_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    stmt = (
        select(UserAnswer, Question)
        .join(Question, UserAnswer.question_id == Question.id)
        .where(UserAnswer.user_id == user.id)
        .order_by(UserAnswer.answered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    return {
        "items": [
            {
                **_question_payload(q, ua),
                "answeredAt": ua.answered_at.isoformat() if ua.answered_at else None,
            }
            for ua, q in rows
        ],
        "page": page,
        "pageSize": page_size,
    }
