from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
import uuid
from typing import Any
from datetime import date
from app.db.models.domain import SalesOrder, Party
from app.metrics.base import ComputedFact

class OnTimeDeliveryV1:
    async def execute(self, session: AsyncSession, party_id: uuid.UUID | None = None, as_of_date: date | None = None, **kwargs) -> ComputedFact | list[ComputedFact]:
        # on_time_delivery: actual_delivery_date <= coalesce(revised_delivery_date, promised_delivery_date)
        
        # Determine the target delivery date
        target_date = func.coalesce(SalesOrder.revised_delivery_date, SalesOrder.promised_delivery_date)
        
        # An order is considered "on time" if fulfilled and actual <= target_date
        is_on_time = case(
            (SalesOrder.actual_delivery_date <= target_date, 1),
            else_=0
        )
        
        group_by = kwargs.get("group_by")

        if group_by == "party":
            query = select(
                SalesOrder.customer_id,
                Party.name,
                func.count(SalesOrder.id).label("total_fulfilled"),
                func.sum(is_on_time).label("total_on_time")
            ).join(Party, Party.id == SalesOrder.customer_id).where(SalesOrder.status == 'fulfilled')

            if as_of_date:
                query = query.where(SalesOrder.order_date <= as_of_date)

            query = query.group_by(SalesOrder.customer_id, Party.name)
            result = await session.execute(query)

            facts = []
            for row in result.all():
                total_fulfilled = row.total_fulfilled or 0
                total_on_time = row.total_on_time or 0
                percentage = (float(total_on_time) / float(total_fulfilled) * 100.0) if total_fulfilled > 0 else 0.0

                facts.append(ComputedFact(
                    fact_id=str(uuid.uuid4()),
                    metric="on_time_delivery",
                    metric_version="v1",
                    value=percentage,
                    unit="percentage",
                    currency=None,
                    entity_id=row.customer_id,
                    entity_name=row.name,
                    as_of_date=as_of_date,
                    provenance={
                        "total_fulfilled": int(total_fulfilled),
                        "total_on_time": int(total_on_time),
                        "party_id": str(row.customer_id),
                        "date_to": str(as_of_date) if as_of_date else None,
                        "group_by": "party"
                    }
                ))
            return facts

        # Fallback to single calculation if not grouping by party
        # We'll calculate a percentage of on-time orders among all fulfilled orders
        query = select(
            func.count(SalesOrder.id).label("total_fulfilled"),
            func.sum(is_on_time).label("total_on_time")
        ).where(SalesOrder.status == 'fulfilled')
        
        if party_id:
            query = query.where(SalesOrder.customer_id == party_id)
            
        if as_of_date:
            query = query.where(SalesOrder.order_date <= as_of_date)
            
        result = await session.execute(query)
        row = result.first()

        total_fulfilled = row.total_fulfilled or 0
        total_on_time = row.total_on_time or 0

        percentage = (float(total_on_time) / float(total_fulfilled) * 100.0) if total_fulfilled > 0 else 0.0

        # Fetch party name so the renderer can display it
        party_name = None
        if party_id:
            name_result = await session.execute(select(Party.name).where(Party.id == party_id))
            party_name = name_result.scalar()

        return ComputedFact(
            fact_id=str(uuid.uuid4()),
            metric="on_time_delivery",
            metric_version="v1",
            value=percentage,
            unit="percentage",
            currency=None,
            entity_id=party_id,
            entity_name=party_name,
            as_of_date=as_of_date,
            provenance={
                "total_fulfilled": int(total_fulfilled),
                "total_on_time": int(total_on_time),
                "party_id": str(party_id) if party_id else None,
                "date_to": str(as_of_date) if as_of_date else None,
            }
        )
