#!/usr/bin/env python3
"""
API测试运行器 - 统一的HTTP接口测试工具
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_api_endpoints import TestAPIEndpoints
from tests.test_api_quick import test_a_stock_analysis

def print_banner():
    """打印测试横幅"""
    print("=" * 80)
    print("🌐 股票分析系统 HTTP API 测试套件")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def print_test_options():
    """打印测试选项"""
    print("\n📋 可用测试选项:")
    print("1. quick     - 快速A股分析测试（验证修复效果）")
    print("2. full      - 完整API端点测试")
    print("3. health    - 仅测试服务器健康状态")
    print("4. analyze   - 仅测试股票分析接口")
    print("5. stream    - 仅测试流式分析接口")
    print("6. search    - 仅测试搜索接口")
    print("7. scan      - 仅测试扫描接口")
    print("8. perf      - 仅测试性能")

async def run_quick_test(base_url: str, stock_code: str = "688385", username: str = "demo", password: str = "demo"):
    """运行快速A股测试"""
    print("🚀 运行快速A股分析测试...")
    try:
        return await test_a_stock_analysis(base_url, stock_code, username, password)
    except Exception as e:
        print(f"快速测试执行失败: {str(e)}")
        return False

async def run_full_test(base_url: str, username: str = "demo", password: str = "demo"):
    """运行完整API测试"""
    print("🚀 运行完整API端点测试...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    return await test_suite.run_all_tests()

async def run_health_test(base_url: str):
    """仅测试服务器健康状态"""
    print("🚀 测试服务器健康状态...")
    test_suite = TestAPIEndpoints(base_url)
    await test_suite.setup_session()
    try:
        result = await test_suite.test_server_health()
        print(f"结果: {'✓ 通过' if result else '✗ 失败'}")
        return result
    finally:
        await test_suite.cleanup_session()

async def run_analyze_test(base_url: str, username: str = "demo", password: str = "demo"):
    """仅测试股票分析接口"""
    print("🚀 测试股票分析接口...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    await test_suite.setup_session()
    try:
        # 先登录
        if not await test_suite.login():
            print("登录失败，无法继续测试")
            return False
            
        results = {}
        for market_type, stock_info in test_suite.test_stocks.items():
            stock_code = stock_info['code']
            result = await test_suite.test_stock_analysis(market_type, stock_code)
            results[f"{market_type}_{stock_code}"] = result
        
        passed = sum(results.values())
        total = len(results)
        print(f"\n分析测试结果: {passed}/{total} 通过")
        return passed == total
    finally:
        await test_suite.cleanup_session()

async def run_stream_test(base_url: str, username: str = "demo", password: str = "demo"):
    """仅测试流式分析接口"""
    print("🚀 测试流式分析接口...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    await test_suite.setup_session()
    try:
        # 先登录
        if not await test_suite.login():
            print("登录失败，无法继续测试")
            return False
            
        results = {}
        for market_type, stock_info in test_suite.test_stocks.items():
            stock_code = stock_info['code']
            result = await test_suite.test_stock_analysis_stream(market_type, stock_code)
            results[f"{market_type}_{stock_code}"] = result
        
        passed = sum(results.values())
        total = len(results)
        print(f"\n流式测试结果: {passed}/{total} 通过")
        return passed == total
    finally:
        await test_suite.cleanup_session()

async def run_search_test(base_url: str, username: str = "demo", password: str = "demo"):
    """仅测试搜索接口"""
    print("🚀 测试搜索接口...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    await test_suite.setup_session()
    try:
        # 先登录
        if not await test_suite.login():
            print("登录失败，无法继续测试")
            return False
            
        results = {}
        results['us_search'] = await test_suite.test_us_stock_search('TSLA')
        results['fund_search'] = await test_suite.test_fund_search('科技', 'ETF')
        
        passed = sum(results.values())
        total = len(results)
        print(f"\n搜索测试结果: {passed}/{total} 通过")
        return passed == total
    finally:
        await test_suite.cleanup_session()

async def run_scan_test(base_url: str, username: str = "demo", password: str = "demo"):
    """仅测试扫描接口"""
    print("🚀 测试扫描接口...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    await test_suite.setup_session()
    try:
        # 先登录
        if not await test_suite.login():
            print("登录失败，无法继续测试")
            return False
            
        result = await test_suite.test_stock_scan('A', ['688385', '000001'])
        print(f"\n扫描测试结果: {'✓ 通过' if result else '✗ 失败'}")
        return result
    finally:
        await test_suite.cleanup_session()

async def run_perf_test(base_url: str, username: str = "demo", password: str = "demo"):
    """仅测试性能"""
    print("🚀 测试API性能...")
    test_suite = TestAPIEndpoints(base_url, username, password)
    await test_suite.setup_session()
    try:
        # 先登录
        if not await test_suite.login():
            print("登录失败，无法继续测试")
            return False
            
        results = {}
        for market_type, stock_info in test_suite.test_stocks.items():
            stock_code = stock_info['code']
            result = await test_suite.test_api_performance(market_type, stock_code)
            results[f"{market_type}_{stock_code}"] = result
        
        passed = sum(results.values())
        total = len(results)
        print(f"\n性能测试结果: {passed}/{total} 通过")
        return passed == total
    finally:
        await test_suite.cleanup_session()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="API测试运行器")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="quick",
        choices=["quick", "full", "health", "analyze", "stream", "search", "scan", "perf"],
        help="测试类型"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8888",
        help="API服务器地址 (默认: http://localhost:8888)"
    )
    parser.add_argument(
        "--code",
        default="688385",
        help="股票代码（快速测试用）"
    )
    parser.add_argument(
        "--username",
        default="demo",
        help="登录用户名 (默认: demo)"
    )
    parser.add_argument(
        "--password",
        default="demo",
        help="登录密码 (默认: demo)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    print(f"测试服务器: {args.url}")
    print(f"测试类型: {args.test_type}")
    print(f"登录账号: {args.username}")
    
    try:
        success = False
        
        if args.test_type == "quick":
            success = await run_quick_test(args.url, args.code, args.username, args.password)
        elif args.test_type == "full":
            result = await run_full_test(args.url, args.username, args.password)
            success = isinstance(result, dict) and sum(result.values()) > 0
        elif args.test_type == "health":
            success = await run_health_test(args.url)
        elif args.test_type == "analyze":
            success = await run_analyze_test(args.url, args.username, args.password)
        elif args.test_type == "stream":
            success = await run_stream_test(args.url, args.username, args.password)
        elif args.test_type == "search":
            success = await run_search_test(args.url, args.username, args.password)
        elif args.test_type == "scan":
            success = await run_scan_test(args.url, args.username, args.password)
        elif args.test_type == "perf":
            success = await run_perf_test(args.url, args.username, args.password)
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 API测试通过！")
        else:
            print("❌ API测试失败，请检查服务器状态")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 检查是否在交互模式下运行
    if len(sys.argv) == 1:
        print_banner()
        print_test_options()
        print("\n💡 提示: 使用 'python tests/run_api_tests.py quick' 运行快速测试")
        print("💡 提示: 使用 'python tests/run_api_tests.py --help' 查看所有选项")
        print("\n🚀 默认运行快速测试...")
        sys.argv.append("quick")
    
    asyncio.run(main()) 