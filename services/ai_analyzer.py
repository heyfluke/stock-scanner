import pandas as pd
import os
import json
import httpx
import re
from typing import AsyncGenerator, List, Dict, Any, Optional
from dotenv import load_dotenv
from utils.logger import get_logger
from utils.api_utils import APIUtils
from datetime import datetime

# 获取日志器
logger = get_logger()

class AIAnalyzer:
    """
    异步AI分析服务
    负责调用AI API对股票数据进行分析
    """
    
    def __init__(self, custom_api_url=None, custom_api_key=None, custom_api_model=None, custom_api_timeout=None):
        """
        初始化AI分析服务
        
        Args:
            custom_api_url: 自定义API URL
            custom_api_key: 自定义API密钥
            custom_api_model: 自定义API模型
            custom_api_timeout: 自定义API超时时间
        """
        # 加载环境变量
        load_dotenv()
        
        # 设置API配置，处理空字符串环境变量
        self.API_URL = (custom_api_url if custom_api_url and custom_api_url.strip() else None) or \
                      (os.getenv('API_URL') if os.getenv('API_URL') and os.getenv('API_URL').strip() else None) or \
                      'https://api.openai.com/v1/chat/completions'
        
        self.API_KEY = (custom_api_key if custom_api_key and custom_api_key.strip() else None) or \
                      (os.getenv('API_KEY') if os.getenv('API_KEY') and os.getenv('API_KEY').strip() else '') or \
                      ''
        
        self.API_MODEL = (custom_api_model if custom_api_model and custom_api_model.strip() else None) or \
                        (os.getenv('API_MODEL') if os.getenv('API_MODEL') and os.getenv('API_MODEL').strip() else None) or \
                        'gpt-4o'
        
        # 处理API超时参数，确保空字符串也能正确处理
        timeout_str = None
        if custom_api_timeout and custom_api_timeout.strip():
            timeout_str = custom_api_timeout.strip()
        elif os.getenv('API_TIMEOUT') and os.getenv('API_TIMEOUT').strip():
            timeout_str = os.getenv('API_TIMEOUT').strip()
        else:
            timeout_str = '60'
        
        try:
            self.API_TIMEOUT = int(timeout_str)
            if self.API_TIMEOUT <= 0:
                raise ValueError("超时时间必须大于0")
        except (ValueError, TypeError) as e:
            logger.warning(f"无效的API超时值: {timeout_str}，错误: {e}，使用默认值60秒")
            self.API_TIMEOUT = 60
        
        logger.info(f"AIAnalyzer初始化完成: URL={self.API_URL}, MODEL={self.API_MODEL}, TIMEOUT={self.API_TIMEOUT}")
        
        # 预设对话提示词
        self.conversation_prompts = [
            "请详细解释一下这个分析结果中的技术指标含义",
            "基于当前分析，您认为这只股票的风险点在哪里？",
            "能否分析一下这只股票的支撑位和压力位？",
            "从技术面来看，这只股票适合什么类型的投资者？",
            "请分析一下成交量变化对股价的影响",
            "基于RSI指标，当前是否适合买入或卖出？",
            "能否预测一下这只股票的短期走势？",
            "请解释一下MACD指标在当前分析中的作用",
            "从风险收益比来看，这只股票值得投资吗？",
            "能否分析一下这只股票与同行业其他股票的对比？",
            "请详细说明一下止损位的设置逻辑",
            "基于当前技术指标，您建议的仓位管理策略是什么？",
            "能否分析一下这只股票在不同市场环境下的表现？",
            "请解释一下布林带指标在当前分析中的意义",
            "基于技术分析，您认为这只股票的中长期投资价值如何？"
        ]
    
    def get_random_conversation_prompt(self) -> str:
        """获取随机的对话提示词"""
        import random
        return random.choice(self.conversation_prompts)

    async def get_completion(self, prompt: str, stream: bool = False):
        """
        使用当前模型与密钥执行补全。
        
        Args:
            prompt: 提示词
            stream: 是否流式输出。如果为True，返回异步生成器；如果为False，返回字符串
        
        Returns:
            str (当stream=False) 或 AsyncGenerator[str, None] (当stream=True)
        """
        api_url = APIUtils.format_api_url(self.API_URL)
        if not self.API_KEY or self.API_KEY.strip() == "":
            raise RuntimeError("API_KEY未配置或为空")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY.strip()}"
        }
        request_data = {
            "model": self.API_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": stream
        }
        
        if not stream:
            # 非流式：一次性返回完整文本
            async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
                response = await client.post(api_url, json=request_data, headers=headers)
                if response.status_code != 200:
                    try:
                        data = response.json()
                        msg = data.get('error', {}).get('message', str(data))
                    except Exception:
                        msg = response.text
                    raise RuntimeError(f"API请求失败: {response.status_code} - {msg}")
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    logger.error(f"API响应中没有choices: {data}")
                    raise RuntimeError(f"API返回了空的响应")
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    logger.error(f"API响应中没有内容: {data}")
                    raise RuntimeError(f"API返回了空的分析内容")
                return content
        else:
            # 流式：返回异步生成器
            return self._stream_completion(api_url, request_data, headers)
    
    async def _stream_completion(self, api_url: str, request_data: dict, headers: dict):
        """
        流式补全的内部实现
        Yields: (content_chunk, usage_info) 元组
        """
        async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
            async with client.stream('POST', api_url, json=request_data, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    try:
                        data = response.json()
                        msg = data.get('error', {}).get('message', str(data))
                    except Exception:
                        msg = error_text.decode('utf-8')
                    raise RuntimeError(f"API请求失败: {response.status_code} - {msg}")
                
                usage_info = None
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # 处理 SSE 格式：data: {...}
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    # 跳过 [DONE] 标记
                    if line.strip() == '[DONE]':
                        break
                    
                    try:
                        chunk_data = json.loads(line)
                        delta = chunk_data.get('choices', [{}])[0].get('delta', {})
                        content = delta.get('content', '')
                        
                        # 提取usage信息（通常在最后一个chunk中）
                        if 'usage' in chunk_data:
                            usage_info = chunk_data['usage']
                        
                        if content:
                            yield (content, usage_info)
                    except json.JSONDecodeError:
                        # 忽略无法解析的行
                        continue
                
                # 如果有usage信息但最后没有内容，单独yield一次
                if usage_info:
                    yield ('', usage_info)
    
    async def get_ai_analysis(self, df: pd.DataFrame, stock_code: str, market_type: str = 'A', stream: bool = False, analysis_days: int = 30, portfolio_context: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        对股票数据进行AI分析
        
        Args:
            df: 包含技术指标的DataFrame
            stock_code: 股票代码
            market_type: 市场类型，默认为'A'股
            stream: 是否使用流式响应
            analysis_days: AI分析使用的天数，默认30天
            portfolio_context: 用户持仓信息（可选），将添加到分析提示词中
            
        Returns:
            异步生成器，生成分析结果字符串
        """
        try:
            logger.info(f"开始AI分析 {stock_code}, 流式模式: {stream}")
            
            # 提取关键技术指标
            latest_data = df.iloc[-1]
            
            # 计算技术指标
            rsi = latest_data.get('RSI')
            price = latest_data.get('Close')
            price_change = latest_data.get('Change')
            
            # 确定MA趋势
            ma_trend = 'UP' if latest_data.get('MA5', 0) > latest_data.get('MA20', 0) else 'DOWN'
            
            # 确定MACD信号
            macd = latest_data.get('MACD', 0)
            macd_signal = latest_data.get('MACD_Signal', 0)
            macd_signal_type = 'BUY' if macd > macd_signal else 'SELL'
            
            # 确定成交量状态
            volume_ratio = latest_data.get('Volume_Ratio', 1)
            volume_status = 'HIGH' if volume_ratio > 1.5 else ('LOW' if volume_ratio < 0.5 else 'NORMAL')
            
            # AI 分析内容
            # 获取指定天数的股票数据记录
            recent_df = df.tail(analysis_days).copy()
            recent_df.reset_index(inplace=True)
            # 统一把第一个列名（原index）重命名为 'date'
            recent_df.rename(columns={recent_df.columns[0]: 'date'}, inplace=True)
            # 确保 'date' 列为字符串格式
            if pd.api.types.is_datetime64_any_dtype(recent_df['date']):
                recent_df['date'] = recent_df['date'].dt.strftime('%Y-%m-%d')
            else:
                try:
                    recent_df['date'] = pd.to_datetime(recent_df['date']).dt.strftime('%Y-%m-%d')
                except Exception:
                    recent_df['date'] = recent_df['date'].astype(str)
            
            recent_data = recent_df.to_dict('records')
            logger.debug(f"recent_data for chart: {recent_data}")
            
            # 包含trend, volatility, volume_trend, rsi_level的字典
            technical_summary = {
                'trend': 'upward' if df.iloc[-1]['MA5'] > df.iloc[-1]['MA20'] else 'downward',
                'volatility': f"{df.iloc[-1]['Volatility']:.2f}%",
                'volume_trend': 'increasing' if df.iloc[-1]['Volume_Ratio'] > 1 else 'decreasing',
                'rsi_level': df.iloc[-1]['RSI']
            }
            
            # 根据市场类型调整分析提示
            if market_type in ['ETF', 'LOF']:
                prompt = f"""
                分析基金 {stock_code}：

                技术指标概要：
                {technical_summary}
                
                近{analysis_days}日交易数据：
                {recent_data}
                
                请提供：
                1. 净值走势分析（包含支撑位和压力位）
                2. 成交量分析及其对净值的影响
                3. 风险评估（包含波动率和折溢价分析）
                4. 短期和中期净值预测
                5. 关键价格位分析
                6. 申购赎回建议（包含止损位）
                
                请基于技术指标和市场表现进行分析，给出具体数据支持。
                """
            elif market_type == 'US':
                prompt = f"""
                分析美股 {stock_code}：

                技术指标概要：
                {technical_summary}
                
                近{analysis_days}日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位，美元计价）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率和美股市场特有风险）
                4. 短期和中期目标价位（美元）
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和美股市场特点进行分析，给出具体数据支持。
                """
            elif market_type == 'HK':
                prompt = f"""
                分析港股 {stock_code}：

                技术指标概要：
                {technical_summary}
                
                近{analysis_days}日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位，港币计价）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率和港股市场特有风险）
                4. 短期和中期目标价位（港币）
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和港股市场特点进行分析，给出具体数据支持。
                """
            else:  # A股
                prompt = f"""
                分析A股 {stock_code}：

                技术指标概要：
                {technical_summary}
                
                近{analysis_days}日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率分析）
                4. 短期和中期目标价位
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和A股市场特点进行分析，给出具体数据支持。
                """
            
            if portfolio_context:
                logger.info(f"Add portfolio (len: {len(portfolio_context)})")
                prompt += f"\n\n{'='*50}\n📊 我的持仓情况\n{'='*50}\n{portfolio_context}"
            else:
                logger.debug(f"portfolio_context not provided")
            
            # 格式化API URL
            api_url = APIUtils.format_api_url(self.API_URL)
            
            # 准备请求数据
            request_data = {
                "model": self.API_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "stream": stream
            }
            
            # 检查API_KEY是否为空
            if not self.API_KEY or self.API_KEY.strip() == "":
                logger.error("API_KEY为空，无法进行股票分析")
                yield json.dumps({
                    "stock_code": stock_code,
                    "error": "API_KEY未配置或为空，请检查API配置",
                    "status": "error"
                }, ensure_ascii=False)
                return
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY.strip()}"
            }
            
            # 获取当前日期作为分析日期
            analysis_date = datetime.now().strftime("%Y-%m-%d")
            
            # 异步请求API
            async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
                # 记录请求
                logger.debug(f"发送AI请求: URL={api_url}, MODEL={self.API_MODEL}, STREAM={stream}")
                logger.debug(f"完整的AI请求Prompt for {stock_code}:\n{prompt}")
                
                # 先发送技术指标数据
                yield json.dumps({
                    "stock_code": stock_code,
                    "status": "analyzing",
                    "chart_data": recent_data
                }, ensure_ascii=False)
                
                if stream:
                    # 流式响应处理
                    async with client.stream("POST", api_url, json=request_data, headers=headers) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            error_data = json.loads(error_text)
                            error_message = error_data.get('error', {}).get('message', '未知错误')
                            logger.error(f"AI API请求失败: {response.status_code} - {error_message}")
                            yield json.dumps({
                                "stock_code": stock_code,
                                "error": f"API请求失败: {error_message}",
                                "status": "error"
                            })
                            return
                            
                        # 处理流式响应
                        buffer = ""
                        collected_messages = []
                        chunk_count = 0
                        usage_info = None  # 收集usage信息
                        
                        async for chunk in response.aiter_text():
                            if chunk:
                                # 分割多行响应（处理某些API可能在一个chunk中返回多行）
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue
                                        
                                    # 处理以data:开头的行
                                    if line.startswith("data: "):
                                        line = line[6:]  # 去除"data: "前缀
                                     
                                    if line == "[DONE]":
                                        logger.debug("收到流结束标记 [DONE]")
                                        continue
                                        
                                    try:
                                        # 处理特殊错误情况
                                        if "error" in line.lower():
                                            error_msg = line
                                            try:
                                                error_data = json.loads(line)
                                                error_msg = error_data.get("error", line)
                                            except:
                                                pass
                                            
                                            logger.error(f"流式响应中收到错误: {error_msg}")
                                            yield json.dumps({
                                                "stock_code": stock_code,
                                                "error": f"流式响应错误: {error_msg}",
                                                "status": "error"
                                            })
                                            continue
                                        
                                        # 尝试解析JSON
                                        chunk_data = json.loads(line)
                                        
                                        # 获取choices数组，确保不为空
                                        choices = chunk_data.get("choices", [])
                                        if not choices:
                                            logger.debug("收到空的choices数组，跳过")
                                            # 即使choices为空，也检查是否有usage信息
                                            if 'usage' in chunk_data:
                                                usage_info = chunk_data['usage']
                                                if usage_info:
                                                    logger.debug(f"收到usage信息: {usage_info}")
                                            continue
                                        
                                        # 检查是否有finish_reason
                                        finish_reason = choices[0].get("finish_reason")
                                        if finish_reason == "stop":
                                            logger.debug("收到finish_reason=stop，流结束")
                                            # 流结束时也检查usage信息
                                            if 'usage' in chunk_data:
                                                usage_info = chunk_data['usage']
                                                if usage_info:
                                                    logger.debug(f"收到usage信息: {usage_info}")
                                            continue
                                        
                                        # 提取usage信息（通常在最后一个chunk中）
                                        if 'usage' in chunk_data:
                                            usage_info = chunk_data['usage']
                                            if usage_info:
                                                logger.debug(f"收到usage信息: {usage_info}")
                                        
                                        # 获取delta内容
                                        delta = choices[0].get("delta", {})
                                        
                                        # 检查delta是否为空对象
                                        if not delta or delta == {}:
                                            logger.debug("收到空的delta对象，跳过")
                                            continue
                                        
                                        content = delta.get("content", "")
                                        
                                        if content:
                                            chunk_count += 1
                                            buffer += content
                                            collected_messages.append(content)
                                            
                                            # 直接发送每个内容片段，不累积
                                            yield json.dumps({
                                                "stock_code": stock_code,
                                                "ai_analysis_chunk": content,
                                                "status": "analyzing"
                                            })
                                    except json.JSONDecodeError:
                                        # 记录解析错误并尝试恢复
                                        logger.error(f"JSON解析错误，块内容: {line}")
                                        
                                        # 如果是特定错误模式，处理它
                                        if "streaming failed after retries" in line.lower():
                                            logger.error("检测到流式传输失败")
                                            yield json.dumps({
                                                "stock_code": stock_code,
                                                "error": "流式传输失败，请稍后重试",
                                                "status": "error"
                                            })
                                            return
                                        continue
                        
                        logger.info(f"AI流式处理完成，共收到 {chunk_count} 个内容片段，总长度: {len(buffer)}")
                        
                        # 如果buffer不为空且不以换行符结束，发送一个换行符
                        if buffer and not buffer.endswith('\n'):
                            logger.debug("发送换行符")
                            yield json.dumps({
                                "stock_code": stock_code,
                                "ai_analysis_chunk": "\n",
                                "status": "analyzing"
                            })
                        
                        # 完整的分析内容
                        full_content = buffer
                        logger.debug(f"full_content: {full_content}")
                        # logger.debug(f"collected_messages: {collected_messages}")
                        
                        # 尝试从分析内容中提取投资建议
                        recommendation = self._extract_recommendation(full_content)
                        
                        # 计算分析评分
                        score = self._calculate_analysis_score(full_content, technical_summary)
                        
                        # 发送完成状态和评分、建议
                        completion_data = {
                            "stock_code": stock_code,
                            "status": "completed",
                            "score": score,
                            "recommendation": recommendation
                        }
                        
                        # 添加token使用信息
                        if usage_info:
                            completion_data["token_usage"] = usage_info
                            logger.info(f"标准分析完成，token使用（精确）: {usage_info}")
                        else:
                            # API不返回usage，使用字符数估算
                            prompt_chars = len(prompt)
                            output_chars = len(buffer)
                            estimated_tokens = (prompt_chars + output_chars) // 3
                            completion_data["token_usage"] = {
                                "estimated": True,
                                "total_tokens": estimated_tokens,
                                "prompt_chars": prompt_chars,
                                "output_chars": output_chars
                            }
                            logger.info(f"标准分析完成，估算token使用: ~{estimated_tokens} (输入{prompt_chars}字符 + 输出{output_chars}字符)")
                        
                        yield json.dumps(completion_data)
                else:
                    # 非流式响应处理
                    response = await client.post(api_url, json=request_data, headers=headers)
                    
                    if response.status_code != 200:
                        error_data = response.json()
                        error_message = error_data.get('error', {}).get('message', '未知错误')
                        logger.error(f"AI API请求失败: {response.status_code} - {error_message}")
                        yield json.dumps({
                            "stock_code": stock_code,
                            "error": f"API请求失败: {error_message}",
                            "status": "error"
                        })
                        return
                    
                    response_data = response.json()
                    
                    # 安全地提取分析内容
                    choices = response_data.get("choices", [])
                    if not choices:
                        logger.error(f"API响应中没有choices: {response_data}")
                        yield json.dumps({
                            "stock_code": stock_code,
                            "error": "API返回了空的响应",
                            "status": "error"
                        })
                        return
                    
                    analysis_text = choices[0].get("message", {}).get("content", "")
                    if not analysis_text:
                        logger.error(f"API响应中没有内容: {response_data}")
                        yield json.dumps({
                            "stock_code": stock_code,
                            "error": "API返回了空的分析内容",
                            "status": "error"
                        })
                        return
                    
                    # 提取usage信息
                    usage_info = response_data.get('usage')
                    
                    # 尝试从分析内容中提取投资建议
                    recommendation = self._extract_recommendation(analysis_text)
                    
                    # 计算分析评分
                    score = self._calculate_analysis_score(analysis_text, technical_summary)
                    
                    # 发送完整的分析结果
                    completion_data = {
                        "stock_code": stock_code,
                        "status": "completed",
                        "analysis": analysis_text,
                        "score": score,
                        "recommendation": recommendation,
                        "rsi": rsi,
                        "price": price,
                        "price_change": price_change,
                        "ma_trend": ma_trend,
                        "macd_signal": macd_signal_type,
                        "volume_status": volume_status,
                        "analysis_date": analysis_date
                    }
                    
                    # 添加token使用信息
                    if usage_info:
                        completion_data["token_usage"] = usage_info
                        logger.info(f"标准分析完成（非流式），token使用（精确）: {usage_info}")
                    else:
                        # API不返回usage，使用字符数估算
                        prompt_chars = len(prompt)
                        output_chars = len(analysis_text)
                        estimated_tokens = (prompt_chars + output_chars) // 3
                        completion_data["token_usage"] = {
                            "estimated": True,
                            "total_tokens": estimated_tokens,
                            "prompt_chars": prompt_chars,
                            "output_chars": output_chars
                        }
                        logger.info(f"标准分析完成（非流式），估算token使用: ~{estimated_tokens}")
                    
                    yield json.dumps(completion_data)
                    
        except Exception as e:
            logger.error(f"AI分析出错: {str(e)}", exc_info=True)
            yield json.dumps({
                "stock_code": stock_code,
                "error": f"分析出错: {str(e)}",
                "status": "error"
            })
            
    def _extract_recommendation(self, analysis_text: str) -> str:
        """从分析文本中提取投资建议"""
        # 查找投资建议部分
        investment_advice_pattern = r"##\s*投资建议\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(investment_advice_pattern, analysis_text, re.DOTALL)
        
        if match:
            advice_text = match.group(1).strip()
            
            # 提取关键建议
            if "买入" in advice_text or "增持" in advice_text:
                return "买入"
            elif "卖出" in advice_text or "减持" in advice_text:
                return "卖出"
            elif "持有" in advice_text:
                return "持有"
            else:
                return "观望"
        
        return "观望"  # 默认建议
        
    def _calculate_analysis_score(self, analysis_text: str, technical_summary: dict) -> int:
        """计算分析评分"""
        score = 50  # 基础分数
        
        # 根据技术指标调整分数
        if technical_summary['trend'] == 'upward':
            score += 10
        else:
            score -= 10
            
        if technical_summary['volume_trend'] == 'increasing':
            score += 5
        else:
            score -= 5
            
        rsi = technical_summary['rsi_level']
        if rsi < 30:  # 超卖
            score += 15
        elif rsi > 70:  # 超买
            score -= 15
            
        # 根据分析文本中的关键词调整分数
        if "强烈买入" in analysis_text or "显著上涨" in analysis_text:
            score += 20
        elif "买入" in analysis_text or "看涨" in analysis_text:
            score += 10
        elif "强烈卖出" in analysis_text or "显著下跌" in analysis_text:
            score -= 20
        elif "卖出" in analysis_text or "看跌" in analysis_text:
            score -= 10
            
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    def _truncate_json_for_logging(self, json_obj, max_length=500):
        """截断JSON对象用于日志记录"""
        json_str = json.dumps(json_obj, ensure_ascii=False)
        if len(json_str) > max_length:
            return json_str[:max_length] + "..."
        return json_str

    async def get_conversation_response(self, 
                                      conversation_messages: List[Dict[str, str]], 
                                      analysis_context: Dict[str, Any],
                                      user_message: str,
                                      stream: bool = False) -> AsyncGenerator[str, None]:
        """
        处理AI对话回复
        
        Args:
            conversation_messages: 历史对话消息列表
            analysis_context: 原始分析结果上下文
            user_message: 用户当前消息
            stream: 是否使用流式响应
            
        Returns:
            异步生成器，生成AI回复
        """
        try:
            logger.info(f"开始处理对话请求，消息数量: {len(conversation_messages)}")
            
            # 构建系统提示词
            system_prompt = self._build_conversation_system_prompt(analysis_context)
            
            # 构建消息历史
            messages = [{"role": "system", "content": system_prompt}]
            
            # 添加历史对话消息
            for msg in conversation_messages:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 添加用户当前消息
            messages.append({"role": "user", "content": user_message})
            
            # 格式化API URL
            api_url = APIUtils.format_api_url(self.API_URL)
            
            # 准备请求数据
            request_data = {
                "model": self.API_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "stream": stream
            }
            
            # 检查API_KEY是否为空
            if not self.API_KEY or self.API_KEY.strip() == "":
                logger.error("API_KEY为空，无法处理对话请求")
                yield json.dumps({
                    "error": "API_KEY未配置或为空，请检查API配置",
                    "status": "error"
                })
                return
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY.strip()}"
            }
            
            logger.debug(f"发送对话请求: URL={api_url}, MODEL={self.API_MODEL}, STREAM={stream}")
            logger.debug(f"对话消息数量: {len(messages)}")
            
            # 异步请求API
            async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
                if stream:
                    # 流式响应处理
                    async with client.stream("POST", api_url, json=request_data, headers=headers) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            error_data = json.loads(error_text)
                            error_message = error_data.get('error', {}).get('message', '未知错误')
                            logger.error(f"对话API请求失败: {response.status_code} - {error_message}")
                            yield json.dumps({
                                "error": f"API请求失败: {error_message}",
                                "status": "error"
                            })
                            return
                            
                        # 处理流式响应
                        buffer = ""
                        collected_messages = []
                        
                        async for chunk in response.aiter_text():
                            if chunk:
                                # 分割多行响应
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue
                                        
                                    # 处理以data:开头的行
                                    if line.startswith("data: "):
                                        line = line[6:]  # 去除"data: "前缀
                                     
                                    if line == "[DONE]":
                                        logger.debug("收到流结束标记 [DONE]")
                                        continue
                                        
                                    try:
                                        # 处理特殊错误情况
                                        if "error" in line.lower():
                                            error_msg = line
                                            try:
                                                error_data = json.loads(line)
                                                error_msg = error_data.get("error", line)
                                            except:
                                                pass
                                            
                                            logger.error(f"流式响应中收到错误: {error_msg}")
                                            yield json.dumps({
                                                "error": f"流式响应错误: {error_msg}",
                                                "status": "error"
                                            })
                                            continue
                                        
                                        # 尝试解析JSON
                                        chunk_data = json.loads(line)
                                        
                                        # 检查是否有finish_reason
                                        finish_reason = chunk_data.get("choices", [{}])[0].get("finish_reason")
                                        if finish_reason == "stop":
                                            logger.debug("收到finish_reason=stop，流结束")
                                            continue
                                        
                                        # 获取delta内容
                                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                        
                                        if "content" in delta:
                                            content = delta["content"]
                                            if content is not None:  # 确保content不是None
                                                buffer += content
                                                collected_messages.append(content)
                                                
                                                # 流式返回内容
                                                yield json.dumps({
                                                    "content": content,
                                                    "status": "streaming"
                                                })
                                            
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"解析流式响应JSON失败: {e}, 原始数据: {line}")
                                        continue
                                    
                        # 流式响应完成
                        if buffer:
                            logger.info(f"对话流式响应完成，总长度: {len(buffer)}")
                            yield json.dumps({
                                "content": buffer,
                                "status": "completed"
                            })
                else:
                    # 非流式响应处理
                    response = await client.post(api_url, json=request_data, headers=headers)
                    
                    if response.status_code != 200:
                        error_data = response.json()
                        error_message = error_data.get('error', {}).get('message', '未知错误')
                        logger.error(f"对话API请求失败: {response.status_code} - {error_message}")
                        yield json.dumps({
                            "error": f"API请求失败: {error_message}",
                            "status": "error"
                        })
                        return
                    
                    response_data = response.json()
                    
                    # 安全地提取对话内容
                    choices = response_data.get("choices", [])
                    if not choices:
                        logger.error(f"对话API响应中没有choices: {response_data}")
                        yield json.dumps({
                            "error": "API返回了空的响应",
                            "status": "error"
                        })
                        return
                    
                    content = choices[0].get("message", {}).get("content", "")
                    if not content:
                        logger.error(f"对话API响应中没有内容: {response_data}")
                        yield json.dumps({
                            "error": "API返回了空的对话内容",
                            "status": "error"
                        })
                        return
                    
                    logger.info(f"对话响应完成，长度: {len(content)}")
                    yield json.dumps({
                        "content": content,
                        "status": "completed"
                    })
                    
        except Exception as e:
            logger.error(f"处理对话请求失败: {str(e)}")
            logger.exception(e)
            yield json.dumps({
                "error": f"处理对话请求失败: {str(e)}",
                "status": "error"
            })

    def _build_conversation_system_prompt(self, analysis_context: Dict[str, Any]) -> str:
        """
        构建对话系统提示词
        
        Args:
            analysis_context: 原始分析结果上下文
            
        Returns:
            系统提示词字符串
        """
        stock_codes = analysis_context.get("stock_codes", [])
        market_type = analysis_context.get("market_type", "A")
        analysis_result = analysis_context.get("analysis_result", {})
        ai_output = analysis_context.get("ai_output", "")
        chart_data = analysis_context.get("chart_data", {})
        
        # 构建股票信息摘要
        stock_summary = []
        if analysis_result:  # 检查analysis_result是否为None
            for code in stock_codes:
                if code in analysis_result:
                    stock_info = analysis_result[code]
                    summary = f"{code}: 价格{stock_info.get('price', 'N/A')}, 评分{stock_info.get('score', 'N/A')}, RSI{stock_info.get('rsi', 'N/A')}"
                    stock_summary.append(summary)
        
        # 市场类型映射
        market_names = {
            "A": "A股",
            "HK": "港股", 
            "US": "美股",
            "ETF": "ETF基金",
            "LOF": "LOF基金"
        }
        market_name = market_names.get(market_type, market_type)
        
        system_prompt = f"""
你是一个专业的股票分析师助手。用户正在与你讨论关于{market_name}的分析结果。

## 分析背景信息

**分析的股票**: {', '.join(stock_codes)}
**市场类型**: {market_name}
**分析周期**: {analysis_context.get('analysis_days', 30)}天

**股票技术指标摘要**:
{chr(10).join(stock_summary) if stock_summary else '暂无详细数据'}

**原始AI分析结果**:
{ai_output if ai_output else '暂无AI分析结果'}

## 你的职责

1. **基于原始分析结果**: 你的回答应该基于上述分析背景，不要偏离原始分析的核心内容
2. **提供专业建议**: 结合技术指标和市场情况，给出专业的投资建议
3. **解释技术概念**: 如果用户询问技术指标或分析方法，请详细解释
4. **风险评估**: 始终提醒用户投资风险，强调投资需要谨慎
5. **保持一致性**: 确保你的回答与原始分析结果保持一致

## 回答要求

- 保持专业、客观的语气
- 提供具体的数据支持，情况恶劣的情况下，也可以给出看空的指引
- 考虑市场特点和风险因素
- 可结合一些仓位假设来给出指引
- 可给长期投资、短期操作等不同角度的建议
- 如果用户的问题超出分析范围，请说明并提供相关建议
- 始终强调投资有风险，建议用户谨慎决策

请基于以上背景信息回答用户的问题。
"""
        
        return system_prompt 