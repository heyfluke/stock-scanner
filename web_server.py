from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generator
from services.stock_analyzer_service import StockAnalyzerService
from services.us_stock_service_async import USStockServiceAsync
from services.fund_service_async import FundServiceAsync
from services.user_service import user_service, UserRegisterRequest, UserLoginRequest, FavoriteRequest, UserSettingsRequest, APIConfigRequest
import os
import httpx
from utils.logger import get_logger
from utils.api_utils import APIUtils
from dotenv import load_dotenv
import uvicorn
import json
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt
from services.ai_analyzer import AIAnalyzer
from services.agent_orchestrator import AgentOrchestrator

# 添加数据库迁移导入
from utils.database_migrator import DatabaseMigrator

load_dotenv()

# 获取日志器
logger = get_logger()

# JWT相关配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # Token过期时间一周

# 是否启用用户系统（统一的认证方式）
ENABLE_USER_SYSTEM = os.getenv("ENABLE_USER_SYSTEM", "true").lower() == "true"
# 是否允许匿名访问（不启用用户系统时）
ALLOW_ANONYMOUS = not ENABLE_USER_SYSTEM


app = FastAPI(
    title="Stock Scanner API",
    description="异步股票分析API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],
)

# 初始化异步服务
us_stock_service = USStockServiceAsync()
fund_service = FundServiceAsync()

# 在应用启动时添加数据库迁移检查
@app.on_event("startup")
async def startup_event():
    logger.info("应用启动，检查数据库迁移")
    migrator = DatabaseMigrator()
    await migrator.check_and_apply_migrations()
    logger.info("数据库迁移检查完成")

# 定义请求和响应模型
class AnalyzeRequest(BaseModel):
    stock_codes: List[str]
    market_type: str = "A"
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    api_model: Optional[str] = None
    api_timeout: Optional[str] = None
    analysis_days: Optional[int] = 30  # AI分析使用的天数，默认30天
    preset_id: Optional[str] = None     # 多Agent预设方案ID（可选）
    config_name: Optional[str] = None   # API配置名称（新增）

class TestAPIRequest(BaseModel):
    api_url: str
    api_key: str
    api_model: Optional[str] = None
    api_timeout: Optional[int] = 10

class LoginRequest(BaseModel):
    password: Optional[str] = None  # 兼容旧版密码登录
    username: Optional[str] = None  # 新用户系统
    
class Token(BaseModel):
    access_token: str
    token_type: str

# 自定义依赖项，在允许匿名访问时不要求token
class OptionalOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        if ALLOW_ANONYMOUS:
            return None
        try:
            return await super().__call__(request)
        except HTTPException:
            if ALLOW_ANONYMOUS:
                return None
            raise

# 使用自定义的依赖项
optional_oauth2_scheme = OptionalOAuth2PasswordBearer(tokenUrl="login")

# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 验证令牌并获取用户信息
async def get_current_user(token: Optional[str] = Depends(optional_oauth2_scheme)):
    """验证令牌并返回用户信息"""
    # 如果允许匿名访问，返回匿名用户
    if ALLOW_ANONYMOUS:
        return {"user_id": None, "username": "guest", "is_authenticated": False}
        
    # 如果没有token但允许匿名访问，返回guest
    if token is None and ALLOW_ANONYMOUS:
        return {"user_id": None, "username": "guest", "is_authenticated": False}
        
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 如果需要认证但没有token，抛出异常
    if token is None:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if username is None:
            raise credentials_exception
            
        # 如果启用了用户系统且有user_id，验证用户是否在数据库中存在
        if ENABLE_USER_SYSTEM and user_id:
            # 验证用户是否在数据库中存在
            user = user_service.get_user_by_id(user_id)
            if user:
                return {"user_id": user_id, "username": username, "is_authenticated": True}
            else:
                # 用户不存在于数据库中，清除认证状态
                raise credentials_exception
        else:
            # 兼容旧版认证系统
            return {"user_id": None, "username": username, "is_authenticated": True}
            
    except JWTError:
        raise credentials_exception

# 验证令牌（
async def verify_token(token: Optional[str] = Depends(optional_oauth2_scheme)):
    """验证令牌，返回用户名（保持与原版兼容）"""
    # 如果允许匿名访问，返回guest
    if ALLOW_ANONYMOUS:
        return "guest"
        
    # 如果没有token且允许匿名访问，返回guest
    if token is None and ALLOW_ANONYMOUS:
        return "guest"
        
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 如果需要认证但没有token，抛出异常
    if token is None:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

