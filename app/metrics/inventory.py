from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from typing import Any
from app.db.models.domain import Inventory, SalesOrderItem, SalesOrder
from app.metrics.base import ComputedFact

class StockInHandV1:
    async def execute(self, session: AsyncSession, material_code: str, **kwargs) -> ComputedFact:
        # stock_in_hand: physical inventory - quantity committed to open sales orders
        
        # 1. Get physical inventory
        inv_query = select(Inventory.quantity_on_hand).where(Inventory.material_code == material_code)
        inv_result = await session.execute(inv_query)
        physical_qty = inv_result.scalar() or 0.0
        
        # 2. Get quantity committed to open/partially fulfilled sales orders
        # Note: We consider quantity committed as (ordered quantity - delivered quantity)
        commit_query = (
            select(func.coalesce(func.sum(SalesOrderItem.quantity - SalesOrderItem.quantity_delivered), 0))
            .join(SalesOrder)
            .where(SalesOrderItem.material_code == material_code)
            .where(SalesOrder.status.in_(['open', 'partially_fulfilled']))
        )
        commit_result = await session.execute(commit_query)
        committed_qty = commit_result.scalar() or 0.0
        
        available_stock = float(physical_qty) - float(committed_qty)
        
        return ComputedFact(
            fact_id=str(uuid.uuid4()),
            metric="stock_in_hand",
            metric_version="v1",
            value=available_stock,
            unit="quantity",
            currency=None,
            entity_id=None,
            as_of_date=None,
            provenance={
                "material_code": material_code,
                "physical_quantity": float(physical_qty),
                "committed_quantity": float(committed_qty)
            }
        )
