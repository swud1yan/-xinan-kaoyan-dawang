"""Phase 5 mock exam APIs."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import MockExam, UserExam
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/exams", tags=["Mock Exams"])


class ExamAnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    answer: str = ""


class ExamMarkRequest(BaseModel):
    question_id: str = Field(..., min_length=1)


SEED_EXAMS = [
    ("408", "408计算机综合模拟卷（一）", 150),
    ("math", "数学一模拟卷（一）", 150),
    ("english", "英语一模拟卷（一）", 100),
    ("politics", "政治模拟卷（一）", 100),
]


def _sections(subject: str, total_score: int) -> list[dict]:
    base = [
        {
            "id": "q1",
            "type": "single_choice",
            "content": "下列哪一项最适合作为今天的第一轮复习任务？",
            "options": ["A. 刷短视频", "B. 做一组真题并复盘", "C. 只整理计划", "D. 反复换资料"],
            "answer": "B",
            "explanation": "真题复盘能同时检验知识和暴露薄弱点。",
            "score": 10,
        },
        {
            "id": "q2",
            "type": "single_choice",
            "content": f"{subject} 复习中遇到错题，最优先应该做什么？",
            "options": ["A. 立即跳过", "B. 标记并归纳原因", "C. 删除记录", "D. 只看答案"],
            "answer": "B",
            "explanation": "错题归因和复习间隔比单纯看答案更有效。",
            "score": 10,
        },
        {
            "id": "q3",
            "type": "essay",
            "content": "请写出你对本题知识点的理解和复盘计划。",
            "answer": "结构清晰，包含知识点、错误原因、下一步计划。",
            "explanation": "主观题按完成度给分。",
            "score": max(20, total_score - 20),
        },
    ]
    return [{"name": "综合训练", "type": "mixed", "questions": base}]


async def ensure_exam_seed(db: AsyncSession) -> None:
    count = int((await db.execute(select(func.count()).select_from(MockExam))).scalar() or 0)
    if count:
        return
    for subject, title, score in SEED_EXAMS:
        sections = _sections(subject, score)
        db.add(
            MockExam(
                title=title,
                subject=subject,
                difficulty=3,
                total_score=score,
                time_limit_minutes=180,
                question_count=sum(len(s["questions"]) for s in sections),
                sections=json.dumps(sections, ensure_ascii=False),
                is_active=True,
            )
        )
    await db.commit()


def _exam_payload(exam: MockExam, include_answer: bool = False) -> dict:
    sections = json.loads(exam.sections or "[]")
    if not include_answer:
        for section in sections:
            for question in section.get("questions", []):
                question.pop("answer", None)
                question.pop("explanation", None)
    return {
        "id": exam.id,
        "title": exam.title,
        "subject": exam.subject,
        "difficulty": exam.difficulty,
        "totalScore": exam.total_score,
        "timeLimitMinutes": exam.time_limit_minutes,
        "questionCount": exam.question_count,
        "sections": sections,
        "createdAt": exam.created_at.isoformat() if exam.created_at else None,
    }


def _score_exam(exam: MockExam, answers: dict) -> tuple[int, list[dict]]:
    total = 0
    details = []
    for section in json.loads(exam.sections or "[]"):
        for q in section.get("questions", []):
            qid = q["id"]
            user_answer = str(answers.get(qid, "")).strip()
            max_score = int(q.get("score", 0))
            if q.get("type") == "essay":
                earned = max_score if len(user_answer) >= 30 else (max_score // 2 if user_answer else 0)
                correct = earned == max_score
            else:
                correct = user_answer.upper() == str(q.get("answer", "")).upper()
                earned = max_score if correct else 0
            total += earned
            details.append(
                {
                    "questionId": qid,
                    "answer": q.get("answer"),
                    "userAnswer": user_answer,
                    "score": earned,
                    "maxScore": max_score,
                    "isCorrect": correct,
                    "explanation": q.get("explanation"),
                }
            )
    return total, details


def _attempt_payload(attempt: UserExam, exam: MockExam | None = None) -> dict:
    return {
        "attemptId": attempt.id,
        "examId": attempt.exam_id,
        "examTitle": exam.title if exam else None,
        "subject": exam.subject if exam else None,
        "status": attempt.status,
        "startedAt": attempt.started_at.isoformat() if attempt.started_at else None,
        "submittedAt": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "timeSpentSeconds": attempt.time_spent_seconds,
        "totalScore": attempt.total_score,
        "maxScore": attempt.max_score,
        "answers": json.loads(attempt.answers or "{}"),
        "markedQuestions": json.loads(attempt.marked_questions or "[]"),
        "aiAnalysis": attempt.ai_analysis,
    }


@router.get("")
async def list_exams(
    subject: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_exam_seed(db)
    stmt = select(MockExam).where(MockExam.is_active == True)  # noqa: E712
    if subject:
        stmt = stmt.where(MockExam.subject == subject)
    exams = (await db.execute(stmt.order_by(MockExam.subject.asc(), MockExam.created_at.desc()))).scalars().all()
    return {"items": [_exam_payload(e) for e in exams]}


@router.get("/history")
async def exam_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(UserExam).where(UserExam.user_id == user.id).order_by(UserExam.created_at.desc()).limit(30))
    ).scalars().all()
    items = []
    for attempt in rows:
        items.append(_attempt_payload(attempt, await db.get(MockExam, attempt.exam_id)))
    return {"items": items}


@router.get("/stats")
async def exam_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(UserExam).where(UserExam.user_id == user.id, UserExam.status == "submitted").order_by(UserExam.submitted_at.asc()))
    ).scalars().all()
    return {
        "count": len(rows),
        "bestScore": max([r.total_score or 0 for r in rows], default=0),
        "avgScore": round(sum(r.total_score or 0 for r in rows) / max(len(rows), 1), 1),
        "trend": [{"attemptId": r.id, "score": r.total_score, "maxScore": r.max_score, "date": r.submitted_at.isoformat() if r.submitted_at else None} for r in rows],
    }


@router.get("/{exam_id}/start")
async def start_exam(exam_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_exam_seed(db)
    exam = await db.get(MockExam, exam_id)
    if not exam or not exam.is_active:
        raise HTTPException(status_code=404, detail="exam not found")
    attempt = UserExam(
        user_id=user.id,
        exam_id=exam.id,
        status="in_progress",
        started_at=datetime.now(),
        max_score=exam.total_score,
        answers="{}",
        marked_questions="[]",
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return {"attempt": _attempt_payload(attempt, exam), "exam": _exam_payload(exam)}


@router.put("/{attempt_id}/answer")
async def save_answer(
    attempt_id: str,
    req: ExamAnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attempt = await db.get(UserExam, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="attempt not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="exam already submitted")
    answers = json.loads(attempt.answers or "{}")
    answers[req.question_id] = req.answer
    attempt.answers = json.dumps(answers, ensure_ascii=False)
    await db.commit()
    return {"success": True, "answers": answers}


@router.put("/{attempt_id}/mark")
async def toggle_mark(
    attempt_id: str,
    req: ExamMarkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attempt = await db.get(UserExam, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="attempt not found")
    marked = set(json.loads(attempt.marked_questions or "[]"))
    if req.question_id in marked:
        marked.remove(req.question_id)
    else:
        marked.add(req.question_id)
    attempt.marked_questions = json.dumps(sorted(marked), ensure_ascii=False)
    await db.commit()
    return {"success": True, "markedQuestions": sorted(marked)}


@router.post("/{attempt_id}/submit")
async def submit_exam(attempt_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    attempt = await db.get(UserExam, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="attempt not found")
    exam = await db.get(MockExam, attempt.exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="exam not found")
    score, details = _score_exam(exam, json.loads(attempt.answers or "{}"))
    now = datetime.now()
    attempt.status = "submitted"
    attempt.submitted_at = now
    attempt.time_spent_seconds = max(0, int((now - attempt.started_at).total_seconds())) if attempt.started_at else 0
    attempt.total_score = score
    attempt.max_score = exam.total_score
    # Charge 5 coins for AI analysis
    from app.services.coins_service import ensure_coins_reset, get_available_coins, consume_coins
    await ensure_coins_reset(db, user)
    coins_ok = (await get_available_coins(user))["total_coins"] >= 5 and await consume_coins(db, user, 5)
    # AI analysis via LLM
    weak_list = [d for d in details if not d["isCorrect"]]
    weak_str = "; ".join(f"{d.get('question','')[:60]}" for d in weak_list[:10]) if weak_list else "无"
    analysis_prompt = f"考研{exam.subject}模拟考试分析：得分{score}/{exam.total_score}，错题{len(weak_list)}道。薄弱知识点：{weak_str}。请给100字以内的分析：1句话评价、2-3个薄弱点、1条提分建议。"
    ai_text = "AI分析暂不可用"
    try:
        from app.config import get_settings
        st = get_settings()
        if st.DEEPSEEK_API_KEY and coins_ok:
            async with httpx.AsyncClient(timeout=15.0) as cl:
                r = await cl.post(f"{st.DEEPSEEK_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {st.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}, json={"model": st.DEEPSEEK_MODEL, "messages": [{"role": "user", "content": analysis_prompt}], "max_tokens": 200, "temperature": 0.5})
                if r.status_code == 200: ai_text = r.json()["choices"][0]["message"]["content"]
    except Exception: pass
    attempt.ai_analysis = ai_text
    await db.commit()
    return {"result": _attempt_payload(attempt, exam), "details": details}


@router.get("/{attempt_id}/result")
async def exam_result(attempt_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    attempt = await db.get(UserExam, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="attempt not found")
    exam = await db.get(MockExam, attempt.exam_id)
    score, details = _score_exam(exam, json.loads(attempt.answers or "{}")) if exam else (0, [])
    return {"result": _attempt_payload(attempt, exam), "details": details}
