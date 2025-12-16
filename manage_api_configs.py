#!/usr/bin/env python3
"""
API配置管理脚本
用于添加、列出、删除AI API配置
"""
import os
import sys
import argparse
from typing import Optional
from dotenv import load_dotenv
from services.user_service import user_service, APIConfigRequest
from utils.logger import get_logger

load_dotenv()
logger = get_logger()

class APIConfigManager:
    """API配置管理器"""
    
    def __init__(self, database_url=None):
        # 如果指定了数据库路径，使用指定的；否则使用默认的
        if database_url:
            from services.user_service import UserService
            self.user_service = UserService(database_url=database_url)
        else:
            self.user_service = user_service
    
    def add_config(self, config_name: str, api_url: str, api_key: str, 
                   api_model: str, description: Optional[str] = None) -> bool:
        """添加API配置"""
        try:
            config_request = APIConfigRequest(
                config_name=config_name,
                api_url=api_url,
                api_key=api_key,
                api_model=api_model,
                description=description
            )
            
            success = self.user_service.add_api_configuration(config_request)
            
            if success:
                print(f"✓ API配置添加成功: {config_name}")
                print(f"  URL: {api_url}")
                print(f"  模型: {api_model}")
                if description:
                    print(f"  描述: {description}")
                return True
            else:
                print(f"✗ API配置添加失败: {config_name} (可能已存在)")
                return False
                
        except Exception as e:
            print(f"✗ 添加API配置时出错: {str(e)}")
            logger.error(f"添加API配置时出错: {str(e)}")
            return False
    
    def list_configs(self, show_all: bool = False) -> None:
        """列出所有API配置"""
        try:
            configs = self.user_service.get_api_configurations(
                active_only=not show_all, 
                include_sensitive=True  # 管理脚本显示敏感信息
            )
            
            if not configs:
                print("没有找到任何API配置")
                return
            
            print(f"\n{'='*80}")
            print(f"共找到 {len(configs)} 个API配置:")
            print(f"{'='*80}\n")
            
            for i, config in enumerate(configs, 1):
                print(f"{i}. {config['config_name']}")
                print(f"   URL: {config['api_url']}")
                print(f"   密钥: {config['api_key']}")  # 已隐藏
                print(f"   模型: {config['api_model']}")
                if config.get('description'):
                    print(f"   描述: {config['description']}")
                print(f"   状态: {'激活' if config['is_active'] else '停用'}")
                print(f"   创建时间: {config['created_at']}")
                print()
            
        except Exception as e:
            print(f"✗ 获取API配置列表时出错: {str(e)}")
            logger.error(f"获取API配置列表时出错: {str(e)}")
    
    def delete_config(self, config_name: str) -> bool:
        """删除API配置"""
        try:
            # 确认删除
            confirm = input(f"确定要删除配置 '{config_name}' 吗？(y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return False
            
            success = self.user_service.delete_api_configuration(config_name)
            
            if success:
                print(f"✓ API配置删除成功: {config_name}")
                return True
            else:
                print(f"✗ API配置删除失败: {config_name} (可能不存在)")
                return False
                
        except Exception as e:
            print(f"✗ 删除API配置时出错: {str(e)}")
            logger.error(f"删除API配置时出错: {str(e)}")
            return False
    
    def show_usage(self, config_name: Optional[str] = None) -> None:
        """显示API用量统计"""
        print("用量统计功能尚未实现，需要用户登录后查看")
        print("请使用前端界面查看个人API用量")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="API配置管理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  添加配置:
    python manage_api_configs.py --add --config-name openai-gpt4 \\
        --url https://api.openai.com/v1/ \\
        --key sk-your-api-key \\
        --model gpt-4o \\
        --description "OpenAI GPT-4o"
  
  列出所有配置:
    python manage_api_configs.py --list
  
  删除配置:
    python manage_api_configs.py --delete --config-name openai-gpt4
  
  使用Docker开发环境的数据库:
    python manage_api_configs.py --list --db data/stock_scanner.db
        """
    )
    
    # 操作参数
    parser.add_argument('--add', action='store_true', help='添加新的API配置')
    parser.add_argument('--list', action='store_true', help='列出所有API配置')
    parser.add_argument('--delete', action='store_true', help='删除API配置')
    parser.add_argument('--usage', action='store_true', help='显示用量统计')
    
    # 配置参数
    parser.add_argument('--config-name', type=str, help='配置名称（唯一标识）')
    parser.add_argument('--url', type=str, help='API URL')
    parser.add_argument('--key', type=str, help='API密钥')
    parser.add_argument('--model', type=str, help='模型名称')
    parser.add_argument('--description', type=str, help='配置描述')
    
    # 其他参数
    parser.add_argument('--all', action='store_true', help='显示所有配置（包括停用的）')
    parser.add_argument('--db', type=str, help='指定数据库路径（默认：sqlite:///./stock_scanner.db）')
    
    args = parser.parse_args()
    
    # 如果没有任何操作参数，显示帮助
    if not (args.add or args.list or args.delete or args.usage):
        parser.print_help()
        return
    
    # 构建数据库URL
    database_url = None
    if args.db:
        database_url = f"sqlite:///{args.db}"
        print(f"📁 使用数据库: {database_url}")
        print()
    
    manager = APIConfigManager(database_url=database_url)
    
    try:
        # 添加配置
        if args.add:
            if not all([args.config_name, args.url, args.key, args.model]):
                print("✗ 添加配置需要提供: --config-name, --url, --key, --model")
                sys.exit(1)
            
            success = manager.add_config(
                config_name=args.config_name,
                api_url=args.url,
                api_key=args.key,
                api_model=args.model,
                description=args.description
            )
            sys.exit(0 if success else 1)
        
        # 列出配置
        elif args.list:
            manager.list_configs(show_all=args.all)
        
        # 删除配置
        elif args.delete:
            if not args.config_name:
                print("✗ 删除配置需要提供: --config-name")
                sys.exit(1)
            
            success = manager.delete_config(args.config_name)
            sys.exit(0 if success else 1)
        
        # 显示用量
        elif args.usage:
            manager.show_usage(args.config_name)
    
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 发生错误: {str(e)}")
        logger.error(f"管理脚本错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

