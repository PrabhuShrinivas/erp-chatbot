from typing import Type
from app.metrics.base import MetricExecutor
from app.metrics.outstanding import OutstandingV1
from app.metrics.delivery import OnTimeDeliveryV1
from app.metrics.inventory import StockInHandV1

class MetricRegistry:
    def __init__(self):
        self._registry: dict[str, MetricExecutor] = {}
        
    def register(self, metric: str, version: str, executor: MetricExecutor):
        key = f"{metric}:{version}"
        self._registry[key] = executor
        
    def get(self, metric: str, version: str) -> MetricExecutor | None:
        key = f"{metric}:{version}"
        return self._registry.get(key)
        
    def list_capabilities(self) -> list[str]:
        return list(self._registry.keys())

# Global registry instance
registry = MetricRegistry()

# Register initial capabilities
registry.register("outstanding", "v1", OutstandingV1())
registry.register("on_time_delivery", "v1", OnTimeDeliveryV1())
registry.register("stock_in_hand", "v1", StockInHandV1())
