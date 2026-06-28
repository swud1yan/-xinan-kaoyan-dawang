"""
安全工具 — 密码哈希 / JWT 签发与验证
"""
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from app.config import get_settings

settings = get_settings()


def _truncate_password(password: str) -> bytes:
    """将密码截断至 72 字节（bcrypt 限制）"""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希"""
    pwd_bytes = _truncate_password(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否匹配哈希"""
    pwd_bytes = _truncate_password(plain)
    return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))


def create_token(user_id: str, username: str) -> str:
    """签发 JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码 JWT，失败返回 None"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
