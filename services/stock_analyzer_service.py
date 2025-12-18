import json
from datetime import datetime
from typing import List, AsyncGenerator, Optional
from utils.logger import get_logger
from services.stock_data_provider import StockDataProvider
from services.technical_indicator import TechnicalIndicator
from services.stock_scorer import StockScorer
from services.ai_analyzer import AIAnalyzer

# 获取日志器
logger = get_logger()

class StockAnalyzerService:
    """
    股票分析服务
    作为门面类协调数据提供、指标计算、评分和AI分析等组件
    """
    
    def __init__(self, custom_api_url=None, custom_api_key=None, custom_api_model=None, custom_api_timeout=None):
        """
        初始化股票分析服务
        
        Args:
            custom_api_url: 自定义API URL
            custom_api_key: 自定义API密钥
            custom_api_model: 自定义API模型
            custom_api_timeout: 自定义API超时时间
        """
        # 初始化各个组件
        self.data_provider = StockDataProvider()
        self.indicator = TechnicalIndicator()
        self.scorer = StockScorer()
        self.ai_analyzer = AIAnalyzer(
            custom_api_url=custom_api_url,
            custom_api_key=custom_api_key,
            custom_api_model=custom_api_model,
            custom_api_timeout=custom_api_timeout
        )
        
        logger.info("初始化StockAnalyzerService完成")
    
    async def analyze_stock(self, stock_code: str, market_type: str = 'A', stream: bool = False, analysis_days: int = 30, portfolio_context: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        分析单只股票
        
        Args:
            stock_code: 股票代码
            market_type: 市场类型，默认为'A'股
            stream: 是否使用流式响应
            analysis_days: AI分析使用的天数，默认30天
            portfolio_context: 用户持仓信息（可选），将添加到分析提示词中
            
        Returns:
            异步生成器，生成分析结果的JSON字符串
        """
        try:
            logger.info(f"开始分析股票: {stock_code}, 市场: {market_type}")
            logger.info(f"🔍 analyze_stock接收到的portfolio_context: {'存在' if portfolio_context else '不存在'}, 长度={len(portfolio_context) if portfolio_context else 0}")
            
            # 获取股票数据
            logger.debug(f"准备从 data_provider 获取股票代码为 '{stock_code}' 的数据...")
            df = await self.data_provider.get_stock_data(stock_code, market_type)
            logger.debug(f"从 data_provider 获取数据完成。DataFrame is empty: {df.empty}")
            
            # 检查是否有错误
            if hasattr(df, 'error'):
                error_msg = df.error
                logger.error(f"获取股票数据时出错: {error_msg}")
                yield json.dumps({
                    "stock_code": stock_code,
                    "market_type": market_type,
                    "error": error_msg,
                    "status": "error"
                }, ensure_ascii=False)
                return
            
            # 检查数据是否为空
            if df.empty:
                error_msg = f"获取到的股票 {stock_code} 数据为空"
                logger.error(error_msg)
                yield json.dumps({
                    "stock_code": stock_code,
                    "market_type": market_type,
                    "error": error_msg,
                    "status": "error"
                }, ensure_ascii=False)
                return
            
            # 计算技术指标
            df_with_indicators = self.indicator.calculate_indicators(df)
            
            # 计算评分
            score = self.scorer.calculate_score(df_with_indicators)
            recommendation = self.scorer.get_recommendation(score)
            
            # 获取最新数据
            latest_data = df_with_indicators.iloc[-1]
            previous_data = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else latest_data
            
            # 价格变动绝对值
            price_change_value = latest_data['Close'] - previous_data['Close']
            
            # 优先使用原始数据中的涨跌幅(Change_pct)
            change_percent = latest_data.get('Change_pct')
            
            # 如果原始数据中没有涨跌幅，才进行计算
            if change_percent is None and previous_data['Close'] != 0:
                change_percent = (price_change_value / previous_data['Close']) * 100
            
            # 确定MA趋势
            ma_short = latest_data.get('MA5', 0)
            ma_medium = latest_data.get('MA20', 0)
            ma_long = latest_data.get('MA60', 0)
            
            if ma_short > ma_medium > ma_long:
                ma_trend = "UP"
            elif ma_short < ma_medium < ma_long:
                ma_trend = "DOWN"
            else:
                ma_trend = "FLAT"
                
            # 确定MACD信号
            macd = latest_data.get('MACD', 0)
            signal = latest_data.get('Signal', 0)
            
            if macd > signal:
                macd_signal = "BUY"
            elif macd < signal:
                macd_signal = "SELL"
            else:
                macd_signal = "HOLD"
                
            # 确定成交量状态
            volume = latest_data.get('Volume', 0)
            volume_ma = latest_data.get('Volume_MA', 0)
            
            if volume > volume_ma * 1.5:
                volume_status = "HIGH"
            elif volume < volume_ma * 0.5:
                volume_status = "LOW"
            else:
                volume_status = "NORMAL"
                
            # 当前分析日期
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 生成基本分析结果
            basic_result = {
                "stock_code": stock_code,
                "market_type": market_type,
                "analysis_date": analysis_date,
                "score": score,
                "price": latest_data['Close'],
                "price_change_value": price_change_value,  # 价格变动绝对值
                "price_change": change_percent,  # 兼容旧版前端，传递涨跌幅
                "change_percent": change_percent,  # 涨跌幅百分比，新字段
                "ma_trend": ma_trend,
                "rsi": latest_data.get('RSI', 0),
                "macd_signal": macd_signal,
                "volume_status": volume_status,
                "recommendation": recommendation,
                "ai_analysis": ""
            }
            
            # 输出基本分析结果
            logger.info(f"基本分析结果: {json.dumps(basic_result)}")
            yield json.dumps(basic_result, ensure_ascii=False)
            
            # 使用AI进行深入分析
            async for analysis_chunk in self.ai_analyzer.get_ai_analysis(df_with_indicators, stock_code, market_type, stream, analysis_days, portfolio_context):
                yield analysis_chunk
                
            logger.info(f"完成股票分析: {stock_code}")
            
        except Exception as e:
            error_msg = f"分析股票 {stock_code} 时出错: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            yield json.dumps({"error": error_msg, "stock_code": stock_code}, ensure_ascii=False)
    
    async def scan_stocks(self, stock_codes: List[str], market_type: str = 'A', min_score: int = 0, stream: bool = False, analysis_days: int = 30) -> AsyncGenerator[str, None]:
        """
        批量扫描股票
        
        Args:
            stock_codes: 股票代码列表
            market_type: 市场类型
            min_score: 最低评分阈值
            stream: 是否使用流式响应
            analysis_days: AI分析使用的天数，默认30天
            
        Returns:
            异步生成器，生成扫描结果的JSON字符串
        """
        try:
            logger.info(f"开始批量扫描 {len(stock_codes)} 只股票, 市场: {market_type}")
            
            # 输出初始状态 - 发送批量分析初始化消息
            yield json.dumps({
                "stream_type": "batch",
                "stock_codes": stock_codes,
                "market_type": market_type,
                "min_score": min_score
            }, ensure_ascii=False)
            
            # 批量获取股票数据
            logger.debug(f"准备从 data_provider 批量获取 {len(stock_codes)} 个股票代码的数据...")
            stock_data_dict = await self.data_provider.get_multiple_stocks_data(stock_codes, market_type)
            logger.debug(f"批量获取数据完成。获取到 {len(stock_data_dict)} 个股票的数据。")
            
            # 计算技术指标
            stock_with_indicators = {}
            for code, df in stock_data_dict.items():
                try:
                    stock_with_indicators[code] = self.indicator.calculate_indicators(df)
                except Exception as e:
                    logger.error(f"计算 {code} 技术指标时出错: {str(e)}")
                    # 发送错误状态
                    yield json.dumps({
                        "stock_code": code,
                        "error": f"计算技术指标时出错: {str(e)}",
                        "status": "error"
                    }, ensure_ascii=False)
            
            # 评分股票
            results = self.scorer.batch_score_stocks(stock_with_indicators)
            
            # 过滤低于最低评分的股票
            filtered_results = [r for r in results if r[1] >= min_score]
            
            # 为每只股票发送基本评分和推荐信息
            for code, score, rec in results:
                df = stock_with_indicators.get(code)
                if df is not None and len(df) > 0:
                    # 获取最新数据
                    latest_data = df.iloc[-1]
                    previous_data = df.iloc[-2] if len(df) > 1 else latest_data
                    
                    # 价格变动绝对值
                    price_change_value = latest_data['Close'] - previous_data['Close']
                    
                    # 获取涨跌幅
                    change_percent = latest_data.get('Change_pct')
                    
                    # 发送股票基本信息和评分
                    yield json.dumps({
                        "stock_code": code,
                        "score": score,
                        "recommendation": rec,
                        "price": float(latest_data.get('Close', 0)),
                        "price_change_value": float(price_change_value),  # 价格变动绝对值
                        "price_change": change_percent,  # 兼容旧版前端，传递涨跌幅
                        "change_percent": change_percent,  # 涨跌幅百分比，新字段
                        "rsi": float(latest_data.get('RSI', 0)) if 'RSI' in latest_data else None,
                        "ma_trend": "UP" if latest_data.get('MA5', 0) > latest_data.get('MA20', 0) else "DOWN",
                        "macd_signal": "BUY" if latest_data.get('MACD', 0) > latest_data.get('MACD_Signal', 0) else "SELL",
                        "volume_status": "HIGH" if latest_data.get('Volume_Ratio', 1) > 1.5 else ("LOW" if latest_data.get('Volume_Ratio', 1) < 0.5 else "NORMAL"),
                        "status": "completed" if score < min_score else "waiting"
                    }, ensure_ascii=False)
            
            # 如果需要进一步分析，对评分较高的股票进行AI分析
            if stream and filtered_results:
                # 只分析前5只评分最高的股票，避免分析过多导致前端卡顿
                top_stocks = filtered_results[:5]
                
                for stock_code, score, _ in top_stocks:
                    df = stock_with_indicators.get(stock_code)
                    if df is not None:
                        # 输出正在分析的股票信息
                        yield json.dumps({
                            "stock_code": stock_code,
                            "status": "analyzing"
                        }, ensure_ascii=False)
                        
                        # AI分析
                        async for analysis_chunk in self.ai_analyzer.get_ai_analysis(df, stock_code, market_type, stream, analysis_days):
                            yield analysis_chunk
            
            # 输出扫描完成信息
            yield json.dumps({
                "scan_completed": True,
                "total_scanned": len(results),
                "total_matched": len(filtered_results)
            }, ensure_ascii=False)
            
            logger.info(f"完成批量扫描 {len(stock_codes)} 只股票, 符合条件: {len(filtered_results)}")
            
        except Exception as e:
            error_msg = f"批量扫描股票时出错: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            yield json.dumps({"error": error_msg}, ensure_ascii=False)
