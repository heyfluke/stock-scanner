# 用户服务模块
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger()

# 数据库模型定义
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: Optional[str] = Field(default=None, unique=True, max_length=100)
    password_hash: str = Field(max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class UserFavorite(SQLModel, table=True):
    __tablename__ = "user_favorites"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    stock_code: str = Field(max_length=20)
    market_type: str = Field(max_length=10)
    display_name: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[str] = Field(default=None, max_length=200)  # JSON格式
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisHistory(SQLModel, table=True):
    __tablename__ = "analysis_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    stock_codes: str = Field()  # JSON格式
    market_type: str = Field(max_length=10)
    analysis_days: int = Field(default=30)
    analysis_result: Optional[str] = Field(default=None)  # JSON格式
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, foreign_key="users.id")
    default_market_type: str = Field(default="A", max_length=10)
    default_analysis_days: int = Field(default=30)
    api_preferences: Optional[str] = Field(default=None)  # JSON格式
    ui_preferences: Optional[str] = Field(default=None)   # JSON格式
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# 请求响应模型
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    username: str
    password: str

class FavoriteRequest(BaseModel):
    stock_code: str
    market_type: str
    display_name: Optional[str] = None
    tags: Optional[List[str]] = None

class UserSettingsRequest(BaseModel):
    default_market_type: Optional[str] = None
    default_analysis_days: Optional[int] = None
    api_preferences: Optional[Dict[str, Any]] = None
    ui_preferences: Optional[Dict[str, Any]] = None

