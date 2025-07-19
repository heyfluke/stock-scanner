#!/usr/bin/env python3
"""
快速API测试脚本 - 专门验证A股分析修复效果
"""

import asyncio
import aiohttp
import json
import sys
import time
import os
from typing import Dict

def check_api_key_availability() -> bool:
    """检查是否有可用的API key"""
    # 检查环境变量
    api_key = os.getenv('API_KEY', '')
    if api_key and api_key.startswith('sk-'):
        print("✓ 检测到环境变量中的有效API key")
        return True
    
    # 检查.env文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('API_KEY', '')
        if api_key and api_key.startswith('sk-'):
            print("✓ 检测到.env文件中的有效API key")
            return True
    except ImportError:
        pass
    
    print("⚠️ 未检测到有效的API key，将跳过AI分析部分")
    return False

def get_test_api_config(has_valid_api_key: bool) -> Dict:
    """获取测试用的API配置"""
    if has_valid_api_key:
        # 如果环境中有有效API key，不传递api_key，让服务器使用环境变量
        return {
            'analysis_days': 30
        }
    else:
        # 如果没有有效API key，传递测试配置但期望会失败
        return {
            'analysis_days': 30,
            'api_url': 'https://api.openai.com/v1/',
            'api_key': 'test-key-will-fail',
            'api_model': 'gpt-4o',
            'api_timeout': '60'
        }

