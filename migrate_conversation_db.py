#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加对话功能表
"""

import os
import sys
from sqlmodel import SQLModel, create_engine
from services.user_service import Conversation, ConversationMessage

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_database():
    """执行数据库迁移"""
    try:
        # 数据库路径
        db_path = "data/stock_scanner.db"
        
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        
        # 创建数据库引擎
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url, echo=True)
        
        print("开始创建对话功能相关表...")
        
        # 创建新表
        SQLModel.metadata.create_all(engine, tables=[
            Conversation.__table__,
            ConversationMessage.__table__
        ])
        
        print("✅ 对话功能表创建成功!")
        print(f"   - conversations 表")
        print(f"   - conversation_messages 表")
        print(f"数据库文件: {db_path}")
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 50)
    print("股票分析系统 - 对话功能数据库迁移")
    print("=" * 50)
    
    migrate_database()
    
    print("\n迁移完成! 现在可以启动应用了。") 