# 用户注册接口
@app.post("/api/register")
async def register(request: UserRegisterRequest):
    """用户注册接口"""
    if not ENABLE_USER_SYSTEM:
        raise HTTPException(status_code=400, detail="用户系统未启用")
    
    user = user_service.create_user(request)
    if user:
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}, 
            expires_delta=access_token_expires
        )
        logger.info(f"用户注册成功: {user.username}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email
            }
        }
    else:
        raise HTTPException(status_code=400, detail="用户注册失败，用户名可能已存在")

# 用户登录接口（仅用户系统）
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录接口"""
    if not ENABLE_USER_SYSTEM:
        raise HTTPException(status_code=400, detail="用户系统未启用")
        
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="请提供用户名和密码")
        
    user = user_service.authenticate_user(request.username, request.password)
    if user:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}, 
            expires_delta=access_token_expires
        )
        logger.info(f"用户登录成功: {user.username}")
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email
            }
        }
    else:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

# 检查用户认证状态
@app.get("/api/check_auth")
async def check_auth(current_user: dict = Depends(get_current_user)):
    """检查用户认证状态"""
    return {
        "authenticated": current_user["is_authenticated"], 
        "username": current_user["username"],
        "user_id": current_user.get("user_id"),
        "user_system_enabled": ENABLE_USER_SYSTEM
    }

@app.post("/api/logout")
async def logout():
    """用户登出接口"""
    # JWT是无状态的，服务端不需要做任何操作
    # 客户端需要清除localStorage中的token
    return {"message": "登出成功"}

# 获取用户信息
@app.get("/api/user/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """获取用户信息"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    user = user_service.get_user_by_id(current_user["user_id"])
    if user:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="用户不存在")

# 收藏功能
@app.post("/api/user/favorites")
async def add_favorite(request: FavoriteRequest, current_user: dict = Depends(get_current_user)):
    """添加收藏股票"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    success = user_service.add_favorite(current_user["user_id"], request)
    if success:
        return {"message": "收藏添加成功"}
    else:
        raise HTTPException(status_code=400, detail="添加收藏失败，可能已存在")

@app.delete("/api/user/favorites/{stock_code}")
async def remove_favorite(stock_code: str, market_type: str, current_user: dict = Depends(get_current_user)):
    """移除收藏股票"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    success = user_service.remove_favorite(current_user["user_id"], stock_code, market_type)
    if success:
        return {"message": "收藏移除成功"}
    else:
        raise HTTPException(status_code=404, detail="收藏不存在")

@app.get("/api/user/favorites")
async def get_favorites(current_user: dict = Depends(get_current_user)):
    """获取收藏列表"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    favorites = user_service.get_user_favorites(current_user["user_id"])
    return {"favorites": favorites}

# 历史记录功能
@app.get("/api/user/history")
async def get_analysis_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """获取分析历史"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    history = user_service.get_analysis_history(current_user["user_id"], limit)
    return {"history": history}

@app.delete("/api/user/history/{history_id}")
async def delete_analysis_history(history_id: int, current_user: dict = Depends(get_current_user)):
    """删除分析历史"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    success = user_service.delete_analysis_history(current_user["user_id"], history_id)
    if success:
        return {"message": "删除成功"}
    else:
        raise HTTPException(status_code=404, detail="历史记录不存在或无权限删除")

# 对话功能接口
@app.post("/api/conversations")
async def create_conversation(
    request: dict, 
    current_user: dict = Depends(get_current_user)
):
    """创建新对话"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    history_id = request.get("history_id")
    title = request.get("title")
    
    if not history_id:
        raise HTTPException(status_code=400, detail="缺少历史记录ID")
    
    conversation_id = user_service.create_conversation(
        current_user["user_id"], 
        history_id, 
        title
    )
    
    if conversation_id:
        return {"conversation_id": conversation_id, "message": "对话创建成功"}
    else:
        # 检查是否是频率限制导致的失败
        # 这里我们通过检查最近的创建记录来判断
        # 由于频率限制检查在服务层，我们需要在API层提供更友好的错误信息
        raise HTTPException(
            status_code=429, 
            detail="创建对话过于频繁，请稍后再试（限制：每秒最多3次）"
        )

