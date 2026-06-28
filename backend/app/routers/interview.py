"""Phase 5 interview — DeepSeek powered personalized questions and scoring."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_settings
from app.database import get_db
from app.models.phase2_5 import InterviewQA, InterviewSession
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.coins_service import ensure_coins_reset, get_available_coins, consume_coins

router = APIRouter(prefix="/interview", tags=["Interview"])
settings = get_settings()


class InterviewStartRequest(BaseModel):
    type: str = Field("professional", max_length=20)
    targetSchool: str | None = Field(None, max_length=100)
    targetMajor: str | None = Field(None, max_length=200)


class InterviewAnswerRequest(BaseModel):
    question_id: str | None = None
    answer: str = Field("", max_length=4000)


async def _call_llm(messages: list, max_tokens: int = 500, temperature: float = 0.7) -> str:
    from app.services.ai_control import ai_enabled
    if not ai_enabled():
        return "AI功能维护中，请稍后再试。"
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return "AI服务未配置" if max_tokens < 100 else json.dumps({"scores": [70,70,70], "feedback": "AI未配置","suggestion": ""})
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": settings.DEEPSEEK_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
            )
            if r.status_code != 200:
                return "AI服务异常"
            return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return "AI连接失败"


def _session_payload(session, qas):
    return {
        "sessionId": session.id, "type": session.type, "targetSchool": session.target_school,
        "targetMajor": session.target_major, "status": session.status, "totalScore": session.total_score,
        "answeredCount": len([q for q in qas if q.user_answer is not None]),
        "questionCount": len(qas),
        "startedAt": session.started_at.isoformat() if session.started_at else None,
        "completedAt": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.post("/start")
async def start_interview(req: InterviewStartRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check VIP: gold+ required
    if (user.vip_level or 0) < 2:
        raise HTTPException(403, detail="AI复试面试需要金卡及以上VIP")
    # Charge 10 coins
    await ensure_coins_reset(db, user)
    coins = await get_available_coins(user)
    if coins["total_coins"] < 10:
        raise HTTPException(402, detail=f"研AI币不足(需要10币，当前{coins['total_coins']}币)")
    if not await consume_coins(db, user, 10):
        raise HTTPException(402, detail="研AI币扣除失败")

    school = req.targetSchool or user.target_school or "目标院校"
    major = req.targetMajor or user.major or "计算机"
    interview_type = req.type if req.type in ("english", "professional", "comprehensive", "full") else "professional"
    num_questions = 8 if interview_type == "full" else 5

    # Generate personalized questions with LLM
    prompt = f"""你是研究生复试面试官。考生报考{school}的{major}专业。面试类型: {interview_type}。
请生成{num_questions}道复试面试问题。要求:
- 问题与{school}和{major}密切相关
- 英文面试用英文提问，其余用中文
- 问题由浅入深，考察专业基础、研究兴趣和综合素质
直接输出JSON数组，每项包含"question"字段。只输出JSON，不要其他内容。"""

    questions_json = await _call_llm([{"role": "user", "content": prompt}], max_tokens=800, temperature=0.8)
    try:
        start = questions_json.find("[")
        end = questions_json.rfind("]") + 1
        q_list = json.loads(questions_json[start:end]) if start >= 0 else []
    except Exception:
        q_list = [{"question": f"请谈谈你对{major}的理解，以及为什么选择{school}？"}]

    session = InterviewSession(user_id=user.id, type=interview_type, target_school=school, target_major=major, status="in_progress", started_at=datetime.now())
    db.add(session); await db.flush()
    for i, q in enumerate(q_list[:num_questions], start=1):
        db.add(InterviewQA(session_id=session.id, question=q.get("question", f"问题{i}"), sort_order=i))
    await db.commit()
    qas = (await db.execute(select(InterviewQA).where(InterviewQA.session_id == session.id).order_by(InterviewQA.sort_order.asc()))).scalars().all()
    return {"session": _session_payload(session, qas), "question": _qa_payload(qas[0] if qas else None), "coins_used": 10}


@router.post("/{session_id}/answer")
async def answer_interview(session_id: str, req: InterviewAnswerRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = await db.get(InterviewSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404)
    if session.status != "in_progress":
        raise HTTPException(400, "面试已结束")

    qas = (await db.execute(select(InterviewQA).where(InterviewQA.session_id == session.id).order_by(InterviewQA.sort_order.asc()))).scalars().all()
    current_qa = None
    for q in qas:
        if q.user_answer is None:
            current_qa = q; break
    if not current_qa:
        raise HTTPException(400, "所有问题已答完")

    # AI scoring
    score_prompt = f"""你是研究生复试面试评分官。考生报考{session.target_school}的{session.target_major}。
