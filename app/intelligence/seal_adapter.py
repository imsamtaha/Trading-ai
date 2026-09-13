"""
SEAL Model Adapter - Interface Contract
=======================================
This is NOT a trained model. It is the contract your real SEAL model must
satisfy to plug into the orchestrator.

To go live, subclass SEALModelInterface and implement predict() using your
actual trained model. Do not use SEALModelInterface directly; it raises
NotImplementedError on purpose, so a forgotten wire-up fails loudly instead
of silently trading on dummy logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Literal, Mapping, NotRequired, TypedDict


SEALSignal = Literal["buy", "sell", "hold"]
ExecutorDecision = Literal["APPROVE_EXECUTION", "REJECT_EXECUTION", "REQUIRE_HUMAN_REVIEW"]


class SEALModelOutput(TypedDict):
    signal: SEALSignal
    confidence: float
    stop_loss_pips: NotRequired[float]
    take_profit_pips: NotRequired[float]


class SEALGateInput(SEALModelOutput, total=False):
    supporting_factors: list[str]
    counter_signals: list[str]
    data_quality_concerns: list[str]


class SEALGateResult(TypedDict):
    executor_decision: ExecutorDecision
    executor_reason: str
    execution_blockers: list[str]
    required_confirmations_met: bool
    human_review_required: bool


class SEALModelInterface(ABC):
    """
    Contract expected by orchestrator.Orchestrator.

    predict() receives the flattened dict produced by
    seal_bridge.feature_merge.MergedFeatureVector.to_model_input(), i.e.:

        {
            "returns": [...],
            "volatility": float,
            "movement_modifier": float,
            "regime_classification": "trending" | "range_bound" | "high_volatility",
            ... any additional keys from your real feature pipeline's
                TechnicalFeatures.raw_features ...,
            "llm_sentiment_score": float,
            "llm_sentiment_weighted": float,
            "llm_event_relevance": float,
            "llm_regime_hint": str,
            "llm_branch_valid": bool,
        }

    predict() must return exactly:

        {
            "signal": "buy" | "sell" | "hold",
            "confidence": float,
            "stop_loss_pips": float,
            "take_profit_pips": float,
        }

    Directional signals must include positive stop-loss and take-profit
    distances. Confidence must be calibrated, not aspirational.
    """

    @abstractmethod
    def predict(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        """Implement using your real trained SEAL model."""
        raise NotImplementedError(
            "SEALModelInterface.predict() is a contract, not an implementation. "
            "Subclass this with your real trained model."
        )

    def predict_and_validate(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        output = self.predict(model_input)
        self._validate_output(output)
        return output

    @staticmethod
    def _validate_output(output: Dict[str, Any]) -> None:
        if "signal" not in output or output["signal"] not in ("buy", "sell", "hold"):
            raise ValueError(f"SEAL model output missing/invalid 'signal': {output.get('signal')!r}")

        if "confidence" not in output:
            raise ValueError("SEAL model output missing 'confidence'.")
        conf = output["confidence"]
        if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            raise ValueError(f"SEAL model 'confidence' must be a float in [0,1], got {conf!r}")

        if output["signal"] in ("buy", "sell"):
            sl = output.get("stop_loss_pips")
            if sl is None or not isinstance(sl, (int, float)) or sl <= 0:
                raise ValueError(
                    f"SEAL model signal={output['signal']!r} requires a positive "
                    f"stop_loss_pips, got {sl!r}. Never emit a directional signal "
                    f"without a real stop."
                )
            tp = output.get("take_profit_pips")
            if tp is None or not isinstance(tp, (int, float)) or tp <= 0:
                raise ValueError(
                    f"SEAL model signal={output['signal']!r} requires a positive "
                    f"take_profit_pips, got {tp!r}."
                )


class UnimplementedSEALModel(SEALModelInterface):
    """Default model placeholder that fails loudly until a real model is wired."""

    def predict(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "No real SEAL model has been wired in. Replace UnimplementedSEALModel "
            "with a subclass of SEALModelInterface that calls your actual trained model."
        )


class ExecutionGatekeeper:
    """Confirm whether a calibrated SEAL/ATLAS signal is eligible for execution.

    This gate does not place trades and does not size positions. It only returns
    APPROVE_EXECUTION, REJECT_EXECUTION, or REQUIRE_HUMAN_REVIEW for the final
    risk/execution layer.
    """

    MIN_CONFIDENCE = 0.70
    MIN_CONFIRMATIONS = 3

    CRITICAL_COUNTER_TERMS = (
        "critical",
        "invalidates",
        "high-impact news",
        "spread too wide",
        "stale data",
        "major event",
    )

    def evaluate(
        self,
        signal: Mapping[str, Any],
        market_context: Mapping[str, Any] | None = None,
    ) -> SEALGateResult:
        blockers: list[str] = []
        normalized_signal = str(signal.get("signal", "hold")).lower()
        confidence = float(signal.get("confidence", 0.0) or 0.0)
        supporting_factors = list(signal.get("supporting_factors") or [])
        counter_signals = list(signal.get("counter_signals") or [])
        data_quality_concerns = list(signal.get("data_quality_concerns") or [])
        stop_loss_pips = float(signal.get("stop_loss_pips", 0.0) or 0.0)
        take_profit_pips = float(signal.get("take_profit_pips", 0.0) or 0.0)

        if normalized_signal == "hold":
            blockers.append("Signal is HOLD; execution is not allowed.")
        if normalized_signal not in {"buy", "sell", "hold"}:
            blockers.append("Signal is invalid.")
        if confidence < self.MIN_CONFIDENCE:
            blockers.append("Signal confidence is below execution threshold.")
        if len(supporting_factors) < self.MIN_CONFIRMATIONS:
            blockers.append("Fewer than 3 independent confirmations.")
        if normalized_signal in {"buy", "sell"} and stop_loss_pips <= 0:
            blockers.append("Missing or invalid stop loss.")
        if normalized_signal in {"buy", "sell"} and take_profit_pips <= stop_loss_pips:
            blockers.append("Take profit does not exceed stop loss.")

        has_critical_counter_signal = any(
            term in str(item).lower()
            for item in counter_signals
            for term in self.CRITICAL_COUNTER_TERMS
        )
        if has_critical_counter_signal:
            blockers.append("Critical counter-signal detected.")

        if market_context:
            if not market_context.get("spread_ok", True):
                blockers.append("Market spread is not acceptable.")
            if not market_context.get("volatility_ok", True):
                blockers.append("Market volatility is not acceptable.")
            if not market_context.get("session_ok", True):
                blockers.append("Trading session conditions are not acceptable.")
            if market_context.get("high_impact_news", False):
                blockers.append("High-impact news conflict detected.")

        required_confirmations_met = (
            normalized_signal in {"buy", "sell"}
            and confidence >= self.MIN_CONFIDENCE
            and len(supporting_factors) >= self.MIN_CONFIRMATIONS
            and stop_loss_pips > 0
            and take_profit_pips > stop_loss_pips
        )

        if data_quality_concerns:
            blockers.append("Data quality concerns require review.")

        if blockers:
            review_only = required_confirmations_met and blockers == ["Data quality concerns require review."]
            return {
                "executor_decision": "REQUIRE_HUMAN_REVIEW" if review_only else "REJECT_EXECUTION",
                "executor_reason": "; ".join(blockers),
                "execution_blockers": blockers,
                "required_confirmations_met": required_confirmations_met,
                "human_review_required": review_only,
            }

        return {
            "executor_decision": "APPROVE_EXECUTION",
            "executor_reason": "Signal passed confirmation, stop-loss, target, and market-context checks.",
            "execution_blockers": [],
            "required_confirmations_met": True,
            "human_review_required": False,
        }