@app.get("/api/conversations")
async def get_conversations(
    history_id: int = None,
    current_user: dict = Depends(get_current_user)
):
    """获取对话列表"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    conversations = user_service.get_conversations(
        current_user["user_id"], 
        history_id
    )
    return {"conversations": conversations}

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取对话消息"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    messages = user_service.get_conversation_messages(
        current_user["user_id"], 
        conversation_id
    )
    return {"messages": messages}

@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """发送消息"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    message = request.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    # 保存用户消息
    success = user_service.add_conversation_message(
        current_user["user_id"],
        conversation_id,
        "user",
        message
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="保存用户消息失败")
    
    # 获取对话历史
    conversation_messages = user_service.get_conversation_messages(
        current_user["user_id"],
        conversation_id
    )
    
    # 获取对话关联的历史记录
    conversations = user_service.get_conversations(
        current_user["user_id"],
        None
    )
    
    target_conversation = None
    for conv in conversations:
        if conv["id"] == conversation_id:
            target_conversation = conv
            break
    
    if not target_conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 获取历史记录数据作为上下文
    history_records = user_service.get_analysis_history(
        current_user["user_id"],
        50
    )
    
    target_history = None
    for history in history_records:
        if history["id"] == target_conversation["history_id"]:
            target_history = history
            break
    
    if not target_history:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    
    # 构建分析上下文
    analysis_context = {
        "stock_codes": target_history["stock_codes"] or [],  # 提供默认空列表
        "market_type": target_history["market_type"] or "A",  # 提供默认市场类型
        "analysis_days": target_history["analysis_days"] or 30,  # 提供默认分析天数
        "analysis_result": target_history["analysis_result"] or {},  # 提供默认空字典
        "ai_output": target_history["ai_output"] or "",  # 提供默认空字符串
        "chart_data": target_history["chart_data"] or {}  # 提供默认空字典
    }
    
    # 创建AI分析器
    ai_analyzer = AIAnalyzer()
    
    # 定义流式生成器
    async def generate_conversation_stream():
        try:
            ai_response_content = ""
            async for response in ai_analyzer.get_conversation_response(
                conversation_messages,
                analysis_context,
                message,
                stream=True
            ):
                response_data = json.loads(response)
                
                # 收集AI回复内容
                if response_data.get("status") == "streaming" and "content" in response_data:
                    ai_response_content += response_data["content"]
                elif response_data.get("status") == "completed" and "content" in response_data:
                    ai_response_content += response_data["content"]
                
                yield response + '\n'
            
            # 保存AI回复
            if ai_response_content:
                user_service.add_conversation_message(
                    current_user["user_id"],
                    conversation_id,
                    "assistant",
                    ai_response_content
                )
                
        except Exception as e:
            logger.error(f"对话流式响应失败: {str(e)}")
            yield json.dumps({
                "error": f"对话响应失败: {str(e)}",
                "status": "error"
            }) + '\n'
    
    return StreamingResponse(
        generate_conversation_stream(), 
        media_type='application/json'
    )

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除对话"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    success = user_service.delete_conversation(
        current_user["user_id"],
        conversation_id
    )
    
    if success:
        return {"message": "删除成功"}
    else:
        raise HTTPException(status_code=404, detail="对话不存在或无权限删除")