面试问题: {current_qa.question}
考生回答: {req.answer}

请从内容完整性(40%)、表达清晰度(30%)、专业深度(30%)三个维度评分，并给出简短点评和建议。
输出JSON: {{"scores": [内容分0-100, 表达分0-100, 专业分0-100], "feedback": "简短点评", "suggestion": "改进建议"}}"""

    result = await _call_llm([{"role": "user", "content": score_prompt}], max_tokens=300, temperature=0.3)
    try:
        start = result.find("{"); end = result.rfind("}") + 1
        eval_data = json.loads(result[start:end]) if start >= 0 else {}
    except Exception:
        eval_data = {}
    scores = eval_data.get("scores", [70, 70, 70])

    current_qa.user_answer = req.answer
    current_qa.score_content = scores[0] if len(scores) > 0 else 70
    current_qa.score_expression = scores[1] if len(scores) > 1 else 70
    current_qa.score_confidence = scores[2] if len(scores) > 2 else 70
    current_qa.feedback = eval_data.get("feedback", "")
    current_qa.suggested_answer = eval_data.get("suggestion", "")

    # Check if all answered
    qas = (await db.execute(select(InterviewQA).where(InterviewQA.session_id == session.id).order_by(InterviewQA.sort_order.asc()))).scalars().all()
    if all(q.user_answer is not None for q in qas):
        scores_list = [int(((q.score_content or 0) + (q.score_expression or 0) + (q.score_confidence or 0)) / 3) for q in qas]
        session.total_score = int(sum(scores_list) / max(len(scores_list), 1)) if scores_list else 0
        session.status = "completed"
        session.completed_at = datetime.now()

    await db.commit()
    next_qa = None
    for q in qas:
        if q.user_answer is None: next_qa = q; break
    return {"current": _qa_payload(current_qa), "next": _qa_payload(next_qa), "session": _session_payload(session, qas)}


@router.get("/{session_id}/report")
async def interview_report(session_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = await db.get(InterviewSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404)
    qas = (await db.execute(select(InterviewQA).where(InterviewQA.session_id == session.id).order_by(InterviewQA.sort_order.asc()))).scalars().all()
    # Generate AI summary
    qa_text = "\n".join(f"Q: {q.question}\nA: {q.user_answer or '未答'}\n评分: 内容{q.score_content} 表达{q.score_expression} 专业{q.score_confidence}" for q in qas)
    summary_prompt = f"""请根据以下复试面试记录，给出150字以内的总体评价和改进方向:
{qa_text}"""
    ai_summary = await _call_llm([{"role": "user", "content": summary_prompt}], max_tokens=200, temperature=0.5)
    return {"session": _session_payload(session, qas), "qas": [_qa_payload(q) for q in qas], "aiSummary": ai_summary}


@router.get("/history")
async def interview_history(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sessions = (await db.execute(select(InterviewSession).where(InterviewSession.user_id == user.id).order_by(InterviewSession.started_at.desc()).limit(30))).scalars().all()
    items = []
    for s in sessions:
        qas = (await db.execute(select(InterviewQA).where(InterviewQA.session_id == s.id).order_by(InterviewQA.sort_order.asc()))).scalars().all()
        items.append(_session_payload(s, qas))
    return {"items": items}


def _qa_payload(qa):
    if not qa: return None
    return {"id": qa.id, "question": qa.question, "answer": qa.user_answer, "scoreContent": qa.score_content, "scoreExpression": qa.score_expression, "scoreConfidence": qa.score_confidence, "feedback": qa.feedback, "suggestedAnswer": qa.suggested_answer, "sortOrder": qa.sort_order}
