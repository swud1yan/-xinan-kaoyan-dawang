"""
AI Help / Customer Support - restricted to app-usage questions only.
Uses DeepSeek API with strict system prompt. 3 off-topic strikes = 1hr ban.
"""
import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/help", tags=["AI客服"])
settings = get_settings()

# In-memory help strike tracker: {user_id: {"strikes": int, "banned_until": iso_str|None}}
_help_state: dict[str, dict] = {}

HELP_SYSTEM_PROMPT = """你是西南大王考研APP的智能客服助手。你只能回答与软件使用相关的问题。

【允许回答的问题类型】
- APP功能介绍和使用方法（择校、专业课、AI陪聊、研友圈、好友聊天、番茄钟、每日一题、记忆闪卡、模拟考试、复试面试、调剂监控、学习计划等）
- 注册/登录/账号相关问题
- VIP会员、研王爷、研AI币、兑换码相关
- 签到、经验值、等级、成就徽章相关
- 通知、消息、好友管理
- 数据同步、设置修改

【严禁回答的问题】
- 考研知识、考试内容、题目解答（请使用APP中的AI陪聊功能）
- 任何与APP使用无关的话题
- 政治、宗教、暴力、色情等违规内容

【回复规则】
- 如果用户询问APP使用方法：简洁清晰地解释操作步骤
- 如果用户询问考研知识：回复"这是考研知识相关的问题，请使用APP中'AI陪聊'功能咨询，我可以帮你解答APP使用方面的问题。"
- 如果用户询问无关话题：回复"我仅支持APP使用相关问题。请描述你在使用西南大王APP时遇到的具体问题。"
- 如果用户提到要反馈问题、提建议、投诉等内容：回复"如需提交反馈或建议，请直接输入'我要反馈'即可进入反馈页面。"

回复控制在150字以内，语气友好亲切。"""


class HelpAskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


def _get_state(user_id: str) -> dict:
    if user_id not in _help_state:
        _help_state[user_id] = {"strikes": 0, "banned_until": None}
    return _help_state[user_id]


def _is_off_topic(user_message: str) -> bool:
    """Quick heuristic check before calling LLM - catches obvious off-topic."""
    msg_lower = user_message.lower().strip()
    # Obvious off-topic patterns
    off_topic_keywords = [
        "天气", "新闻", "股票", "游戏", "电影", "音乐", "美食",
        "weather", "game", "movie", "music",
        "考研政治", "考研英语", "数学题", "专业课",
        "政治题", "英语题", "真题答案", "考试内容",
    ]
    for kw in off_topic_keywords:
        if kw in msg_lower:
            return True
    return False


async def _call_deepseek(system_prompt: str, user_message: str) -> str:
    """Call DeepSeek API."""
    from app.services.ai_control import ai_enabled
    if not ai_enabled():
        return "AI功能维护中，请稍后再试。"
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return "客服系统暂未配置，请联系管理员。"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.5,
                },
            )
            if r.status_code != 200:
                return "客服系统暂时繁忙，请稍后再试。"
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return "客服系统暂时无法连接，请稍后再试。"


async def _classify_topic(user_message: str) -> bool:
    """Use a quick LLM call to check if message is on-topic. Returns True if ON-topic."""
    check_prompt = f"""判断以下用户消息是否与APP软件使用相关（如功能介绍、操作步骤、账号问题、VIP购买等）。
仅回复 "yes" 或 "no"。

用户消息: {user_message}"""
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return True  # No API key, default to allowing
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个内容过滤器。只回复yes或no。"},
                        {"role": "user", "content": check_prompt},
                    ],
                    "max_tokens": 5,
                    "temperature": 0,
                },
            )
            if r.status_code != 200:
                return True
            data = r.json()
            result = data["choices"][0]["message"]["content"].strip().lower()
            return "yes" in result
    except Exception:
        return True  # On error, allow


@router.post("/ask")
async def help_ask(
    req: HelpAskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI客服 - 仅回答APP使用问题"""
    state = _get_state(user.id)

    # Check if banned
    if state["banned_until"]:
        ban_time = datetime.fromisoformat(state["banned_until"])
        if datetime.now(timezone.utc) < ban_time:
            remaining = int((ban_time - datetime.now(timezone.utc)).total_seconds() / 60)
            raise HTTPException(429, detail=f"帮助功能已被暂时禁用，剩余 {remaining} 分钟。请等待解禁后再使用。")
        else:
            # Ban expired
            state["banned_until"] = None
            state["strikes"] = 0

    msg = req.message.strip()

    # Step 1: Quick heuristic check
    if _is_off_topic(msg):
        state["strikes"] += 1
        if state["strikes"] >= 3:
            state["banned_until"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            return {
                "reply": "你已连续3次询问与APP使用无关的问题，帮助功能已被禁用1小时。请等待解禁后再使用。",
                "strikes": state["strikes"],
                "banned": True,
            }
        return {
            "reply": f"我仅支持APP使用相关问题。请描述你在使用西南大王APP时遇到的具体问题。（警告 {state['strikes']}/3 次）",
            "strikes": state["strikes"],
            "banned": False,
        }

    # Step 2: LLM classification (lightweight check)
    is_on_topic = await _classify_topic(msg)
    if not is_on_topic:
        state["strikes"] += 1
        if state["strikes"] >= 3:
            state["banned_until"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            return {
                "reply": "你已连续3次询问与APP使用无关的问题，帮助功能已被禁用1小时。",
                "strikes": state["strikes"],
                "banned": True,
            }
        return {
            "reply": f"我仅支持APP使用相关问题。请描述你在使用西南大王APP时遇到的具体问题。（警告 {state['strikes']}/3 次）",
            "strikes": state["strikes"],
            "banned": False,
        }

    # Step 3: On-topic — answer with help system prompt
    reply = await _call_deepseek(HELP_SYSTEM_PROMPT, msg)

    return {
        "reply": reply,
        "strikes": state["strikes"],
        "banned": False,
    }


@router.get("/status")
async def help_status(user: User = Depends(get_current_user)):
    """查询帮助功能状态"""
    state = _get_state(user.id)
    banned_remaining = None
    if state["banned_until"]:
        ban_time = datetime.fromisoformat(state["banned_until"])
        if datetime.now(timezone.utc) < ban_time:
            banned_remaining = int((ban_time - datetime.now(timezone.utc)).total_seconds() / 60)
        else:
            state["banned_until"] = None
            state["strikes"] = 0
    return {
        "strikes": state["strikes"],
        "banned_until": state["banned_until"],
        "banned_remaining_minutes": banned_remaining,
    }
