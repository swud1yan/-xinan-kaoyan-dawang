"""
AI 陪聊服务 - 对接 DeepSeek / 通义千问 / Claude
"""
import httpx
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """你是"西南大王"，一位全能的考研备考AI助手，服务于全国考研学子。

你的能力范围：
1. 熟悉全国所有985/211/双一流高校的考研政策、分数线、招生人数
2. 精通所有统考科目：408计算机综合、政治、英语一/二、数学一/二/三、法硕联考、管理类联考、临床医学综合等
3. 了解各校自主命题特点，能对比不同学校的考试难度
4. 能提供系统的备考计划、时间管理、复习策略
5. 能做院校推荐（基于用户背景和意向），分析报录比和竞争情况
6. 擅长心态调节，鼓励学生坚持

你的风格：
- 亲切幽默，像一位已经上岸的学长/学姐，自称"本王"
- 回答简洁实用，多用具体数据和例子
- 不限制地域，全国高校都熟悉
- 遇到不知道的具体数据，诚实说明并给参考方向
- 始终鼓励为主，但也会直言不讳指出问题

用中文回答，控制在200字以内（除非用户要求详细分析）。"""


def _build_messages(history: list[dict], new_message: str) -> list[dict]:
    """构建发送给 LLM 的消息列表"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": new_message})
    return messages


async def chat_with_deepseek(history: list[dict], message: str) -> str:
    """使用 DeepSeek API"""
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API Key 未配置")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": _build_messages(history, message),
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def chat_with_dashscope(history: list[dict], message: str) -> str:
    """使用通义千问 (DashScope) API"""
    if not settings.DASHSCOPE_API_KEY:
        raise ValueError("通义千问 API Key 未配置")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DASHSCOPE_MODEL,
                "messages": _build_messages(history, message),
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def chat_with_anthropic(history: list[dict], message: str) -> str:
    """使用 Claude (Anthropic) API"""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("Claude API Key 未配置")

    anthropic_messages = []
    for msg in history[-20:]:
        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
    anthropic_messages.append({"role": "user", "content": message})

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "system": SYSTEM_PROMPT,
                "messages": anthropic_messages,
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def chat(history: list[dict], message: str) -> str:
    """统一入口：根据配置选择 LLM 提供商"""
    from app.services.ai_control import ai_enabled
    if not ai_enabled():
        return "AI功能维护中，请稍后再试。"
    provider = settings.LLM_PROVIDER

    if provider == "deepseek":
        return await chat_with_deepseek(history, message)
    elif provider == "dashscope":
        return await chat_with_dashscope(history, message)
    elif provider == "anthropic":
        return await chat_with_anthropic(history, message)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
