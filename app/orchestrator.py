"""
Orchestrator
============
Ties every layer together into one decision cycle:

    1. Read account + market state from the connector.
    2. Get technical features from the SEAL feature pipeline.
    3. Get LLM context features optionally, degrading gracefully.
    4. Merge into one feature vector with hard-capped LLM influence.
    5. SEAL model produces a signal + calibrated confidence.
    6. Build a proposal, pass it through execution gate and risk manager.
    7. Log everything. Never place an order outside this path.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.intelligence.seal_adapter import ExecutionGatekeeper, SEALModelInterface
from app.risk.manager import calculate_risk
from app.seal_bridge.feature_merge import LLMContextFeatures, TechnicalFeatures, merge_features

logger = logging.getLogger("orchestrator")


class Connector(Protocol):
    def read_account_state(self) -> dict[str, Any]: ...
    def read_market_state(self, symbol: str, timeframe: str) -> dict[str, Any]: ...
    def place_order(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
    def log_decision_cycle(self, payload: dict[str, Any]) -> None: ...


class FeaturePipeline(Protocol):
    def build(self, market_state: dict[str, Any]) -> TechnicalFeatures: ...


class LLMContextClient(Protocol):
    def build_context(self, market_state: dict[str, Any]) -> LLMContextFeatures: ...


@dataclass
class Orchestrator:
    connector: Connector
    feature_pipeline: FeaturePipeline
    seal_model: SEALModelInterface
    llm_client: LLMContextClient | None = None
    execution_gatekeeper: ExecutionGatekeeper | None = None
    execution_enabled: bool = False
    risk_percent: float = 1.0
    llm_weight: float = 0.15

    def run_cycle(self, symbol: str, timeframe: str) -> dict[str, Any]:
        started_at = time.time()
        account_state = self.connector.read_account_state()
        market_state = self.connector.read_market_state(symbol, timeframe)
        technical_features = self.feature_pipeline.build(market_state)
        llm_context = self._llm_context(market_state)
        merged = merge_features(technical_features, llm_context, llm_weight=self.llm_weight)
        model_input = merged.to_model_input()
        seal_output = self.seal_model.predict_and_validate(model_input)
        proposal = self._build_trade_proposal(
            symbol=symbol,
            timeframe=timeframe,
            model_input=model_input,
            seal_output=seal_output,
            account_state=account_state,
        )
        result = self._finalize_decision(proposal)
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "account_state": account_state,
            "market_state": market_state,
            "model_input": model_input,
            "seal_output": seal_output,
            "proposal": proposal,
            "result": result,
            "elapsed_ms": round((time.time() - started_at) * 1000, 2),
        }
        self._log(payload)
        return result

    def _llm_context(self, market_state: dict[str, Any]) -> LLMContextFeatures:
        if self.llm_client is None:
            return LLMContextFeatures()
        try:
            return self.llm_client.build_context(market_state)
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("LLM context unavailable; continuing without it: %s", exc)
            return LLMContextFeatures()

    def _build_trade_proposal(
        self,
        *,
        symbol: str,
        timeframe: str,
        model_input: dict[str, Any],
        seal_output: dict[str, Any],
        account_state: dict[str, Any],
    ) -> dict[str, Any]:
        signal = str(seal_output["signal"]).lower()
        price = float(model_input.get("price", 0.0) or 0.0)
        pip_size = self._pip_size(symbol)
        stop_loss_pips = float(seal_output.get("stop_loss_pips", 0.0) or 0.0)
        take_profit_pips = float(seal_output.get("take_profit_pips", 0.0) or 0.0)

        entry = price
        stop_loss = 0.0
        take_profit = 0.0
        direction = "WAIT"
        if signal == "buy" and price > 0:
            direction = "LONG"
            stop_loss = price - (stop_loss_pips * pip_size)
            take_profit = price + (take_profit_pips * pip_size)
        elif signal == "sell" and price > 0:
            direction = "SHORT"
            stop_loss = price + (stop_loss_pips * pip_size)
            take_profit = price - (take_profit_pips * pip_size)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "account_balance": float(account_state.get("equity", 0.0) or 0.0),
            "seal_signal": {
                **seal_output,
                "supporting_factors": list(model_input.get("supporting_factors") or []),
                "counter_signals": list(model_input.get("counter_signals") or []),
                "data_quality_concerns": list(model_input.get("data_quality_concerns") or []),
            },
        }

    def _finalize_decision(self, proposal: dict[str, Any]) -> dict[str, Any]:
        gatekeeper = self.execution_gatekeeper or ExecutionGatekeeper()
        executor = gatekeeper.evaluate(proposal["seal_signal"])
        if executor["executor_decision"] != "APPROVE_EXECUTION":
            return {
                "status": "BLOCKED",
                "reason": executor["executor_reason"],
                "executor": executor,
                "proposal": proposal,
            }

        risk = calculate_risk(
            direction=proposal["direction"],
            entry=proposal["entry"],
            stop_loss=proposal["stop_loss"],
            take_profit=proposal["take_profit"],
            account_balance=proposal["account_balance"],
            risk_percent=self.risk_percent,
        )
        if not risk["approved"]:
            return {
                "status": "BLOCKED",
                "reason": risk["reason"],
                "executor": executor,
                "risk": risk,
                "proposal": proposal,
            }

        if not self.execution_enabled:
            return {
                "status": "PAPER_APPROVED",
                "reason": "Execution path approved, but live execution is disabled.",
                "executor": executor,
                "risk": risk,
                "proposal": proposal,
            }

        execution = self.connector.place_order({**proposal, "risk": risk, "executor": executor})
        return {
            "status": "EXECUTED",
            "executor": executor,
            "risk": risk,
            "execution": execution,
            "proposal": proposal,
        }

    def _log(self, payload: dict[str, Any]) -> None:
        try:
            self.connector.log_decision_cycle(payload)
        except Exception as exc:  # pragma: no cover - logging must not place trades
            logger.warning("Decision-cycle logging failed: %s", exc)

    @staticmethod
    def _pip_size(symbol: str) -> float:
        normalized = symbol.upper()
        if normalized.startswith("XAU"):
            return 0.10
        if normalized.startswith("XAG") or normalized.endswith("USDT"):
            return 0.01
        if "JPY" in normalized:
            return 0.01
        return 0.0001
