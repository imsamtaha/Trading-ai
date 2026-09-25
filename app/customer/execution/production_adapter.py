class ProductionAdapter:
    """Reserved production interface. This plan intentionally does not activate it."""

    def execute(self, intent, risk: dict, *, trace_id: str):
        raise RuntimeError("LIVE_EXECUTION adapter is not active in customer v2")
