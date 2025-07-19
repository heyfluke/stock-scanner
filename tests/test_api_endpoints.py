import asyncio
import aiohttp
import json
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

# 获取日志器
logger = get_logger()

class TestAPIEndpoints:
    """API端点测试类 - 通过HTTP接口测试股票分析功能"""
    
    def __init__(self, base_url: str = "http://localhost:8888", username: str = "demo", password: str = "demo"):
        """初始化测试配置"""
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = None
        self.auth_token = None
        
        # 检查是否有有效的API key
        self.has_valid_api_key = self._check_api_key_availability()
        
        # 测试股票配置
        self.test_stocks = {
            'US': {'code': 'TSLA', 'name': '特斯拉'},
            'HK': {'code': '01810', 'name': '小米集团'},
            'A': {'code': '688385', 'name': '复旦微电'}
        }
        
        # API端点配置
        self.endpoints = {
            'health': '/api/config',
            'login': '/api/login',
            'analyze': '/api/analyze',
            'scan': '/api/scan',
            'search_us': '/api/search/us',
            'search_fund': '/api/search/fund'
        }
    
    def _check_api_key_availability(self) -> bool:
        """检查是否有可用的API key"""
        # 检查环境变量
        api_key = os.getenv('API_KEY', '')
        if api_key and api_key.startswith('sk-'):
            logger.info("检测到环境变量中的有效API key，将进行完整测试")
            return True
        
        # 检查.env文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('API_KEY', '')
            if api_key and api_key.startswith('sk-'):
                logger.info("检测到.env文件中的有效API key，将进行完整测试")
                return True
        except ImportError:
            pass
        
        logger.warning("未检测到有效的API key，将跳过AI分析部分")
        return False
    
    def _get_test_api_config(self) -> Dict[str, Any]:
        """获取测试用的API配置"""
        if self.has_valid_api_key:
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
    
    async def setup_session(self):
        """设置HTTP会话"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=120)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def cleanup_session(self):
        """清理HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def login(self) -> bool:
        """用户登录获取认证Token"""
        try:
            logger.info(f"尝试登录: {self.username}")
            
            url = f"{self.base_url}{self.endpoints['login']}"
            data = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get('access_token')
                    if self.auth_token:
                        logger.info("✓ 登录成功")
                        return True
                    else:
                        logger.error("登录响应中没有access_token")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"登录失败: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"登录过程中发生错误: {str(e)}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def test_server_health(self) -> bool:
        """测试服务器健康状态"""
        try:
            logger.info("测试服务器健康状态...")
            
            url = f"{self.base_url}{self.endpoints['health']}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✓ 服务器正常运行")
                    logger.debug(f"配置信息: {data}")
                    return True
                else:
                    logger.error(f"服务器响应异常: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"服务器连接失败: {str(e)}")
            return False
    
    async def test_stock_analysis(self, market_type: str, stock_code: str) -> bool:
        """测试股票分析接口"""
        try:
            logger.info(f"测试股票分析: {market_type} {stock_code}")
            
            url = f"{self.base_url}{self.endpoints['analyze']}"
            headers = self.get_auth_headers()
            
            # 构建请求数据
            data = {
                'stock_codes': [stock_code],
                'market_type': market_type,
            }
            
            # 添加API配置
            api_config = self._get_test_api_config()
            data.update(api_config)
            
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    error_text = await response.text()
                    logger.error(f"分析请求失败: {response.status}")
                    logger.error(f"错误内容: {error_text}")
                    return False
                
                # 读取响应内容
                content = await response.text()
                
                # 解析JSON响应（可能是多行JSON）
                results = []
                for line in content.strip().split('\n'):
                    if line.strip():
                        try:
                            result = json.loads(line)
                            results.append(result)
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析JSON行: {line}")
                
                if not results:
                    logger.error("分析未返回有效结果")
                    return False
                
                # 查找基本分析结果（包含stock_code, score, price, recommendation的完整结果）
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
                        logger.error("未找到基本分析结果")
                        logger.debug(f"收到的结果: {results}")
                        return False
                if 'error' in basic_result:
                    if not self.has_valid_api_key and "API请求失败" in basic_result['error']:
                        logger.warning(f"AI分析失败（预期，因为没有有效API key）: {basic_result['error']}")
                        # 即使AI失败，只要基础分析成功就算通过
                        if 'stock_code' in basic_result and 'score' in basic_result:
                            logger.info(f"✓ {market_type} {stock_code} 基础分析成功（AI部分跳过）")
                            return True
                    logger.error(f"分析出错: {basic_result['error']}")
                    return False
                
                # 验证必要字段（这里应该不会失败，因为我们已经按这些字段筛选了）
                required_fields = ['stock_code', 'score', 'price', 'recommendation']
                missing_fields = [field for field in required_fields if field not in basic_result]
                
                if missing_fields:
                    logger.error(f"分析结果缺少字段: {missing_fields}")
                    logger.debug(f"基本分析结果: {basic_result}")
                    return False
                
                logger.info(f"✓ {market_type} {stock_code} 分析成功")
                logger.info(f"  评分: {basic_result.get('score', 'N/A')}")
                logger.info(f"  价格: {basic_result.get('price', 'N/A')}")
                logger.info(f"  建议: {basic_result.get('recommendation', 'N/A')}")
                
                # 检查是否有AI分析结果
                ai_chunks = [r for r in results if 'ai_analysis_chunk' in r or 'status' in r]
                if ai_chunks:
                    logger.info(f"  AI分析: 收到 {len(ai_chunks)} 个分析片段")
                elif self.has_valid_api_key:
                    logger.warning("  AI分析: 未收到AI分析内容（可能API配置有问题）")
                else:
                    logger.info("  AI分析: 跳过（无有效API key）")
                
                return True
                
        except Exception as e:
            logger.error(f"测试股票分析失败 {market_type} {stock_code}: {str(e)}")
            return False
    
    async def test_stock_analysis_stream(self, market_type: str, stock_code: str) -> bool:
        """测试流式股票分析接口"""
        try:
            logger.info(f"测试流式股票分析: {market_type} {stock_code}")
            
            url = f"{self.base_url}{self.endpoints['analyze']}"
            headers = self.get_auth_headers()
            
            # 构建请求数据
            data = {
                'stock_codes': [stock_code],
                'market_type': market_type,
            }
            
            # 添加API配置
            api_config = self._get_test_api_config()
            data.update(api_config)
            
            chunks_received = 0
            analysis_completed = False
            basic_analysis_received = False
            
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    logger.error(f"流式分析请求失败: {response.status}")
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
                                    logger.debug(f"收到基础分析结果: 评分{result.get('score')}")
                                
                                # 检查分析状态
                                if result.get('status') == 'completed':
                                    analysis_completed = True
                                    logger.info(f"流式分析完成，收到 {chunks_received} 个数据块")
                                    break
                                elif 'error' in result:
                                    if not self.has_valid_api_key and "API请求失败" in result['error']:
                                        logger.warning(f"AI分析失败（预期）: {result['error']}")
                                        # 如果有基础分析就算成功
                                        if basic_analysis_received:
                                            analysis_completed = True
                                            break
                                    logger.error(f"流式分析出错: {result['error']}")
                                    return False
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析流式JSON: {line_str}")
            
            # 判断是否成功
            if analysis_completed or (basic_analysis_received and chunks_received > 0):
                logger.info(f"✓ {market_type} {stock_code} 流式分析成功")
                if self.has_valid_api_key:
                    logger.info(f"  数据块: {chunks_received}, 完成状态: {analysis_completed}")
                else:
                    logger.info(f"  基础分析完成，AI部分跳过（无有效API key）")
                return True
            else:
                logger.error("流式分析未正常完成")
                return False
                
        except Exception as e:
            logger.error(f"测试流式股票分析失败 {market_type} {stock_code}: {str(e)}")
            return False
    
    async def test_stock_scan(self, market_type: str, codes: List[str]) -> bool:
        """测试股票扫描接口"""
        try:
            logger.info(f"测试股票扫描: {market_type} {codes}")
            
            url = f"{self.base_url}{self.endpoints['scan']}"
            headers = self.get_auth_headers()
            data = {
                'codes': codes,
                'market_type': market_type,
                'min_score': 0,
                'stream': False
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    logger.error(f"扫描请求失败: {response.status}")
                    return False
                
                content = await response.text()
                
                # 解析扫描结果
                results = []
                for line in content.strip().split('\n'):
                    if line.strip():
                        try:
                            result = json.loads(line)
                            results.append(result)
                        except json.JSONDecodeError:
                            continue
                
                if not results:
                    logger.error("扫描未返回有效结果")
                    return False
                
                # 检查扫描结果
                success_count = 0
                for result in results:
                    if 'error' not in result and 'stock_code' in result:
                        success_count += 1
                
                logger.info(f"✓ {market_type} 扫描成功: {success_count}/{len(codes)} 股票")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"测试股票扫描失败 {market_type}: {str(e)}")
            return False
    
    async def test_us_stock_search(self, keyword: str = "TSLA") -> bool:
        """测试美股搜索接口"""
        try:
            logger.info(f"测试美股搜索: {keyword}")
            
            url = f"{self.base_url}{self.endpoints['search_us']}"
            headers = self.get_auth_headers()
            params = {'keyword': keyword}
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    logger.error(f"美股搜索请求失败: {response.status}")
                    return False
                
                data = await response.json()
                
                if 'error' in data:
                    logger.error(f"美股搜索出错: {data['error']}")
                    return False
                
                results = data.get('results', [])
                if not results:
                    logger.warning("美股搜索未返回结果")
                    return False
                
                logger.info(f"✓ 美股搜索成功: 找到 {len(results)} 个结果")
                for result in results[:3]:  # 显示前3个结果
                    logger.info(f"  {result.get('symbol', 'N/A')}: {result.get('name', 'N/A')}")
                
                return True
                
        except Exception as e:
            logger.error(f"测试美股搜索失败: {str(e)}")
            return False
    
    async def test_fund_search(self, keyword: str = "科技", market_type: str = "ETF") -> bool:
        """测试基金搜索接口"""
        try:
            logger.info(f"测试基金搜索: {keyword} ({market_type})")
            
            url = f"{self.base_url}{self.endpoints['search_fund']}"
            headers = self.get_auth_headers()
            params = {
                'keyword': keyword,
                'market_type': market_type
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    logger.error(f"基金搜索请求失败: {response.status}")
                    return False
                
                data = await response.json()
                
                if 'error' in data:
                    logger.error(f"基金搜索出错: {data['error']}")
                    return False
                
                results = data.get('results', [])
                if not results:
                    logger.warning("基金搜索未返回结果")
                    return False
                
                logger.info(f"✓ 基金搜索成功: 找到 {len(results)} 个结果")
                for result in results[:3]:  # 显示前3个结果
                    logger.info(f"  {result.get('symbol', 'N/A')}: {result.get('name', 'N/A')}")
                
                return True
                
        except Exception as e:
            logger.error(f"测试基金搜索失败: {str(e)}")
            return False
    
    async def test_api_performance(self, market_type: str, stock_code: str) -> bool:
        """测试API性能"""
        try:
            logger.info(f"测试API性能: {market_type} {stock_code}")
            
            start_time = time.time()
            
            url = f"{self.base_url}{self.endpoints['analyze']}"
            headers = self.get_auth_headers()
            
            # 构建请求数据
            data = {
                'stock_codes': [stock_code],
                'market_type': market_type,
            }
            
            # 添加API配置
            api_config = self._get_test_api_config()
            data.update(api_config)
            
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 401:
                    logger.error("认证失败，请检查登录状态")
                    return False
                elif response.status != 200:
                    logger.error("性能测试请求失败")
                    return False
                
                await response.text()
                
            end_time = time.time()
            response_time = end_time - start_time
            
            logger.info(f"✓ API响应时间: {response_time:.2f}秒")
            
            # 性能标准：60秒内完成
            if response_time > 60:
                logger.warning(f"响应时间较慢: {response_time:.2f}秒")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"测试API性能失败: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """运行所有API测试"""
        logger.info("=" * 60)
        logger.info("开始API端点测试")
        logger.info("=" * 60)
        
        # 显示API key状态
        if self.has_valid_api_key:
            logger.info("🔑 API Key状态: 有效 - 将进行完整测试包括AI分析")
        else:
            logger.info("🔑 API Key状态: 无效/缺失 - 将跳过AI分析部分")
        
        await self.setup_session()
        
        try:
            test_results = {}
            
            # 1. 测试服务器健康状态
            logger.info("\n🔍 测试服务器状态")
            logger.info("-" * 30)
            test_results['server_health'] = await self.test_server_health()
            
            if not test_results['server_health']:
                logger.error("❌ 服务器连接失败，跳过其他测试")
                return test_results
            
            # 2. 用户登录
            logger.info("\n🔐 用户登录")
            logger.info("-" * 30)
            test_results['login'] = await self.login()
            
            if not test_results['login']:
                logger.error("❌ 用户登录失败，无法进行需要认证的测试")
                return test_results
            
            # 3. 测试股票分析接口
            logger.info("\n📈 测试股票分析接口")
            logger.info("-" * 30)
            
            analysis_results = {}
            for market_type, stock_info in self.test_stocks.items():
                stock_code = stock_info['code']
                stock_name = stock_info['name']
                
                logger.info(f"\n测试 {market_type} 市场: {stock_code} ({stock_name})")
                
                # 非流式分析
                analysis_results[f'{market_type}_analysis'] = await self.test_stock_analysis(market_type, stock_code)
                
                # 流式分析
                analysis_results[f'{market_type}_stream'] = await self.test_stock_analysis_stream(market_type, stock_code)
                
                # 性能测试
                analysis_results[f'{market_type}_performance'] = await self.test_api_performance(market_type, stock_code)
            
            test_results.update(analysis_results)
            
            # 4. 测试扫描接口
            logger.info("\n🔍 测试股票扫描接口")
            logger.info("-" * 30)
            
            # 测试A股扫描
            test_results['a_scan'] = await self.test_stock_scan('A', ['688385', '000001'])
            
            # 5. 测试搜索接口
            logger.info("\n🔎 测试搜索接口")
            logger.info("-" * 30)
            
            test_results['us_search'] = await self.test_us_stock_search('TSLA')
            test_results['fund_search'] = await self.test_fund_search('科技', 'ETF')
            
            # 输出测试结果
            logger.info("\n" + "=" * 60)
            logger.info("API测试结果汇总")
            logger.info("=" * 60)
            
            total_tests = len(test_results)
            passed_tests = sum(test_results.values())
            
            for test_name, result in test_results.items():
                status = "✓ 通过" if result else "✗ 失败"
                logger.info(f"{test_name}: {status}")
            
            logger.info(f"\n总计: {passed_tests}/{total_tests} 测试通过")
            
            if passed_tests == total_tests:
                logger.info("🎉 所有API测试通过！")
            else:
                logger.warning("⚠️  部分API测试失败，请检查相关功能")
            
            # 显示API key建议
            if not self.has_valid_api_key:
                logger.info("\n💡 提示: 设置有效的API_KEY环境变量可以测试完整的AI分析功能")
            
            return test_results
            
        finally:
            await self.cleanup_session()

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API端点测试")
    parser.add_argument(
        "--url",
        default="http://localhost:8888",
        help="API服务器地址 (默认: http://localhost:8888)"
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
    
    # 设置日志级别
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
    
    # 运行测试
    test_suite = TestAPIEndpoints(args.url, args.username, args.password)
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 