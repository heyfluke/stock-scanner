#!/usr/bin/env python3
"""
数据库迁移管理工具
提供查看状态、运行迁移、回滚等功能
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database_migrator import DatabaseMigrator

def show_status(database_url: str):
    """显示数据库状态"""
    try:
        migrator = DatabaseMigrator(database_url)
        current_version = migrator.get_current_version()
        migrations = migrator.get_migrations()
        history = migrator.get_migration_history()
        
        print("=" * 60)
        print("数据库迁移状态")
        print("=" * 60)
        print(f"数据库: {database_url}")
        print(f"当前版本: {current_version}")
        print(f"最新版本: {max(mig['version'] for mig in migrations)}")
        print()
        
        print("可用迁移:")
        for migration in migrations:
            status = "✅ 已应用" if migration["version"] <= current_version else "⏳ 待应用"
            print(f"  v{migration['version']:2d}: {migration['name']:<25} - {migration['description']} [{status}]")
        
        print()
        if history:
            print("迁移历史:")
            for record in history:
                print(f"  v{record['version']:2d}: {record['name']:<25} - {record['applied_at']}")
        
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")

def run_migration_command(database_url: str, target_version: int = None, backup: bool = True):
    """运行迁移命令"""
    try:
        from utils.database_migrator import run_migration
        
        print("=" * 60)
        print("执行数据库迁移")
        print("=" * 60)
        
        success = run_migration(
            database_url=database_url,
            target_version=target_version,
            backup=backup
        )
        
        return success
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

def show_help():
    """显示帮助信息"""
    print("""
数据库迁移管理工具

使用方法:
  python manage_migrations.py status                    # 查看迁移状态
  python manage_migrations.py migrate [--version N]     # 运行迁移到指定版本
  python manage_migrations.py migrate --latest          # 运行迁移到最新版本
  python manage_migrations.py help                      # 显示此帮助

选项:
  --database <URL>    数据库URL (默认: sqlite:///./data/stock_scanner.db)
  --version <N>       目标版本号
  --no-backup         不备份数据库
  --latest            迁移到最新版本

示例:
  python manage_migrations.py status
  python manage_migrations.py migrate --latest
  python manage_migrations.py migrate --version 3
  python manage_migrations.py migrate --database sqlite:///./custom.db --no-backup
""")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移管理工具", add_help=False)
    parser.add_argument("command", choices=["status", "migrate", "help"], help="命令")
    parser.add_argument("--database", help="数据库URL")
    parser.add_argument("--version", type=int, help="目标版本")
    parser.add_argument("--latest", action="store_true", help="迁移到最新版本")
    parser.add_argument("--no-backup", action="store_true", help="不备份数据库")
    
    args = parser.parse_args()
    
    # 设置默认数据库路径
    if not args.database:
        args.database = "sqlite:///./data/stock_scanner.db"
    
    if args.command == "help":
        show_help()
        sys.exit(0)
    
    elif args.command == "status":
        show_status(args.database)
        sys.exit(0)
    
    elif args.command == "migrate":
        target_version = None
        if args.latest:
            target_version = None  # 使用最新版本
        elif args.version:
            target_version = args.version
        
        success = run_migration_command(
            database_url=args.database,
            target_version=target_version,
            backup=not args.no_backup
        )
        
        sys.exit(0 if success else 1)
    
    else:
        print(f"❌ 未知命令: {args.command}")
        show_help()
        sys.exit(1) 