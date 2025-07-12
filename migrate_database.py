#!/usr/bin/env python3
"""
数据库迁移脚本
使用方法: python migrate_database.py [--database <数据库路径>] [--version <目标版本>] [--no-backup]
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database_migrator import run_migration

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="股票分析系统 - 数据库迁移工具")
    parser.add_argument("--database", help="数据库URL (默认: sqlite:///./data/stock_scanner.db)")
    parser.add_argument("--version", type=int, help="目标版本 (默认: 最新版本)")
    parser.add_argument("--no-backup", action="store_true", help="不备份数据库")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("股票分析系统 - 数据库迁移工具")
    print("=" * 60)
    
    # 设置默认数据库路径
    if not args.database:
        args.database = "sqlite:///./data/stock_scanner.db"
    
    print(f"数据库: {args.database}")
    print(f"目标版本: {args.version or '最新版本'}")
    print(f"备份数据库: {'否' if args.no_backup else '是'}")
    print()
    
    success = run_migration(
        database_url=args.database,
        target_version=args.version,
        backup=not args.no_backup
    )
    
    if success:
        print("\n🎉 迁移完成! 现在可以启动应用了。")
    else:
        print("\n💥 迁移失败! 请检查错误信息。")
    
    sys.exit(0 if success else 1) 