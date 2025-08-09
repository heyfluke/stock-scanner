from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional

from utils.logger import get_logger
from services.stock_analyzer_service import StockAnalyzerService


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
    ) -> AsyncGenerator[str, None]:
        """
        Execute analysis according to the preset. For MVP, all presets map to
        existing StockAnalyzerService flows to ensure output compatibility.
        """
        preset = self.get_preset(preset_id)
        preset_key = preset.get("id") if preset else "standard"

        # Emit a small orchestrator init message (non-breaking, optional fields)
        init_msg = {
            "orchestrator": {
                "preset_id": preset_key,
                "status": "initialized",
            }
        }
        yield json.dumps(init_msg, ensure_ascii=False)

        if len(stock_codes) == 1:
            async for chunk in self._stock_service.analyze_stock(
                stock_codes[0], market_type, stream=stream, analysis_days=analysis_days
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


