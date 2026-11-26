def generate_signal(technical: dict, structure: dict) -> dict:
    score = 50
    reasons = []

    trend = technical.get("trend")
    momentum = technical.get("momentum")
    macd = technical.get("macd_signal")
    market_structure = structure.get("structure")

    if trend == "bullish":
        score += 10
        reasons.append("Technical trend is bullish")
    elif trend == "bearish":
        score -= 10
        reasons.append("Technical trend is bearish")

    if momentum == "bullish":
        score += 8
        reasons.append("Momentum is bullish")
    elif momentum == "bearish":
        score -= 8
        reasons.append("Momentum is bearish")

    if macd == "bullish":
        score += 8
        reasons.append("MACD is bullish")
    elif macd == "bearish":
        score -= 8
        reasons.append("MACD is bearish")

    if market_structure == "bullish":
        score += 12
        reasons.append("Market structure is bullish")
    elif market_structure == "bearish":
        score -= 12
        reasons.append("Market structure is bearish")

    score = max(0, min(100, score))

    if score >= 75:
        direction = "LONG"
    elif score <= 25:
        direction = "SHORT"
    else:
        direction = "WAIT"

    if direction == "LONG":
        confidence = score
    elif direction == "SHORT":
        confidence = 100 - score
    else:
        confidence = 100 - abs(50 - score) * 2

    return {
        "direction": direction,
        "confidence": round(confidence, 2),
        "score": score,
        "reasons": reasons,
    }