async def test_a_stock_analysis(base_url: str = "http://localhost:8888", stock_code: str = "688385", username: str = "demo", password: str = "demo"):
    """快速测试A股分析功能"""
    
    print(f"🚀 快速测试A股分析: {stock_code}")
    print("=" * 50)
    
    # 检查API key状态
    has_valid_api_key = check_api_key_availability()
    
    timeout = aiohttp.ClientTimeout(total=120)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # 1. 测试服务器连接
        print("1. 检查服务器连接...")
        try:
            url = f"{base_url}/api/config"
            async with session.get(url) as response:
                if response.status == 200:
                    print("✓ 服务器连接正常")
                else:
                    print(f"✗ 服务器响应异常: {response.status}")
                    return False
        except Exception as e:
            print(f"✗ 服务器连接失败: {e}")
            return False
        
        # 2. 用户登录
        print(f"\n2. 用户登录: {username}...")
        auth_token = None
        try:
            url = f"{base_url}/api/login"
            data = {
                "username": username,
                "password": password
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    auth_token = result.get('access_token')
                    if auth_token:
                        print("✓ 登录成功")
                    else:
                        print("✗ 登录响应中没有access_token")
                        return False
                else:
                    error_text = await response.text()
                    print(f"✗ 登录失败: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"✗ 登录过程中发生错误: {e}")
            return False
        
        # 准备认证头
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # 获取API配置
        api_config = get_test_api_config(has_valid_api_key)
        
        # 3. 测试A股分析（非流式）
        print(f"\n3. 测试A股分析: {stock_code}...")
        try:
            start_time = time.time()
            
            url = f"{base_url}/api/analyze"
            data = {
                'stock_codes': [stock_code],
                'market_type': 'A',
            }
            data.update(api_config)
            
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    print("✗ 认证失败，请检查用户名密码")
                    return False
                elif response.status != 200:
                    error_text = await response.text()
                    print(f"✗ 请求失败: {response.status}")
                    print(f"错误内容: {error_text}")
                    return False
                
                content = await response.text()
                
                # 解析结果
                results = []
                for line in content.strip().split('\n'):
                    if line.strip():
                        try:
                            result = json.loads(line)
                            results.append(result)
                        except json.JSONDecodeError:
                            print(f"警告: 无法解析JSON行: {line}")
                
                if not results:
                    print("✗ 未收到有效分析结果")
                    return False
                
                # 查找基本分析结果（包含完整字段的结果）
                basic_result = None
                for result in results:
                    if ('stock_code' in result and 'score' in result and 
                        'price' in result and 'recommendation' in result):
                        basic_result = result
                        break
                
                if not basic_result:
                    # 如果没找到完整的基本分析结果，检查是否有错误
                    for result in results:
                        if 'error' in result:
                            basic_result = result
                            break
                    
                    if not basic_result:
                        print("✗ 未找到基本分析结果")
                        print(f"收到的结果: {results}")
                        return False
                if 'error' in basic_result:
                    if not has_valid_api_key and "API请求失败" in basic_result['error']:
                        print(f"⚠️ AI分析失败（预期，因为没有有效API key）: {basic_result['error']}")
                        # 即使AI失败，只要基础分析成功就算通过
                        if 'stock_code' in basic_result and 'score' in basic_result:
                            print("✓ A股基础分析成功（AI部分跳过）!")
                            print(f"  股票代码: {basic_result.get('stock_code', 'N/A')}")
                            print(f"  评分: {basic_result.get('score', 'N/A')}")
                            print(f"  价格: {basic_result.get('price', 'N/A')}")
                            print(f"  建议: {basic_result.get('recommendation', 'N/A')}")
                            end_time = time.time()
                            response_time = end_time - start_time
                            print(f"  响应时间: {response_time:.2f}秒")
                            return True
                    print(f"✗ 分析出错: {basic_result['error']}")
                    return False
                
                end_time = time.time()
                response_time = end_time - start_time
                
                print("✓ A股分析成功!")
                print(f"  股票代码: {basic_result.get('stock_code', 'N/A')}")
                print(f"  评分: {basic_result.get('score', 'N/A')}")
                print(f"  价格: {basic_result.get('price', 'N/A')}")
                print(f"  建议: {basic_result.get('recommendation', 'N/A')}")
                print(f"  响应时间: {response_time:.2f}秒")
                
                # 检查AI分析结果
                if len(results) > 1:
                    ai_chunks = [r for r in results if 'ai_analysis_chunk' in r or r.get('status') == 'completed']
                    if ai_chunks:
                        print(f"✓ AI分析完成，收到 {len(ai_chunks)} 个分析片段")
                    elif has_valid_api_key:
                        print("⚠️ AI分析可能未完成")
                    else:
                        print("ℹ️ AI分析跳过（无有效API key）")
                
                return True
                
        except Exception as e:
            print(f"✗ A股分析测试失败: {e}")
            return False
        
        # 4. 测试流式分析
        print(f"\n4. 测试A股流式分析: {stock_code}...")
        try:
            url = f"{base_url}/api/analyze"
            data = {
                'stock_codes': [stock_code],
                'market_type': 'A',
            }
            data.update(api_config)
            
            chunks_received = 0
            analysis_completed = False
            basic_analysis_received = False
            start_time = time.time()
            
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    print("✗ 认证失败，请检查用户名密码")
                    return False
                elif response.status != 200:
                    print(f"✗ 流式请求失败: {response.status}")
                    return False
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            try:
                                result = json.loads(line_str)
                                chunks_received += 1
                                
                                # 检查基础分析结果
                                if 'stock_code' in result and 'score' in result:
                                    basic_analysis_received = True
                                
                                if result.get('status') == 'completed':
                                    analysis_completed = True
                                    break
                                elif 'error' in result:
                                    if not has_valid_api_key and "API请求失败" in result['error']:
                                        print(f"⚠️ AI分析失败（预期）: {result['error']}")
                                        # 如果有基础分析就算成功
                                        if basic_analysis_received:
                                            analysis_completed = True
                                            break
                                    print(f"✗ 流式分析出错: {result['error']}")
                                    return False
                                    
                            except json.JSONDecodeError:
                                continue
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if analysis_completed or (basic_analysis_received and chunks_received > 0):
                print("✓ 流式分析成功!")
                print(f"  收到数据块: {chunks_received}")
                print(f"  响应时间: {response_time:.2f}秒")
                if not has_valid_api_key:
                    print("  注意: 基础分析完成，AI部分跳过（无有效API key）")
                return True
            else:
                print("✗ 流式分析未正常完成")
                return False
                
        except Exception as e:
            print(f"✗ 流式分析测试失败: {e}")
            return False

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="快速A股API测试")
    parser.add_argument(
        "--url",
        default="http://localhost:8888",
        help="API服务器地址"
    )
    parser.add_argument(
        "--code",
        default="688385",
        help="A股代码"
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
    
    args = parser.parse_args()
    
    print(f"测试服务器: {args.url}")
    print(f"测试股票: {args.code}")
    print(f"登录账号: {args.username}")
    print()
    
    success = await test_a_stock_analysis(args.url, args.code, args.username, args.password)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 A股分析测试通过！修复成功！")
        print("\n💡 说明:")
        print("- 基础分析（技术指标、评分、建议）功能正常")
        print("- 如需测试完整AI分析，请设置有效的API_KEY环境变量")
    else:
        print("❌ A股分析测试失败，需要进一步检查")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 