class UserService:
    def __init__(self, database_url: Optional[str] = None):
        """初始化用户服务"""
        if database_url is None:
            import os
            database_url = os.getenv("DATABASE_URL", "sqlite:///./stock_scanner.db")
        
        self.engine = create_engine(database_url, echo=False)
        SQLModel.metadata.create_all(self.engine)
        logger.info(f"用户服务初始化完成 - 数据库: {database_url}")

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == hashed

    def create_user(self, user_data: UserRegisterRequest) -> Optional[User]:
        """创建新用户"""
        try:
            with Session(self.engine) as session:
                # 检查用户名是否已存在
                existing_user = session.exec(
                    select(User).where(User.username == user_data.username)
                ).first()
                
                if existing_user:
                    logger.warning(f"用户名已存在: {user_data.username}")
                    return None

                # 创建新用户
                user = User(
                    username=user_data.username,
                    email=user_data.email,
                    password_hash=self._hash_password(user_data.password),
                    display_name=user_data.display_name or user_data.username
                )
                
                session.add(user)
                session.commit()
                session.refresh(user)
                
                # 创建默认用户设置
                settings = UserSettings(user_id=user.id)
                session.add(settings)
                session.commit()
                
                logger.info(f"用户创建成功: {user.username}")
                return user
                
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            with Session(self.engine) as session:
                user = session.exec(
                    select(User).where(
                        User.username == username, 
                        User.is_active == True
                    )
                ).first()
                
                if user and self._verify_password(password, user.password_hash):
                    logger.info(f"用户认证成功: {username}")
                    return user
                else:
                    logger.warning(f"用户认证失败: {username}")
                    return None
                    
        except Exception as e:
            logger.error(f"用户认证出错: {str(e)}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            with Session(self.engine) as session:
                return session.get(User, user_id)
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            with Session(self.engine) as session:
                return session.exec(
                    select(User).where(User.username == username)
                ).first()
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
            return None

    # 收藏功能
    def add_favorite(self, user_id: int, favorite_data: FavoriteRequest) -> bool:
        """添加收藏股票"""
        try:
            with Session(self.engine) as session:
                # 检查是否已收藏
                existing = session.exec(
                    select(UserFavorite).where(
                        UserFavorite.user_id == user_id,
                        UserFavorite.stock_code == favorite_data.stock_code,
                        UserFavorite.market_type == favorite_data.market_type
                    )
                ).first()
                
                if existing:
                    logger.warning(f"股票已收藏: {favorite_data.stock_code}")
                    return False

                favorite = UserFavorite(
                    user_id=user_id,
                    stock_code=favorite_data.stock_code,
                    market_type=favorite_data.market_type,
                    display_name=favorite_data.display_name,
                    tags=json.dumps(favorite_data.tags) if favorite_data.tags else None
                )
                
                session.add(favorite)
                session.commit()
                logger.info(f"收藏添加成功: {favorite_data.stock_code}")
                return True
                
        except Exception as e:
            logger.error(f"添加收藏失败: {str(e)}")
            return False

    def remove_favorite(self, user_id: int, stock_code: str, market_type: str) -> bool:
        """移除收藏股票"""
        try:
            with Session(self.engine) as session:
                favorite = session.exec(
                    select(UserFavorite).where(
                        UserFavorite.user_id == user_id,
                        UserFavorite.stock_code == stock_code,
                        UserFavorite.market_type == market_type
                    )
                ).first()
                
                if favorite:
                    session.delete(favorite)
                    session.commit()
                    logger.info(f"收藏移除成功: {stock_code}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"移除收藏失败: {str(e)}")
            return False

    def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户收藏列表"""
        try:
            with Session(self.engine) as session:
                favorites = session.exec(
                    select(UserFavorite).where(UserFavorite.user_id == user_id)
                    .order_by(UserFavorite.created_at.desc())
                ).all()
                
                result = []
                for fav in favorites:
                    result.append({
                        "id": fav.id,
                        "stock_code": fav.stock_code,
                        "market_type": fav.market_type,
                        "display_name": fav.display_name,
                        "tags": json.loads(fav.tags) if fav.tags else [],
                        "created_at": fav.created_at.isoformat()
                    })
                return result
                
        except Exception as e:
            logger.error(f"获取收藏列表失败: {str(e)}")
            return []

    # 历史记录功能
    def save_analysis_history(self, user_id: int, stock_codes: List[str], 
                            market_type: str, analysis_days: int, 
                            analysis_result: Optional[Dict[str, Any]] = None) -> bool:
        """保存分析历史"""
        try:
            with Session(self.engine) as session:
                history = AnalysisHistory(
                    user_id=user_id,
                    stock_codes=json.dumps(stock_codes),
                    market_type=market_type,
                    analysis_days=analysis_days,
                    analysis_result=json.dumps(analysis_result) if analysis_result else None
                )
                
                session.add(history)
                session.commit()
                logger.info(f"分析历史保存成功: {len(stock_codes)}只股票")
                return True
                
        except Exception as e:
            logger.error(f"保存分析历史失败: {str(e)}")
            return False

    def get_analysis_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取分析历史"""
        try:
            with Session(self.engine) as session:
                histories = session.exec(
                    select(AnalysisHistory).where(AnalysisHistory.user_id == user_id)
                    .order_by(AnalysisHistory.created_at.desc())
                    .limit(limit)
                ).all()
                
                result = []
                for history in histories:
                    result.append({
                        "id": history.id,
                        "stock_codes": json.loads(history.stock_codes),
                        "market_type": history.market_type,
                        "analysis_days": history.analysis_days,
                        "analysis_result": json.loads(history.analysis_result) if history.analysis_result else None,
                        "created_at": history.created_at.isoformat()
                    })
                return result
                
        except Exception as e:
            logger.error(f"获取分析历史失败: {str(e)}")
            return []

    # 用户设置功能
    def update_user_settings(self, user_id: int, settings_data: UserSettingsRequest) -> bool:
        """更新用户设置"""
        try:
            with Session(self.engine) as session:
                settings = session.exec(
                    select(UserSettings).where(UserSettings.user_id == user_id)
                ).first()
                
                if not settings:
                    # 创建新设置
                    settings = UserSettings(user_id=user_id)
                    session.add(settings)
                
                # 更新设置
                if settings_data.default_market_type is not None:
                    settings.default_market_type = settings_data.default_market_type
                if settings_data.default_analysis_days is not None:
                    settings.default_analysis_days = settings_data.default_analysis_days
                if settings_data.api_preferences is not None:
                    settings.api_preferences = json.dumps(settings_data.api_preferences)
                if settings_data.ui_preferences is not None:
                    settings.ui_preferences = json.dumps(settings_data.ui_preferences)
                
                settings.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"用户设置更新成功: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"更新用户设置失败: {str(e)}")
            return False

    def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户设置"""
        try:
            with Session(self.engine) as session:
                settings = session.exec(
                    select(UserSettings).where(UserSettings.user_id == user_id)
                ).first()
                
                if settings:
                    return {
                        "default_market_type": settings.default_market_type,
                        "default_analysis_days": settings.default_analysis_days,
                        "api_preferences": json.loads(settings.api_preferences) if settings.api_preferences else {},
                        "ui_preferences": json.loads(settings.ui_preferences) if settings.ui_preferences else {},
                        "updated_at": settings.updated_at.isoformat()
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户设置失败: {str(e)}")
            return None

# 全局用户服务实例
user_service = UserService() 