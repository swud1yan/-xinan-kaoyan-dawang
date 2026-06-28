"""
研友圈路由 — 帖子 / 评论 / 点赞
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services import post_service

router = APIRouter(prefix="/posts", tags=["研友圈"])


# ---- 请求/响应模型 ----

class CreatePostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    tags: str | None = None  # 逗号分隔


class PostAuthor(BaseModel):
    id: str
    username: str
    nickname: str | None = None
    avatar: str | None = None
    school: str | None = None
    vipLevel: int = 0
    level: int = 1
    levelTitle: str = "西南娃娃"
    isWhitelist: bool = False


class PostResponse(BaseModel):
    id: str
    content: str
    tags: list[str] = []
    likesCount: int = 0
    commentCount: int = 0
    createdAt: str | None = None
    author: PostAuthor
    xpEarned: int = 0
    levelUp: bool = False
    newLevel: int | None = None
    newTitle: str | None = None


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    page: int
    pageSize: int
    hasMore: bool


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    reply_to: str | None = None  # 回复某条评论的ID


class CommentAuthor(BaseModel):
    id: str
    username: str
    nickname: str | None = None
    avatar: str | None = None
    vipLevel: int = 0
    level: int = 1
    levelTitle: str = "西南娃娃"
    isWhitelist: bool = False


class CommentResponse(BaseModel):
    id: str
    postId: str
    content: str
    createdAt: str | None = None
    author: CommentAuthor
    xpEarned: int = 0
    levelUp: bool = False
    newLevel: int | None = None
    newTitle: str | None = None


class LikeResponse(BaseModel):
    liked: bool
    likesCount: int
    xpEarned: int = 0
    authorXpEarned: int = 0


# ---- 路由 ----

@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=50),
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取帖子列表"""
    result = await post_service.get_posts(db, page=page, page_size=pageSize, tag=tag)
    # 填充评论数
    for post_dict in result["posts"]:
        comments = await post_service.get_comments(db, post_dict["id"])
        post_dict["commentCount"] = len(comments)
    return result


@router.post("", response_model=PostResponse)
async def create_post(
    req: CreatePostRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发帖"""
    return await post_service.create_post(db, user.id, req.content, req.tags)


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除帖子"""
    ok = await post_service.delete_post(db, post_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="帖子不存在或无权删除")
    return {"message": "已删除"}


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    post_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取帖子评论"""
    return await post_service.get_comments(db, post_id)


@router.post("/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: str,
    req: CreateCommentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发表评论"""
    return await post_service.add_comment(db, post_id, user.id, req.content, reply_to=req.reply_to)


@router.post("/{post_id}/likes", response_model=LikeResponse)
async def toggle_like(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """点赞 / 取消点赞"""
    return await post_service.toggle_like(db, post_id, user.id)
