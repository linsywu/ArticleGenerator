"""
FastAPI 依赖注入：用户认证、爬虫密钥校验
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .auth import decode_access_token
from .config import settings

# Bearer token 安全方案（必选）
security = HTTPBearer()
# Bearer token 安全方案（可选，无 token 时不报错）
optional_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """验证 Bearer token 并返回当前用户"""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
        )
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户标识",
        )
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )
    return user


async def verify_crawler_key(x_api_key: str = Header(..., description="爬虫共享密钥")):
    """校验爬虫共享密钥（X-API-Key header）"""
    if x_api_key != settings.crawler_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的爬虫密钥",
        )
    return None


async def verify_any_auth(
    x_api_key: Optional[str] = Header(None, description="爬虫共享密钥（可选）"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db),
) -> None:
    """接受 JWT Bearer token 或 X-API-Key，任一有效即可"""
    # 优先尝试 X-API-Key
    if x_api_key and x_api_key == settings.crawler_api_key:
        return
    # 其次尝试 Bearer JWT token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要有效的认证凭据",
    )
