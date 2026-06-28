"""
研友圈服务 — 帖子 / 评论 / 点赞
"""
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.user import User
from app.models.post import Post, Comment, Like
from app.services.xp_service import add_xp


async def get_posts(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    tag: str | None = None,
) -> dict:
    """获取帖子列表（分页，可选按标签筛选）"""
    query = select(Post).options(joinedload(Post.author)).order_by(Post.created_at.desc())

    if tag:
        query = query.where(Post.tags.contains(tag))

    # 总数
    count_query = select(func.count()).select_from(Post)
    if tag:
        count_query = count_query.where(Post.tags.contains(tag))
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    posts = result.unique().scalars().all()

    return {
        "posts": [_post_to_dict(p) for p in posts],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasMore": offset + page_size < total,
    }


async def create_post(
    db: AsyncSession,
    user_id: str,
    content: str,
    tags: str | None = None,
) -> dict:
    """创建帖子"""
    post = Post(user_id=user_id, content=content, tags=tags)
    db.add(post)
    await db.flush()
    await db.refresh(post)

    # 重新加载作者信息
    result = await db.execute(
        select(Post).options(joinedload(Post.author)).where(Post.id == post.id)
    )
    post = result.unique().scalar_one()
    data = _post_to_dict(post)
    xp_result = await add_xp(db, user_id, "post", post.id)
    data["xpEarned"] = xp_result.get("xp_added", 0)
    data["levelUp"] = xp_result.get("leveled_up", False)
    data["newLevel"] = xp_result.get("new_level")
    data["newTitle"] = xp_result.get("new_title")
    return data


async def delete_post(db: AsyncSession, post_id: str, user_id: str) -> bool:
    """删除帖子（仅本人可删）"""
    result = await db.execute(
        select(Post).where(and_(Post.id == post_id, Post.user_id == user_id))
    )
    post = result.scalar_one_or_none()
    if not post:
        return False
    await db.delete(post)
    return True


async def add_comment(
    db: AsyncSession,
    post_id: str,
    user_id: str,
    content: str,
    reply_to: str | None = None,
) -> dict:
    """添加评论，可选回复某条评论"""
    comment = Comment(post_id=post_id, user_id=user_id, content=content, reply_to=reply_to)
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    # 重新加载作者
    result = await db.execute(
        select(Comment).options(joinedload(Comment.author)).where(Comment.id == comment.id)
    )
    comment = result.unique().scalar_one()
    data = _comment_to_dict(comment)
    xp_result = await add_xp(db, user_id, "comment", comment.id)
    data["xpEarned"] = xp_result.get("xp_added", 0)
    data["levelUp"] = xp_result.get("leveled_up", False)
    data["newLevel"] = xp_result.get("new_level")
    data["newTitle"] = xp_result.get("new_title")

    # 通知帖子作者（非自己评论时）
    from app.routers.notifications import create_notification
    from app.models.user import User as U
    post = await db.get(Post, post_id)
    if post and post.user_id != user_id:
        commenter = await db.get(U, user_id)
        await create_notification(db, post.user_id, "friend_message",
            "有人评论了你的帖子",
            f"{commenter.nickname or commenter.username} 评论了你的帖子: {(content)[:50]}")
    # 如果是回复，通知被回复者
    if reply_to:
        replied_comment = await db.get(Comment, reply_to)
        if replied_comment and replied_comment.user_id != user_id:
            commenter = await db.get(U, user_id)
            await create_notification(db, replied_comment.user_id, "friend_message",
                "有人回复了你的评论",
                f"{commenter.nickname or commenter.username} 回复了你的评论: {(content)[:50]}")

    return data


async def get_comments(db: AsyncSession, post_id: str) -> list[dict]:
    """获取帖子的评论列表"""
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.author))
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
    )
    comments = result.unique().scalars().all()
    return [_comment_to_dict(c) for c in comments]


async def toggle_like(db: AsyncSession, post_id: str, user_id: str) -> dict:
    """切换点赞状态（点赞/取消点赞）"""
    # 检查是否已点赞
    result = await db.execute(
        select(Like).where(and_(Like.post_id == post_id, Like.user_id == user_id))
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        post = await db.get(Post, post_id)
        if post and post.likes_count > 0:
            post.likes_count -= 1
        return {"liked": False, "likesCount": post.likes_count if post else 0}
    else:
        like = Like(post_id=post_id, user_id=user_id)
        db.add(like)
        post = await db.get(Post, post_id)
        if post:
            post.likes_count += 1
        give_xp = await add_xp(db, user_id, "like_give", post_id)
        receive_xp = {"xp_added": 0}
        if post and post.user_id != user_id:
            receive_xp = await add_xp(db, post.user_id, "like_receive", post_id)
            # 通知帖子作者
            from app.routers.notifications import create_notification
            from app.models.user import User as U
            liker = await db.get(U, user_id)
            await create_notification(db, post.user_id, "friend_message",
                "有人赞了你的帖子",
                f"{liker.nickname or liker.username} 赞了你的帖子")
        return {
            "liked": True,
            "likesCount": post.likes_count if post else 0,
            "xpEarned": give_xp.get("xp_added", 0),
            "authorXpEarned": receive_xp.get("xp_added", 0),
        }


def _author_badge(author) -> dict:
    """提取用户徽章信息"""
    if not author:
        return {"id": "", "username": "未知", "nickname": "未知", "avatar": None, "school": None, "vipLevel": 0, "level": 1, "levelTitle": "西南娃娃", "isWhitelist": False}
    from app.services.xp_service import get_title
    return {
        "id": author.id or "",
        "username": author.username or "未知",
        "nickname": author.nickname or author.username or "未知",
        "avatar": author.avatar,
        "school": author.school,
        "vipLevel": author.vip_level or 0,
        "level": author.level or 1,
        "levelTitle": get_title(author.xp or 0),
        "isWhitelist": author.is_whitelist or False,
    }


def _post_to_dict(post: Post) -> dict:
    return {
        "id": post.id,
        "content": post.content,
        "tags": post.tags.split(",") if post.tags else [],
        "likesCount": post.likes_count,
        "commentCount": 0,
        "createdAt": post.created_at.isoformat() if post.created_at else None,
        "author": _author_badge(post.author),
    }


def _comment_to_dict(comment: Comment) -> dict:
    return {
        "id": comment.id,
        "postId": comment.post_id,
        "content": comment.content,
        "createdAt": comment.created_at.isoformat() if comment.created_at else None,
        "author": _author_badge(comment.author),
    }