@app.get("/api/conversations/prompts/random")
async def get_random_prompt(current_user: dict = Depends(get_current_user)):
    """获取随机对话提示词"""
    if not current_user["is_authenticated"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    ai_analyzer = AIAnalyzer()
    prompt = ai_analyzer.get_random_conversation_prompt()
    return {"prompt": prompt}

# 用户设置功能
@app.put("/api/user/settings")
async def update_settings(request: UserSettingsRequest, current_user: dict = Depends(get_current_user)):
    """更新用户设置"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    success = user_service.update_user_settings(current_user["user_id"], request)
    if success:
        return {"message": "设置更新成功"}
    else:
        raise HTTPException(status_code=400, detail="设置更新失败")

@app.get("/api/user/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """获取用户设置"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    settings = user_service.get_user_settings(current_user["user_id"])
    return {"settings": settings or {}}

# API配置管理接口
@app.get("/api/user/api-configs")
async def get_api_configs(current_user: dict = Depends(get_current_user)):
    """获取所有可用的API配置列表（仅返回配置名称和描述，不暴露敏感信息）"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    configs = []
    
    # 1. 环境配置（如果存在）
    env_api_url = os.getenv('API_URL', '')
    env_api_key = os.getenv('API_KEY', '')
    env_api_model = os.getenv('API_MODEL', '')
    
    if env_api_url and env_api_key:
        configs.append({
            "config_name": "环境配置",
            "description": "从环境变量配置的API",
            "source": "environment"
        })
    
    # 2. 数据库中的配置（仅返回必要信息，不暴露URL和密钥）
    db_configs = user_service.get_api_configurations(active_only=True)
    for config in db_configs:
        configs.append({
            "config_name": config["config_name"],
            "description": config.get("description", ""),
            "source": "database"
        })
    
    return {"configs": configs}

@app.get("/api/user/api-usage")
async def get_api_usage(
    config_name: Optional[str] = None,
    year_month: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取API用量统计"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    user_id = current_user["user_id"]
    
    # 获取月度汇总
    summary = user_service.get_monthly_usage_summary(user_id, year_month)
    
    # 获取详细记录
    records = user_service.get_api_usage(user_id, config_name, year_month)
    
    return {
        "summary": summary,
        "records": records
    }

@app.post("/api/user/api-configs")
async def add_api_config(
    config_data: APIConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """添加新的API配置（仅管理员或特殊用户）"""
    if not current_user["is_authenticated"] or not current_user["user_id"]:
        raise HTTPException(status_code=401, detail="请登录后再试")
    
    # TODO: 可以添加权限检查，限制只有管理员可以添加配置
    
    success = user_service.add_api_configuration(config_data)
    
    if success:
        return {"success": True, "message": "API配置添加成功"}
    else:
        raise HTTPException(status_code=400, detail="API配置添加失败，可能配置名称已存在")

# 获取系统配置
@app.get("/api/config")
async def get_config():
    """返回系统配置信息"""
    config = {
        'announcement': os.getenv('ANNOUNCEMENT_TEXT') or '',
        'default_api_url': os.getenv('API_URL', ''),
        'default_api_model': os.getenv('API_MODEL', ''),
        'default_api_timeout': os.getenv('API_TIMEOUT', '60'),
        'user_system_enabled': ENABLE_USER_SYSTEM,
        'require_login': ENABLE_USER_SYSTEM
    }
    return config

# 预设列表接口（最小实现，返回内置预设）
@app.get("/api/agent/presets")
async def list_agent_presets():
    try:
        presets = AgentOrchestrator.list_presets()
        return {"presets": presets}
    except Exception as e:
        logger.error(f"获取Agent预设失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Agent预设失败")
# AI分析股票
@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
    try:
        logger.info("开始处理分析请求")
        stock_codes = request.stock_codes
        market_type = request.market_type
        
        # 后端再次去重，确保安全
        original_count = len(stock_codes)
        stock_codes = list(dict.fromkeys(stock_codes))  # 保持原有顺序的去重方法
        if len(stock_codes) < original_count:
            logger.info(f"后端去重: 从{original_count}个代码中移除了{original_count - len(stock_codes)}个重复项")
        
        logger.debug(f"接收到分析请求: stock_codes={stock_codes}, market_type={market_type}")
        
        # 获取API配置
        custom_api_url = None
        custom_api_key = None
        custom_api_model = None
        custom_api_timeout = None
        effective_config_name = None  # 实际使用的配置名称
        
        # 优先级：config_name > 个性配置 > 环境配置
        if request.config_name and request.config_name.strip():
            # 使用指定的配置名称
            config_name = request.config_name.strip()
            effective_config_name = config_name
            
            if config_name == "环境配置":
                # 使用环境变量配置
                custom_api_url = os.getenv('API_URL', '')
                custom_api_key = os.getenv('API_KEY', '')
                custom_api_model = os.getenv('API_MODEL', '')
                custom_api_timeout = os.getenv('API_TIMEOUT', '')
                logger.debug(f"使用环境配置: URL={custom_api_url}, 模型={custom_api_model}")
            else:
                # 从数据库获取配置
                api_config = user_service.get_api_configuration(config_name)
                if api_config:
                    custom_api_url = api_config.api_url
                    custom_api_key = api_config.api_key
                    custom_api_model = api_config.api_model
                    logger.debug(f"使用数据库配置: {config_name}, URL={custom_api_url}, 模型={custom_api_model}")
                else:
                    logger.warning(f"未找到配置: {config_name}，使用默认配置")
                    effective_config_name = "个性配置"
        else:
            # 使用个性配置（request中直接提供的API参数）
            custom_api_url = request.api_url if request.api_url and request.api_url.strip() else None
            custom_api_key = request.api_key if request.api_key and request.api_key.strip() else None
            custom_api_model = request.api_model if request.api_model and request.api_model.strip() else None
            custom_api_timeout = request.api_timeout if request.api_timeout and request.api_timeout.strip() else None
            effective_config_name = "个性配置"
            logger.debug(f"使用个性配置: URL={custom_api_url}, 模型={custom_api_model}")
        
        analysis_days = request.analysis_days or 30  # 默认30天
        logger.info(f"📡 当前使用的API配置: {effective_config_name} | URL={'已配置' if custom_api_url else '未配置'} | Key={'已提供' if custom_api_key else '未提供'} | Model={custom_api_model or '默认'} | 分析天数={analysis_days}")
        logger.debug(f"有效配置名称: {effective_config_name}, API Key={'已提供' if custom_api_key else '未提供'}, Timeout={custom_api_timeout}, 分析天数={analysis_days}")
        
        # 如果提供了preset_id，则使用Orchestrator；否则保持原有StockAnalyzerService
        use_orchestrator = True if (request.preset_id and request.preset_id.strip()) else False
        if use_orchestrator:
            orchestrator = AgentOrchestrator(
                custom_api_url=custom_api_url,
                custom_api_key=custom_api_key,
                custom_api_model=custom_api_model,
                custom_api_timeout=custom_api_timeout
            )
        else:
            # 创建新的分析器实例，使用自定义配置
            custom_analyzer = StockAnalyzerService(
                custom_api_url=custom_api_url,
                custom_api_key=custom_api_key,
                custom_api_model=custom_api_model,
                custom_api_timeout=custom_api_timeout
            )
        
        if not stock_codes:
            logger.warning("未提供股票代码")
            raise HTTPException(status_code=400, detail="请输入代码")
        
        # 初始化分析历史记录（如果用户已登录）
        history_id = None
        if ENABLE_USER_SYSTEM and current_user["is_authenticated"] and current_user["user_id"]:
            history_id = user_service.save_analysis_history(
                current_user["user_id"], 
                stock_codes, 
                market_type, 
                analysis_days
            )
        
        # 定义流式生成器
        async def generate_stream():
            # 用于收集分析数据的变量
            collected_analysis_result = {}
            collected_ai_output = ""
            collected_chart_data = {}
            current_analysis_id = None  # 存储当前分析的UUID
            total_token_usage = {  # 收集token使用量
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated": False
            }
            
            if len(stock_codes) == 1:
                # 单个股票分析流式处理
                stock_code = stock_codes[0].strip()
                logger.info(f"开始单股流式分析: {stock_code}")
                
                stock_code_json = json.dumps(stock_code)
                init_message = f'{{"stream_type": "single", "stock_code": {stock_code_json}}}\n'
                yield init_message
                
                logger.debug(f"开始处理股票 {stock_code} 的流式响应")
                chunk_count = 0
                
                # 使用异步生成器
                if use_orchestrator:
                    async for chunk in orchestrator.run([stock_code], market_type, stream=True, analysis_days=analysis_days, preset_id=request.preset_id):
                        chunk_count += 1
                        # 收集chunk数据
                        try:
                            chunk_data = json.loads(chunk)
                            
                            # 提取analysis_id
                            if "orchestrator" in chunk_data and "analysis_id" in chunk_data["orchestrator"]:
                                current_analysis_id = chunk_data["orchestrator"]["analysis_id"]
                            
                            if "stock_code" in chunk_data and "score" in chunk_data:
                                collected_analysis_result[stock_code] = chunk_data
                            if "ai_analysis_chunk" in chunk_data:
                                collected_ai_output += chunk_data["ai_analysis_chunk"]
                            elif "analysis" in chunk_data and chunk_data.get("status") == "completed":
                                collected_ai_output = chunk_data["analysis"]
                            if "chart_data" in chunk_data:
                                collected_chart_data[stock_code] = chunk_data["chart_data"]
                            
                            # 收集token使用量
                            if "token_usage" in chunk_data:
                                usage = chunk_data["token_usage"]
                                total_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                                total_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                                total_token_usage["total_tokens"] += usage.get("total_tokens", 0)
                                if usage.get("estimated", False):
                                    total_token_usage["estimated"] = True
                        except json.JSONDecodeError:
                            pass
                        yield chunk + '\n'
                else:
                    async for chunk in custom_analyzer.analyze_stock(stock_code, market_type, stream=True, analysis_days=analysis_days):
                        chunk_count += 1
                        
                        # 解析chunk数据用于收集
                        try:
                            chunk_data = json.loads(chunk)
                            
                            # 收集基本分析结果
                            if "stock_code" in chunk_data and "score" in chunk_data:
                                collected_analysis_result[stock_code] = chunk_data
                            
                            # 收集AI分析输出
                            if "ai_analysis_chunk" in chunk_data:
                                collected_ai_output += chunk_data["ai_analysis_chunk"]
                            elif "analysis" in chunk_data and chunk_data.get("status") == "completed":
                                collected_ai_output = chunk_data["analysis"]
                            
                            # 收集图表数据
                            if "chart_data" in chunk_data:
                                collected_chart_data[stock_code] = chunk_data["chart_data"]
                            
                            # 收集token使用量
                            if "token_usage" in chunk_data:
                                usage = chunk_data["token_usage"]
                                total_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                                total_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                                total_token_usage["total_tokens"] += usage.get("total_tokens", 0)
                                if usage.get("estimated", False):
                                    total_token_usage["estimated"] = True
                                
                        except json.JSONDecodeError:
                            pass  # 忽略无法解析的chunk
                        
                        yield chunk + '\n'
                
                logger.info(f"股票 {stock_code} 流式分析完成，共发送 {chunk_count} 个块")
            else:
                # 批量分析流式处理
                logger.info(f"开始批量流式分析: {stock_codes}")
                
                stock_codes_json = json.dumps(stock_codes)
                init_message = f'{{"stream_type": "batch", "stock_codes": {stock_codes_json}}}\n'
                yield init_message
                
                logger.debug(f"开始处理批量股票的流式响应")
                chunk_count = 0
                
                # 使用异步生成器
                if use_orchestrator:
                    async for chunk in orchestrator.run(
                        [code.strip() for code in stock_codes],
                        market_type=market_type,
                        stream=True,
                        analysis_days=analysis_days,
                        preset_id=request.preset_id,
                    ):
                        chunk_count += 1
                        try:
                            chunk_data = json.loads(chunk)
                            if "stock_code" in chunk_data:
                                stock_code = chunk_data["stock_code"]
                                if "score" in chunk_data:
                                    collected_analysis_result[stock_code] = chunk_data
                                if "ai_analysis_chunk" in chunk_data:
                                    if not isinstance(collected_ai_output, dict):
                                        collected_ai_output = {}
                                    if stock_code not in collected_ai_output:
                                        collected_ai_output[stock_code] = ""
                                    collected_ai_output[stock_code] += chunk_data["ai_analysis_chunk"]
                                elif "analysis" in chunk_data and chunk_data.get("status") == "completed":
                                    if not isinstance(collected_ai_output, dict):
                                        collected_ai_output = {}
                                    collected_ai_output[stock_code] = chunk_data["analysis"]
                                if "chart_data" in chunk_data:
                                    collected_chart_data[stock_code] = chunk_data["chart_data"]
                            
                            # 收集token使用量
                            if "token_usage" in chunk_data:
                                usage = chunk_data["token_usage"]
                                total_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                                total_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                                total_token_usage["total_tokens"] += usage.get("total_tokens", 0)
                                if usage.get("estimated", False):
                                    total_token_usage["estimated"] = True
                        except json.JSONDecodeError:
                            pass
                        logger.debug(f"发送批量数据块 {chunk_count}: {chunk}")
                        yield chunk + '\n'
                else:
                    async for chunk in custom_analyzer.scan_stocks(
                        [code.strip() for code in stock_codes], 
                        min_score=0, 
                        market_type=market_type,
                        stream=True,
                        analysis_days=analysis_days
                    ):
                        chunk_count += 1
                        
                        # 解析chunk数据用于收集
                        try:
                            chunk_data = json.loads(chunk)
                            
                            # 收集基本分析结果
                            if "stock_code" in chunk_data:
                                stock_code = chunk_data["stock_code"]
                                if "score" in chunk_data:
                                    collected_analysis_result[stock_code] = chunk_data
                                
                                # 收集AI分析输出
                                if "ai_analysis_chunk" in chunk_data:
                                    if not isinstance(collected_ai_output, dict):
                                        collected_ai_output = {}
                                    if stock_code not in collected_ai_output:
                                        collected_ai_output[stock_code] = ""
                                    collected_ai_output[stock_code] += chunk_data["ai_analysis_chunk"]
                                elif "analysis" in chunk_data and chunk_data.get("status") == "completed":
                                    if not isinstance(collected_ai_output, dict):
                                        collected_ai_output = {}
                                    collected_ai_output[stock_code] = chunk_data["analysis"]
                                
                                # 收集图表数据
                                if "chart_data" in chunk_data:
                                    collected_chart_data[stock_code] = chunk_data["chart_data"]
                                
                                # 收集token使用量
                                if "token_usage" in chunk_data:
                                    usage = chunk_data["token_usage"]
                                    total_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                                    total_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                                    total_token_usage["total_tokens"] += usage.get("total_tokens", 0)
                                    if usage.get("estimated", False):
                                        total_token_usage["estimated"] = True
                                    
                        except json.JSONDecodeError:
                            pass  # 忽略无法解析的chunk
                        
                        logger.debug(f"发送批量数据块 {chunk_count}: {chunk}")
                        yield chunk + '\n'
                
                logger.info(f"批量流式分析完成，共发送 {chunk_count} 个块")
            
            # 流式响应完成后，更新历史记录
            if history_id and (collected_analysis_result or collected_ai_output or collected_chart_data):
                try:
                    logger.info(f"准备更新历史记录，收集的数据:")
                    logger.info(f"  - analysis_result: {len(collected_analysis_result)} 条记录")
                    logger.info(f"  - ai_output 类型: {type(collected_ai_output)}, 内容长度: {len(str(collected_ai_output))}")
                    logger.info(f"  - chart_data: {len(collected_chart_data)} 条记录")
                    
                    # 准备AI输出文本
                    ai_output_text = ""
                    if isinstance(collected_ai_output, str):
                        ai_output_text = collected_ai_output
                    elif isinstance(collected_ai_output, dict):
                        ai_output_text = "\n\n".join([f"【{code}】\n{output}" for code, output in collected_ai_output.items()])
                    
                    logger.info(f"最终AI输出文本长度: {len(ai_output_text)}")
                    
                    # 更新历史记录
                    user_service.save_analysis_history(
                        current_user["user_id"],
                        stock_codes,
                        market_type,
                        analysis_days,
                        analysis_result=collected_analysis_result,
                        ai_output=ai_output_text,
                        chart_data=collected_chart_data,
                        analysis_id=current_analysis_id
                    )
                    logger.info(f"历史记录更新成功，ID: {history_id}")
                except Exception as e:
                    logger.error(f"更新历史记录失败: {str(e)}")
                    logger.exception(e)
            
            # 记录token使用量（如果用户已登录且有token使用）
            if (ENABLE_USER_SYSTEM and current_user["is_authenticated"] and 
                current_user["user_id"] and total_token_usage["total_tokens"] > 0):
                try:
                    user_service.record_api_usage(
                        user_id=current_user["user_id"],
                        config_name=effective_config_name or "未知配置",
                        usage_data=total_token_usage
                    )
                    logger.info(f"Token使用量记录成功: 配置={effective_config_name}, 总tokens={total_token_usage['total_tokens']}")
                except Exception as e:
                    logger.error(f"记录token使用量失败: {str(e)}")
                    logger.exception(e)
        
        logger.info("成功创建流式响应生成器")
        return StreamingResponse(generate_stream(), media_type='application/json')
            
    except Exception as e:
        error_msg = f"分析时出错: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        raise HTTPException(status_code=500, detail=error_msg)

# 搜索美股代码
@app.get("/api/search_us_stocks")
async def search_us_stocks(keyword: str = "", username: str = Depends(verify_token)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        # 直接使用异步服务的异步方法
        results = await us_stock_service.search_us_stocks(keyword)
        return {"results": results}
        
    except Exception as e:
        logger.error(f"搜索美股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索基金代码
@app.get("/api/search_funds")
async def search_funds(keyword: str = "", market_type: str = "", username: str = Depends(verify_token)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        # 直接使用异步服务的异步方法
        results = await fund_service.search_funds(keyword, market_type)
        return {"results": results}
        
    except Exception as e:
        logger.error(f"搜索基金代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取美股详情
@app.get("/api/us_stock_detail/{symbol}")
async def get_us_stock_detail(symbol: str, username: str = Depends(verify_token)):
    try:
        if not symbol:
            raise HTTPException(status_code=400, detail="请提供股票代码")
        
        # 使用异步服务获取详情
        detail = await us_stock_service.get_us_stock_detail(symbol)
        return detail
        
    except Exception as e:
        logger.error(f"获取美股详情时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取基金详情
@app.get("/api/fund_detail/{symbol}")
async def get_fund_detail(symbol: str, market_type: str = "ETF", username: str = Depends(verify_token)):
    try:
        if not symbol:
            raise HTTPException(status_code=400, detail="请提供基金代码")
        
        # 使用异步服务获取详情
        detail = await fund_service.get_fund_detail(symbol, market_type)
        return detail
        
    except Exception as e:
        logger.error(f"获取基金详情时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 测试API连接
@app.post("/api/test_api_connection")
async def test_api_connection(request: TestAPIRequest, username: str = Depends(verify_token)):
    """测试API连接"""
    try:
        logger.info("开始测试API连接")
        api_url = request.api_url
        api_key = request.api_key
        api_model = request.api_model
        api_timeout = request.api_timeout
        
        logger.debug(f"测试API连接: URL={api_url}, 模型={api_model}, API Key={'已提供' if api_key else '未提供'}, Timeout={api_timeout}")
        
        if not api_url:
            logger.warning("未提供API URL")
            raise HTTPException(status_code=400, detail="请提供API URL")
            
        if not api_key:
            logger.warning("未提供API Key")
            raise HTTPException(status_code=400, detail="请提供API Key")
            
        # 构建API URL
        test_url = APIUtils.format_api_url(api_url)
        logger.debug(f"完整API测试URL: {test_url}")
        
        # 使用异步HTTP客户端发送测试请求
        async with httpx.AsyncClient(timeout=float(api_timeout)) as client:
            response = await client.post(
                test_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": api_model or "",
                    "messages": [
                        {"role": "user", "content": "Hello, this is a test message. Please respond with 'API connection successful'."}
                    ],
                    "max_tokens": 20
                }
            )
        
        # 检查响应
        if response.status_code == 200:
            logger.info(f"API 连接测试成功: {response.status_code}")
            return {"success": True, "message": "API 连接测试成功"}
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', str(error_data))
            except json.JSONDecodeError:
                error_message = response.text or "服务器返回了空的错误响应"
            
            logger.warning(f"API连接测试失败: {response.status_code} - {error_message}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"API 连接测试失败: {error_message}", "status_code": response.status_code}
            )
            
    except httpx.RequestError as e:
        logger.error(f"API 连接请求错误: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"请求错误: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"测试 API 连接时出错: {str(e)}")
        logger.exception(e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"API 测试连接时出错: {str(e)}"}
        )

# 检查是否需要登录
@app.get("/api/need_login")
async def need_login():
    """检查是否需要登录"""
    # 是否需要认证取决于是否启用用户系统
    return {
        "require_login": ENABLE_USER_SYSTEM,
        "user_system_enabled": ENABLE_USER_SYSTEM,
        "allow_anonymous": ALLOW_ANONYMOUS
    }

# 设置静态文件
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist')
if os.path.exists(frontend_dist):
    # 直接挂载整个dist目录
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
    logger.info(f"前端构建目录挂载成功: {frontend_dist}")
else:
    logger.warning("前端构建目录不存在，仅API功能可用")


if __name__ == '__main__':
    uvicorn.run("web_server:app", host="0.0.0.0", port=8888, reload=True)