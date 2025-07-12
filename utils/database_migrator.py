#!/usr/bin/env python3
"""
数据库迁移系统
支持版本控制和自动迁移
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlmodel import SQLModel, create_engine, Session, text
from utils.logger import get_logger

logger = get_logger()

class DatabaseMigrator:
    """数据库迁移管理器"""
    
    def __init__(self, database_url: str = None):
        """初始化迁移器"""
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///./data/stock_scanner.db")
        
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        
        # 确保数据目录存在
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        try:
            with Session(self.engine) as session:
                # 检查是否存在版本表
                result = session.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='database_version'
                """)).first()
                
                if not result:
                    # 版本表不存在，检查是否有基础表来判断版本
                    return self._detect_existing_version(session)
                
                # 获取当前版本
                result = session.execute(text("SELECT version FROM database_version ORDER BY id DESC LIMIT 1")).first()
                return result[0] if result else 0
                
        except Exception as e:
            logger.warning(f"获取数据库版本失败: {e}")
            return 0
    
    def _detect_existing_version(self, session: Session) -> int:
        """检测现有数据库的版本"""
        try:
            # 检查是否存在基础表
            tables_result = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'user_favorites', 'analysis_history')
            """)).all()
            
            existing_tables = [row[0] for row in tables_result]
            
            # 如果存在基础表，说明是版本1
            if 'users' in existing_tables and 'user_favorites' in existing_tables and 'analysis_history' in existing_tables:
                logger.info("检测到现有数据库包含基础表，推断为版本1")
                return 1
            
            # 检查是否有对话表
            conv_tables_result = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('conversations', 'conversation_messages')
            """)).all()
            
            conv_tables = [row[0] for row in conv_tables_result]
            
            if 'conversations' in conv_tables and 'conversation_messages' in conv_tables:
                logger.info("检测到现有数据库包含对话表，推断为版本2")
                return 2
            
            # 检查是否有用户设置表
            settings_result = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name = 'user_settings'
            """)).first()
            
            if settings_result:
                logger.info("检测到现有数据库包含用户设置表，推断为版本3")
                return 3
            
            # 检查分析历史表是否有新字段
            try:
                columns_result = session.execute(text("PRAGMA table_info(analysis_history)")).all()
                columns = [row[1] for row in columns_result]
                
                if 'ai_output' in columns and 'chart_data' in columns:
                    logger.info("检测到现有数据库包含AI输出字段，推断为版本4")
                    return 4
            except:
                pass
            
            return 0
            
        except Exception as e:
            logger.warning(f"检测现有版本失败: {e}")
            return 0
    
    def create_version_table(self):
        """创建版本表"""
        try:
            with Session(self.engine) as session:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS database_version (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version INTEGER NOT NULL,
                        migration_name TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """))
                session.commit()
                logger.info("版本表创建成功")
        except Exception as e:
            logger.error(f"创建版本表失败: {e}")
            raise
    
    def record_migration(self, version: int, migration_name: str, description: str = ""):
        """记录迁移历史"""
        try:
            with Session(self.engine) as session:
                # 使用SQLAlchemy的execute方法而不是SQLModel的exec
                session.execute(text("""
                    INSERT INTO database_version (version, migration_name, description)
                    VALUES (:version, :migration_name, :description)
                """), {
                    "version": version,
                    "migration_name": migration_name,
                    "description": description
                })
                session.commit()
                logger.info(f"记录迁移: v{version} - {migration_name}")
        except Exception as e:
            logger.error(f"记录迁移失败: {e}")
            raise
    
    def get_migrations(self) -> List[Dict[str, Any]]:
        """获取所有迁移定义"""
        return [
            {
                "version": 1,
                "name": "initial_schema",
                "description": "初始数据库结构",
                "migrate": self._migrate_to_v1
            },
            {
                "version": 2,
                "name": "add_conversation_tables",
                "description": "添加对话功能表",
                "migrate": self._migrate_to_v2
            },
            {
                "version": 3,
                "name": "add_user_settings_table",
                "description": "添加用户设置表",
                "migrate": self._migrate_to_v3
            },
            {
                "version": 4,
                "name": "add_analysis_history_ai_fields",
                "description": "为分析历史添加AI输出和图表数据字段",
                "migrate": self._migrate_to_v4
            }
        ]
    
    def migrate(self, target_version: Optional[int] = None) -> bool:
        """执行数据库迁移"""
        try:
            logger.info("开始数据库迁移...")
            
            # 创建版本表（如果不存在）
            self.create_version_table()
            
            # 获取当前版本
            current_version = self.get_current_version()
            logger.info(f"当前数据库版本: {current_version}")
            
            # 如果检测到现有版本但没有版本记录，先记录当前版本
            if current_version > 0:
                with Session(self.engine) as session:
                    # 检查是否已有版本记录
                    existing_record = session.execute(text("""
                        SELECT COUNT(*) FROM database_version WHERE version = :version
                    """), {"version": current_version}).first()
                    
                    if not existing_record or existing_record[0] == 0:
                        # 记录检测到的版本
                        self.record_migration(
                            current_version,
                            f"detected_v{current_version}",
                            f"检测到的现有数据库版本 {current_version}"
                        )
                        logger.info(f"已记录检测到的版本: v{current_version}")
            
            # 获取所有迁移
            migrations = self.get_migrations()
            
            # 确定目标版本
            if target_version is None:
                target_version = max(mig["version"] for mig in migrations)
            
            logger.info(f"目标版本: {target_version}")
            
            if current_version >= target_version:
                logger.info("数据库已是最新版本，无需迁移")
                return True
            
            # 执行迁移
            for migration in migrations:
                if migration["version"] > current_version and migration["version"] <= target_version:
                    logger.info(f"执行迁移: v{migration['version']} - {migration['name']}")
                    
                    # 执行迁移
                    migration["migrate"]()
                    
                    # 记录迁移
                    self.record_migration(
                        migration["version"],
                        migration["name"],
                        migration["description"]
                    )
                    
                    current_version = migration["version"]
            
            logger.info(f"数据库迁移完成，当前版本: {current_version}")
            return True
            
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            return False
    
    async def check_and_apply_migrations(self) -> bool:
        """异步检查并应用迁移（用于应用启动时）"""
        try:
            # 在后台线程中运行迁移
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.migrate)
        except Exception as e:
            logger.error(f"异步迁移检查失败: {e}")
            return False
    
    def _migrate_to_v1(self):
        """迁移到版本1：初始数据库结构"""
        try:
            # 导入所有模型以确保表被创建
            from services.user_service import User, UserFavorite, AnalysisHistory
            
            # 创建基础表
            SQLModel.metadata.create_all(self.engine, tables=[
                User.__table__,
                UserFavorite.__table__,
                AnalysisHistory.__table__
            ])
            
            logger.info("v1迁移完成：初始数据库结构创建成功")
            
        except Exception as e:
            logger.error(f"v1迁移失败: {e}")
            raise
    
    def _migrate_to_v2(self):
        """迁移到版本2：添加对话功能表"""
        try:
            from services.user_service import Conversation, ConversationMessage
            
            # 创建对话相关表
            SQLModel.metadata.create_all(self.engine, tables=[
                Conversation.__table__,
                ConversationMessage.__table__
            ])
            
            logger.info("v2迁移完成：对话功能表创建成功")
            
        except Exception as e:
            logger.error(f"v2迁移失败: {e}")
            raise
    
    def _migrate_to_v3(self):
        """迁移到版本3：添加用户设置表"""
        try:
            from services.user_service import UserSettings
            
            # 创建用户设置表
            SQLModel.metadata.create_all(self.engine, tables=[
                UserSettings.__table__
            ])
            
            logger.info("v3迁移完成：用户设置表创建成功")
            
        except Exception as e:
            logger.error(f"v3迁移失败: {e}")
            raise
    
    def _migrate_to_v4(self):
        """迁移到版本4：为分析历史添加AI输出和图表数据字段"""
        try:
            with Session(self.engine) as session:
                # 检查字段是否已存在
                result = session.execute(text("""
                    PRAGMA table_info(analysis_history)
                """)).all()
                
                columns = [row[1] for row in result]
                
                # 添加ai_output字段
                if 'ai_output' not in columns:
                    session.execute(text("""
                        ALTER TABLE analysis_history 
                        ADD COLUMN ai_output TEXT
                    """))
                    logger.info("添加ai_output字段")
                
                # 添加chart_data字段
                if 'chart_data' not in columns:
                    session.execute(text("""
                        ALTER TABLE analysis_history 
                        ADD COLUMN chart_data TEXT
                    """))
                    logger.info("添加chart_data字段")
                
                session.commit()
            
            logger.info("v4迁移完成：分析历史字段更新成功")
            
        except Exception as e:
            logger.error(f"v4迁移失败: {e}")
            raise
    
    def backup_database(self) -> str:
        """备份数据库"""
        try:
            if self.database_url.startswith("sqlite:///"):
                db_path = self.database_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    import shutil
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"数据库备份成功: {backup_path}")
                    return backup_path
            return ""
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return ""
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        try:
            with Session(self.engine) as session:
                result = session.execute(text("""
                    SELECT version, migration_name, applied_at, description
                    FROM database_version
                    ORDER BY version ASC
                """)).all()
                
                return [
                    {
                        "version": row[0],
                        "name": row[1],
                        "applied_at": row[2],
                        "description": row[3]
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"获取迁移历史失败: {e}")
            return []

def run_migration(database_url: str = None, target_version: int = None, backup: bool = True) -> bool:
    """运行数据库迁移"""
    try:
        migrator = DatabaseMigrator(database_url)
        
        # 备份数据库
        if backup:
            backup_path = migrator.backup_database()
            if backup_path:
                print(f"数据库已备份到: {backup_path}")
        
        # 执行迁移
        success = migrator.migrate(target_version)
        
        if success:
            print("✅ 数据库迁移成功!")
            
            # 显示迁移历史
            history = migrator.get_migration_history()
            if history:
                print("\n迁移历史:")
                for record in history:
                    print(f"  v{record['version']}: {record['name']} - {record['description']}")
                    print(f"    应用时间: {record['applied_at']}")
        else:
            print("❌ 数据库迁移失败!")
        
        return success
        
    except Exception as e:
        print(f"❌ 迁移过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("--database", help="数据库URL")
    parser.add_argument("--version", type=int, help="目标版本")
    parser.add_argument("--no-backup", action="store_true", help="不备份数据库")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("股票分析系统 - 数据库迁移工具")
    print("=" * 50)
    
    success = run_migration(
        database_url=args.database,
        target_version=args.version,
        backup=not args.no_backup
    )
    
    sys.exit(0 if success else 1) 