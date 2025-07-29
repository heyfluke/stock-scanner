# 用户服务模块
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
from utils.logger import get_logger
from collections import defaultdict

logger = get_logger()

# 频率限制缓存：{user_id: [(timestamp, count), ...]}
conversation_creation_cache = defaultdict(list)

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
    analysis_result: Optional[str] = Field(default=None)  # JSON格式，完整的股票分析数据
    ai_output: Optional[str] = Field(default=None)  # AI分析文本输出
    chart_data: Optional[str] = Field(default=None)  # 图表数据，JSON格式
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    history_id: int = Field(foreign_key="analysis_history.id")  # 关联的分析历史
    title: str = Field(max_length=200)  # 对话标题
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id")
    role: str = Field(max_length=20)  # 'user' 或 'assistant'
    content: str = Field()  # 消息内容
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
            database_url = os.getenv("DATABASE_URL", "sqlite:///./stock_scanner.db")
        
        self.engine = create_engine(database_url, echo=False)
        
        # 注意：数据库迁移应该在应用启动时进行，而不是在服务初始化时
        # 这里只是确保表存在（作为备用方案）
        try:
            SQLModel.metadata.create_all(self.engine)
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
        
        logger.info(f"用户服务初始化完成 - 数据库: {database_url}")

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == hashed

    def _check_conversation_rate_limit(self, user_id: int) -> bool:
        """检查对话创建频率限制"""
        now = datetime.utcnow()
        user_cache = conversation_creation_cache[user_id]
        
        # 清理超过1秒的记录
        user_cache = [(ts, count) for ts, count in user_cache if (now - ts).total_seconds() < 1]
        conversation_creation_cache[user_id] = user_cache
        
        # 计算1秒内的创建次数
        total_count = sum(count for _, count in user_cache)
        
        # 如果1秒内创建超过3次，返回False
        if total_count >= 3:
            logger.warning(f"用户 {user_id} 对话创建频率过高: {total_count} 次/秒")
            return False
        
        # 添加当前创建记录
        user_cache.append((now, 1))
        conversation_creation_cache[user_id] = user_cache
        
        return True

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
                            analysis_result: Optional[Dict[str, Any]] = None,
                            ai_output: Optional[str] = None,
                            chart_data: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """保存分析历史"""
        try:
            with Session(self.engine) as session:
                history = AnalysisHistory(
                    user_id=user_id,
                    stock_codes=json.dumps(stock_codes),
                    market_type=market_type,
                    analysis_days=analysis_days,
                    analysis_result=json.dumps(analysis_result) if analysis_result else None,
                    ai_output=ai_output,
                    chart_data=json.dumps(chart_data) if chart_data else None
                )
                
                session.add(history)
                session.commit()
                session.refresh(history)
                logger.info(f"分析历史保存成功: {len(stock_codes)}只股票, ID: {history.id}")
                return history.id
                
        except Exception as e:
            logger.error(f"保存分析历史失败: {str(e)}")
            return None

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
                    try:
                        result.append({
                            "id": history.id,
                            "stock_codes": json.loads(history.stock_codes) if history.stock_codes else [],
                            "market_type": history.market_type,
                            "analysis_days": history.analysis_days,
                            "analysis_result": json.loads(history.analysis_result) if history.analysis_result else None,
                            "ai_output": history.ai_output,
                            "chart_data": json.loads(history.chart_data) if history.chart_data else None,
                            "created_at": history.created_at.isoformat()
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"解析历史记录JSON失败 (ID: {history.id}): {e}")
                        # 使用默认值
                        result.append({
                            "id": history.id,
                            "stock_codes": [],
                            "market_type": history.market_type,
                            "analysis_days": history.analysis_days,
                            "analysis_result": None,
                            "ai_output": history.ai_output,
                            "chart_data": None,
                            "created_at": history.created_at.isoformat()
                        })
                return result
                
        except Exception as e:
            logger.error(f"获取分析历史失败: {str(e)}")
            return []

    def delete_analysis_history(self, user_id: int, history_id: int) -> bool:
        """删除分析历史"""
        try:
            with Session(self.engine) as session:
                history = session.exec(
                    select(AnalysisHistory).where(
                        AnalysisHistory.id == history_id,
                        AnalysisHistory.user_id == user_id
                    )
                ).first()
                
                if history:
                    # 先删除相关的对话
                    deleted_conversations = self.delete_conversations_by_history(user_id, history_id)
                    if deleted_conversations > 0:
                        logger.info(f"删除历史记录 {history_id} 时，同时删除了 {deleted_conversations} 个相关对话")
                    
                    # 再删除历史记录
                    session.delete(history)
                    session.commit()
                    logger.info(f"删除分析历史成功: ID {history_id}")
                    return True
                else:
                    logger.warning(f"未找到要删除的历史记录: ID {history_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"删除分析历史失败: {str(e)}")
            return False

    # 对话功能
    def create_conversation(self, user_id: int, history_id: int, title: str = None) -> Optional[int]:
        """创建新对话"""
        try:
            # 检查频率限制
            if not self._check_conversation_rate_limit(user_id):
                logger.warning(f"用户 {user_id} 对话创建被频率限制阻止")
                return None
            
            with Session(self.engine) as session:
                # 验证历史记录是否存在且属于该用户
                history = session.exec(
                    select(AnalysisHistory).where(
                        AnalysisHistory.id == history_id,
                        AnalysisHistory.user_id == user_id
                    )
                ).first()
                
                if not history:
                    logger.warning(f"未找到历史记录: user_id={user_id}, history_id={history_id}")
                    return None
                
                # 如果没有提供标题，生成默认标题
                if not title:
                    stock_codes = json.loads(history.stock_codes)
                    title = f"关于 {', '.join(stock_codes)} 的对话"
                
                conversation = Conversation(
                    user_id=user_id,
                    history_id=history_id,
                    title=title
                )
                
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
                logger.info(f"创建对话成功: ID {conversation.id}, 标题: {title}")
                return conversation.id
                
        except Exception as e:
            logger.error(f"创建对话失败: {str(e)}")
            return None

    def get_conversations(self, user_id: int, history_id: int = None) -> List[Dict[str, Any]]:
        """获取对话列表"""
        try:
            with Session(self.engine) as session:
                query = select(Conversation).where(Conversation.user_id == user_id)
                if history_id:
                    query = query.where(Conversation.history_id == history_id)
                
                conversations = session.exec(
                    query.order_by(Conversation.updated_at.desc())
                ).all()
                
                result = []
                for conv in conversations:
                    # 获取对话中的消息数量
                    messages = session.exec(
                        select(ConversationMessage).where(ConversationMessage.conversation_id == conv.id)
                    ).all()
                    message_count = len(messages)
                    
                    result.append({
                        "id": conv.id,
                        "history_id": conv.history_id,
                        "title": conv.title,
                        "message_count": message_count,
                        "created_at": conv.created_at.isoformat(),
                        "updated_at": conv.updated_at.isoformat()
                    })
                return result
                
        except Exception as e:
            logger.error(f"获取对话列表失败: {str(e)}")
            return []

    def get_conversation_messages(self, user_id: int, conversation_id: int) -> List[Dict[str, Any]]:
        """获取对话消息"""
        try:
            with Session(self.engine) as session:
                # 验证对话是否属于该用户
                conversation = session.exec(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                ).first()
                
                if not conversation:
                    logger.warning(f"未找到对话: user_id={user_id}, conversation_id={conversation_id}")
                    return []
                
                messages = session.exec(
                    select(ConversationMessage).where(ConversationMessage.conversation_id == conversation_id)
                    .order_by(ConversationMessage.created_at.asc())
                ).all()
                
                result = []
                for msg in messages:
                    result.append({
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                    })
                return result
                
        except Exception as e:
            logger.error(f"获取对话消息失败: {str(e)}")
            return []

    def add_conversation_message(self, user_id: int, conversation_id: int, role: str, content: str) -> bool:
        """添加对话消息"""
        try:
            with Session(self.engine) as session:
                # 验证对话是否属于该用户
                conversation = session.exec(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                ).first()
                
                if not conversation:
                    logger.warning(f"未找到对话: user_id={user_id}, conversation_id={conversation_id}")
                    return False
                
                message = ConversationMessage(
                    conversation_id=conversation_id,
                    role=role,
                    content=content
                )
                
                session.add(message)
                
                # 更新对话的更新时间
                conversation.updated_at = datetime.utcnow()
                
                session.commit()
                logger.info(f"添加对话消息成功: conversation_id={conversation_id}, role={role}")
                return True
                
        except Exception as e:
            logger.error(f"添加对话消息失败: {str(e)}")
            return False

    def delete_conversation(self, user_id: int, conversation_id: int) -> bool:
        """删除对话"""
        try:
            with Session(self.engine) as session:
                conversation = session.exec(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                ).first()
                
                if conversation:
                    # 先删除对话中的所有消息
                    messages = session.exec(
                        select(ConversationMessage).where(ConversationMessage.conversation_id == conversation_id)
                    ).all()
                    for message in messages:
                        session.delete(message)
                    
                    # 再删除对话
                    session.delete(conversation)
                    session.commit()
                    logger.info(f"删除对话成功: ID {conversation_id}")
                    return True
                else:
                    logger.warning(f"未找到要删除的对话: ID {conversation_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"删除对话失败: {str(e)}")
            return False

    def delete_conversations_by_history(self, user_id: int, history_id: int) -> int:
        """删除指定历史记录的所有对话"""
        try:
            with Session(self.engine) as session:
                # 获取该历史记录的所有对话
                conversations = session.exec(
                    select(Conversation).where(
                        Conversation.history_id == history_id,
                        Conversation.user_id == user_id
                    )
                ).all()
                
                deleted_count = 0
                for conversation in conversations:
                    # 删除对话中的所有消息
                    messages = session.exec(
                        select(ConversationMessage).where(ConversationMessage.conversation_id == conversation.id)
                    ).all()
                    for message in messages:
                        session.delete(message)
                    
                    # 删除对话
                    session.delete(conversation)
                    deleted_count += 1
                
                session.commit()
                logger.info(f"删除历史记录 {history_id} 的所有对话成功: {deleted_count} 个对话")
                return deleted_count
                
        except Exception as e:
            logger.error(f"删除历史记录对话失败: {str(e)}")
            return 0

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