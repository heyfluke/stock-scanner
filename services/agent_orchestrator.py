from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator, Dict, List, Optional

from utils.logger import get_logger
from services.stock_analyzer_service import StockAnalyzerService
from services.stock_data_provider import StockDataProvider
from services.technical_indicator import TechnicalIndicator
from services.stock_scorer import StockScorer
from services.ai_analyzer import AIAnalyzer
import pandas as pd


logger = get_logger()


class AgentOrchestrator:
    """
    Minimal multi-agent orchestrator to support preset-based analysis without
    breaking existing API contracts. For now, presets route to existing
    StockAnalyzerService pipelines, while establishing a unified interface
    for future graph/node orchestration.
    """

    # Built-in presets registry (minimal). In the future this can be loaded
    # from DB tables created by migrations v7-v9.
    BUILTIN_PRESETS: List[Dict] = [
        {
            "id": "standard",
            "name": "标准版",
            "description": "数据→指标→评分→LLM 标准流程",
            "graph": {
                "nodes": [
                    {"id": "ind", "type": "Indicator"},
                    {"id": "score", "type": "Scoring"},
                    {"id": "llm", "type": "LLMAnalyst"},
                ],
                "edges": [
                    {"from": "ind", "to": "score"},
                    {"from": "score", "to": "llm"},
                ],
            },
            "enabled": True,
            "is_builtin": True,
        },
        {
            "id": "risk_first",
            "name": "风控优先",
            "description": "在LLM前增加风控评估（占位，暂与标准版一致）",
            "graph": {},
            "enabled": True,
            "is_builtin": True,
        },
        {
            "id": "multi_model_vote",
            "name": "多模型共识",
            "description": "多模型投票（占位，暂与标准版一致）",
            "graph": {},
            "enabled": True,
            "is_builtin": True,
        },
        {
            "id": "single_model_roles",
            "name": "单模型多角色",
            "description": "一个模型，通过多角色提示词产出多视角结论，并由综合者聚合为执行建议",
            "graph": {},
            "params": {
                "roles": [
                    "trend_analyst",
                    "levels_mapper",
                    "risk_position",
                    "execution_planner",
                    "devils_advocate",
                    "scenario_planner",
                    "synthesizer"
                ]
            },
            "enabled": True,
            "is_builtin": True,
        },
    ]

    def __init__(
        self,
        custom_api_url: Optional[str] = None,
        custom_api_key: Optional[str] = None,
        custom_api_model: Optional[str] = None,
        custom_api_timeout: Optional[str] = None,
    ) -> None:
        self._stock_service = StockAnalyzerService(
            custom_api_url=custom_api_url,
            custom_api_key=custom_api_key,
            custom_api_model=custom_api_model,
            custom_api_timeout=custom_api_timeout,
        )
        # Components for custom pipelines
        self._data_provider = StockDataProvider()
        self._indicator = TechnicalIndicator()
        self._scorer = StockScorer()
        self._api_url = custom_api_url
        self._api_key = custom_api_key
        self._api_model = custom_api_model
        self._api_timeout = custom_api_timeout

    @classmethod
    def list_presets(cls) -> List[Dict]:
        """Return available presets (built-in for now)."""
        return [p for p in cls.BUILTIN_PRESETS if p.get("enabled")]

    @classmethod
    def get_preset(cls, preset_id: Optional[str]) -> Optional[Dict]:
        if not preset_id:
            return None
        for p in cls.BUILTIN_PRESETS:
            if p.get("id") == preset_id and p.get("enabled"):
                return p
        return None

    async def run(
        self,
        stock_codes: List[str],
        market_type: str,
        stream: bool,
        analysis_days: int,
        preset_id: Optional[str] = None,
        portfolio_context: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute analysis according to the preset. For MVP, all presets map to
        existing StockAnalyzerService flows to ensure output compatibility.
        
        Args:
            portfolio_context: Optional user portfolio information to include in analysis
        """
        preset = self.get_preset(preset_id)
        preset_key = preset.get("id") if preset else "standard"

        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Emit a small orchestrator init message (non-breaking, optional fields)
        init_msg = {
            "orchestrator": {
                "preset_id": preset_key,
                "status": "initialized",
                "analysis_id": analysis_id,
            }
        }
        yield json.dumps(init_msg, ensure_ascii=False)

        # Single-model multi-role preset
        if preset_key == "single_model_roles":
            async for chunk in self._run_single_model_roles(stock_codes, market_type, analysis_days, portfolio_context):
                yield chunk
            return

        if len(stock_codes) == 1:
            async for chunk in self._stock_service.analyze_stock(
                stock_codes[0], market_type, stream=stream, analysis_days=analysis_days, portfolio_context=portfolio_context
            ):
                yield chunk
        else:
            async for chunk in self._stock_service.scan_stocks(
                stock_codes,
                market_type=market_type,
                min_score=0,
                stream=stream,
                analysis_days=analysis_days,
            ):
                yield chunk


    async def _run_single_model_roles(
        self,
        stock_codes: List[str],
        market_type: str,
        analysis_days: int,
        portfolio_context: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Single-model multi-role pipeline with synthesizer aggregation.
        Streams per-role outputs and finishes with a synthesized plan.
        
        Args:
            portfolio_context: Optional user portfolio information to include in analysis
        """
        role_templates = (
            ("技术趋势分析师", "你是技术分析师。基于技术摘要与近{days}日数据，输出: 趋势(UP/DOWN/FLAT)、动量质量、关键证据(3-5条)、关键技术位(支撑/压力)。数据: {summary} 近{days}日数据: {recent} 市场:{market} 标的:{code}"),
            ("支撑/压力映射师", "你是支撑/压力映射师。给出最近有效的支撑/压力价位数组(具体数字)、触发条件(突破/跌破)、无效化条件，避免含糊表述。数据: {recent} 市场:{market} 标的:{code}"),
            ("波动与仓位管理师", "你是风险与仓位管理师。基于波动率/量能/RSI建议仓位(0-100%)、止损(价或比例)、持仓周期(短/中)，并给出加减仓规则的量化阈值。摘要: {summary} 数据: {recent}"),
            ("交易执行规划师", "你是交易执行规划师。把当前观点转为执行清单: 入场区间、分批计划、止损、目标位(1/2/3)、必要执行条件(必须满足/最好满足)。结合前述角色要点: {prev}"),
            ("反对意见审阅官", "你是反对意见审阅官。提出3条反向风险论据及其失效/触发条件，并给出触发后的应对方案。结合前述要点: {prev}"),
            ("场景推演规划师", "你是场景推演规划师。在顺利/震荡/反转三种情境下给出不同的进退规则、持仓/止盈调整与再次验证点。结合要点: {prev}"),
        )

        for code in stock_codes:
            # 初始化token使用统计
            total_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0  # 如果需要的话
            }
            
            # Init header
            yield json.dumps({"stream_type": "single", "stock_code": code}, ensure_ascii=False)

            # Indicators and basic score (compatible with UI)
            df = await self._data_provider.get_stock_data(code, market_type)
            df_ind = self._indicator.calculate_indicators(df)
            score = self._scorer.calculate_score(df_ind)
            rec0 = self._scorer.get_recommendation(score)
            latest = df_ind.iloc[-1]
            prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest
            price_change_value = float(latest['Close'] - prev['Close'])
            change_percent = latest.get('Change_pct')
            yield json.dumps({
                "stock_code": code,
                "score": int(score),
                "recommendation": rec0,
                "price": float(latest.get('Close', 0)),
                "price_change_value": price_change_value,
                "price_change": change_percent,
                "change_percent": change_percent,
                "rsi": float(latest.get('RSI', 0)) if 'RSI' in latest else None,
                "ma_trend": "UP" if latest.get('MA5', 0) > latest.get('MA20', 0) else "DOWN",
                "macd_signal": "BUY" if latest.get('MACD', 0) > latest.get('MACD_Signal', 0) else "SELL",
                "volume_status": "HIGH" if latest.get('Volume_Ratio', 1) > 1.5 else ("LOW" if latest.get('Volume_Ratio', 1) < 0.5 else "NORMAL"),
                "status": "waiting"
            }, ensure_ascii=False)

            # Build shared summary and recent data
            technical_summary = {
                'trend': 'upward' if df_ind.iloc[-1]['MA5'] > df_ind.iloc[-1]['MA20'] else 'downward',
                'volatility': f"{df_ind.iloc[-1]['Volatility']:.2f}%" if 'Volatility' in df_ind.columns else "",
                'volume_trend': 'increasing' if df_ind.iloc[-1].get('Volume_Ratio', 1) > 1 else 'decreasing',
                'rsi_level': float(df_ind.iloc[-1].get('RSI', 50))
            }
            recent_df = df_ind.tail(analysis_days).copy()
            recent_df.reset_index(inplace=True)
            recent_df.rename(columns={recent_df.columns[0]: 'date'}, inplace=True)
            if pd.api.types.is_datetime64_any_dtype(recent_df['date']):
                recent_df['date'] = recent_df['date'].dt.strftime('%Y-%m-%d')
            else:
                try:
                    recent_df['date'] = pd.to_datetime(recent_df['date']).dt.strftime('%Y-%m-%d')
                except Exception:
                    recent_df['date'] = recent_df['date'].astype(str)
            recent_data = recent_df.to_dict('records')

            # Send chart data chunk
            yield json.dumps({
                "stock_code": code,
                "status": "analyzing",
                "chart_data": recent_data
            }, ensure_ascii=False)

            # Run roles with single model
            ai = AIAnalyzer(
                custom_api_url=self._api_url,
                custom_api_key=self._api_key,
                custom_api_model=self._api_model,
                custom_api_timeout=self._api_timeout,
            )
            collected_text = ""
            for idx, (role_name, tmpl) in enumerate(role_templates, start=1):
                logger.info(f"开始调用角色 {role_name} 分析股票 {code} (第{idx}/{len(role_templates)}个角色)")
                
                prompt = tmpl.format(
                    days=analysis_days,
                    summary=technical_summary,
                    recent=recent_data,
                    market=market_type,
                    code=code,
                    prev=collected_text,
                )
                
                # 如果是第一个角色且提供了portfolio_context，添加到prompt
                if idx == 1 and portfolio_context:
                    logger.info(f"📋 检测到持仓信息，准备添加到{role_name}的分析提示词 (长度: {len(portfolio_context)} 字符)")
                    prompt += f"\n\n{'='*50}\n📊 我的持仓情况\n{'='*50}\n{portfolio_context}"
                    logger.info(f"✅ 已将用户持仓信息添加到{role_name}的分析提示词中")
                    logger.debug(f"完整prompt长度: {len(prompt)} 字符")
                elif idx == 1:
                    logger.debug(f"❌ portfolio_context 为空，未添加持仓信息到{role_name}")
                
                # 发送角色开始标记
                yield json.dumps({
                    "stock_code": code,
                    "ai_analysis_chunk": f"<analysis>\n\n### {role_name}\n",
                    "status": "analyzing",
                    "role": role_name,
                    "order": idx
                }, ensure_ascii=False)
                
                role_text = ""
                role_usage = None
                try:
                    # 流式接收角色分析
                    stream_gen = await ai.get_completion(prompt, stream=True)
                    async for chunk_data in stream_gen:
                        # chunk_data 现在是 (content, usage) 元组
                        if isinstance(chunk_data, tuple):
                            chunk, usage = chunk_data
                            logger.debug(f"收到元组: chunk长度={len(chunk)}, usage={usage}")
                        else:
                            # 向后兼容：如果不是元组，当作纯内容处理
                            chunk = chunk_data
                            usage = None
                            logger.debug(f"收到字符串: chunk长度={len(chunk)}")
                        
                        role_text += chunk
                        
                        # 保存usage信息（如果有）
                        if usage:
                            role_usage = usage
                            logger.info(f"角色 {role_name} 收到usage信息: {usage}")
                        
                        # 实时发送流式片段
                        if chunk:  # 只发送有内容的chunk
                            yield json.dumps({
                                "stock_code": code,
                                "ai_analysis_chunk": chunk,
                                "status": "analyzing",
                                "role": role_name,
                                "order": idx
                            }, ensure_ascii=False)
                    
                    # 累积token使用
                    if role_usage:
                        total_usage["prompt_tokens"] += role_usage.get("prompt_tokens", 0)
                        total_usage["completion_tokens"] += role_usage.get("completion_tokens", 0)
                        total_usage["total_tokens"] += role_usage.get("total_tokens", 0)
                        logger.info(f"累积后总token使用: {total_usage}")
                    
                    logger.info(f"角色 {role_name} 分析完成，输出长度: {len(role_text)} 字符，token使用: {role_usage}")
                except Exception as e:
                    logger.exception(f"Role {role_name} generation failed for stock {code}")
                    # 角色分析失败时，发送错误消息并终止整个分析
                    error_msg = f"角色 {role_name} 分析失败: {str(e)}"
                    if "ReadTimeout" in str(type(e).__name__) or "timeout" in str(e).lower():
                        error_msg = f"角色 {role_name} 分析超时（可能是AI服务响应慢或超时设置过短）"
                    
                    yield json.dumps({
                        "stock_code": code,
                        "status": "error",
                        "error": error_msg
                    }, ensure_ascii=False)
                    return  # 终止整个分析流程
                
                # 发送角色结束标记
                yield json.dumps({
                    "stock_code": code,
                    "ai_analysis_chunk": "\n</analysis>",
                    "status": "analyzing",
                    "role": role_name,
                    "order": idx
                }, ensure_ascii=False)
                
                collected_text += f"\n\n[{role_name}]\n{role_text}"

            # Synthesizer
            logger.info(f"开始调用综合决策官汇总所有角色结论 (股票: {code})")
            synth_prompt = (
                "你是综合决策官，汇总下列多角色结论，按统一结构输出: \n"
                "- 结论(买入/持有/卖出/观望)\n- 证据(3-5条)\n- 行动(入场区间/止损/目标位/仓位/时间框)\n- 风险(2-3条与触发条件)\n- 置信度(0-1)\n\n"
                f"多角色结论如下:\n{collected_text}\n"
            )
            
            # 发送综合决策开始标记（使用 ai_analysis_chunk 保持一致性）
            yield json.dumps({
                "stock_code": code,
                "ai_analysis_chunk": "<final>### 综合决策官\n\n",
                "status": "analyzing"
            }, ensure_ascii=False)
            
            final_text = ""
            final_usage = None
            try:
                # 流式接收综合决策
                stream_gen = await ai.get_completion(synth_prompt, stream=True)
                async for chunk_data in stream_gen:
                    # chunk_data 现在是 (content, usage) 元组
                    if isinstance(chunk_data, tuple):
                        chunk, usage = chunk_data
                    else:
                        # 向后兼容：如果不是元组，当作纯内容处理
                        chunk = chunk_data
                        usage = None
                    
                    final_text += chunk
                    
                    # 保存usage信息（如果有）
                    if usage:
                        final_usage = usage
                        logger.info(f"综合决策官收到usage信息: {usage}")
                    
                    # 实时发送流式片段
                    if chunk:  # 只发送有内容的chunk
                        yield json.dumps({
                            "stock_code": code,
                            "ai_analysis_chunk": chunk,
                            "status": "analyzing"
                        }, ensure_ascii=False)
                
                # 累积综合决策的token使用
                if final_usage:
                    total_usage["prompt_tokens"] += final_usage.get("prompt_tokens", 0)
                    total_usage["completion_tokens"] += final_usage.get("completion_tokens", 0)
                    total_usage["total_tokens"] += final_usage.get("total_tokens", 0)
                    logger.info(f"累积后总token使用: {total_usage}")
                
                logger.info(f"综合决策官分析完成，输出长度: {len(final_text)} 字符，token使用: {final_usage}")
            except Exception as e:
                logger.exception(f"综合决策官执行失败: {e}")
                # 综合决策官失败时，发送错误消息并终止
                error_msg = f"综合决策官分析失败: {str(e)}"
                if "ReadTimeout" in str(type(e).__name__) or "timeout" in str(e).lower():
                    error_msg = f"综合决策官分析超时（可能是AI服务响应慢或超时设置过短）"
                
                yield json.dumps({
                    "stock_code": code,
                    "status": "error",
                    "error": error_msg
                }, ensure_ascii=False)
                return  # 终止整个分析流程

            # 发送综合决策结束标记
            yield json.dumps({
                "stock_code": code,
                "ai_analysis_chunk": "</final>",
                "status": "analyzing"
            }, ensure_ascii=False)

            # Extract recommendation using existing helper
            rec_text = AIAnalyzer(
                custom_api_url=self._api_url,
                custom_api_key=self._api_key,
                custom_api_model=self._api_model,
                custom_api_timeout=self._api_timeout,
            )._extract_recommendation(final_text)

            # 发送完成状态（包含token使用信息）
            completion_data = {
                "stock_code": code,
                "status": "completed",
                "recommendation": rec_text
            }
            
            # 添加token使用信息到响应中
            logger.info(f"检查token使用统计: total_tokens={total_usage['total_tokens']}")
            
            if total_usage["total_tokens"] > 0:
                # 有精确的token统计
                completion_data["token_usage"] = total_usage
                logger.info(f"股票 {code} 分析完成，总token使用（精确）: {total_usage}")
            else:
                # API不返回usage，使用字符数估算（粗略：1 token ≈ 4 字符）
                # 计算所有角色的输入字符数（prompt）
                prompt_chars = 0
                for _, tmpl in role_templates:
                    prompt_chars += len(tmpl) + len(str(technical_summary)) + len(str(recent_data))
                
                # 计算综合决策的输入字符数
                prompt_chars += len(synth_prompt)
                
                # 计算输出字符数
                output_chars = len(collected_text) + len(final_text)
                
                # 估算token（1 token ≈ 4 字符，中文可能是 1 token ≈ 1.5-2 字符）
                estimated_tokens = (prompt_chars + output_chars) // 3  # 使用3作为中文友好的估算
                
                completion_data["token_usage"] = {
                    "estimated": True,
                    "total_tokens": estimated_tokens,
                    "prompt_chars": prompt_chars,
                    "output_chars": output_chars
                }
                logger.info(f"股票 {code} 分析完成，估算token使用: ~{estimated_tokens} (输入{prompt_chars}字符 + 输出{output_chars}字符)")
            
            yield json.dumps(completion_data, ensure_ascii=False)


