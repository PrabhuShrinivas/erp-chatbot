from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Any
from datetime import date
import uuid
from app.db.models.domain import Invoice, Payment
from app.metrics.base import ComputedFact

class OutstandingV1:
    async def execute(self, session: AsyncSession, party_id: uuid.UUID, as_of_date: date | None = None, **kwargs) -> ComputedFact:
        # outstanding: Invoice gross amount - payments allocated to invoices - unallocated customer advances
        
        # 1. Total invoices for the party
        inv_query = select(func.coalesce(func.sum(Invoice.gross_amount), 0)).where(Invoice.customer_id == party_id)
        if as_of_date:
            inv_query = inv_query.where(Invoice.invoice_date <= as_of_date)
        
        inv_result = await session.execute(inv_query)
        total_invoices = inv_result.scalar() or 0
        
        # 2. Total payments (allocated and unallocated) for the party
        pay_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.customer_id == party_id)
        if as_of_date:
            pay_query = pay_query.where(Payment.payment_date <= as_of_date)
            
        pay_result = await session.execute(pay_query)
        total_payments = pay_result.scalar() or 0
        
        # Note: In the absence of a credit_notes table, the exact outstanding is:
        # Invoices - Payments. (Unallocated advances are just payments without an invoice_id)
        # So we sum all payments.
        
        outstanding = float(total_invoices - total_payments)
        
        return ComputedFact(
            fact_id=str(uuid.uuid4()),
            metric="outstanding",
            metric_version="v1",
            value=outstanding,
            unit="amount",
            currency="INR",
            entity_id=party_id,
            as_of_date=as_of_date,
            provenance={
                "total_invoices": float(total_invoices),
                "total_payments": float(total_payments),
                "party_id": str(party_id),
                "date_filter": str(as_of_date) if as_of_date else None
            }
        )
