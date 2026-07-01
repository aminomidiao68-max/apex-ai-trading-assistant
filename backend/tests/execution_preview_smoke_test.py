import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import ExecutionPreviewRequest
from app.services.execution_engine import ExecutionEngine

engine = ExecutionEngine()
preview = engine.preview_order(
    ExecutionPreviewRequest(
        connector="bybit",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        signal_score=82.0,
        risk_approved=True,
    )
)
print(preview.model_dump())
print([item.model_dump() for item in engine.capabilities()])
