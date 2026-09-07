from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Any
from datetime import date, timedelta
from calendar import monthrange
import uuid
from app.db.models.domain import Invoice, Payment, Party
from app.metrics.base import ComputedFact

class OutstandingV1:
    async def execute(self, session: AsyncSession, party_id: uuid.UUID | None = None,
                      as_of_date: date | None = None, date_from: date | None = None,
                      group_by: str | None = None, **kwargs) -> ComputedFact | list[ComputedFact]:
        # outstanding: Invoice gross amount - payments made (date-filtered)

        def _apply_date_filter(query, date_col, df: date | None, dt: date | None):
            """Apply date_from (>=) and date_to / as_of_date (<=) filters to a column."""
            if df:
                query = query.where(date_col >= df)
            if dt:
                query = query.where(date_col <= dt)
            return query

        if group_by == "party":
            # 1. Total invoices grouped by party
            inv_query = select(Invoice.customer_id, Party.name,
                               func.coalesce(func.sum(Invoice.gross_amount), 0).label('total')
                               ).join(Party, Party.id == Invoice.customer_id)
            inv_query = _apply_date_filter(inv_query, Invoice.invoice_date, date_from, as_of_date)
            inv_query = inv_query.group_by(Invoice.customer_id, Party.name)
            inv_result = await session.execute(inv_query)

            name_map = {}
            inv_map = {}
            for row in inv_result.all():
                inv_map[row.customer_id] = float(row.total)
                name_map[row.customer_id] = row.name

            # 2. Total payments grouped by party
            pay_query = select(Payment.customer_id, Party.name,
                               func.coalesce(func.sum(Payment.amount), 0).label('total')
                               ).join(Party, Party.id == Payment.customer_id)
            pay_query = _apply_date_filter(pay_query, Payment.payment_date, date_from, as_of_date)
            pay_query = pay_query.group_by(Payment.customer_id, Party.name)
            pay_result = await session.execute(pay_query)

            pay_map = {}
            for row in pay_result.all():
                pay_map[row.customer_id] = float(row.total)
                name_map[row.customer_id] = row.name

            all_parties = set(inv_map.keys()).union(set(pay_map.keys()))
            facts = []
            for pid in all_parties:
                inv_total = inv_map.get(pid, 0.0)
                pay_total = pay_map.get(pid, 0.0)
                outstanding = inv_total - pay_total

                facts.append(ComputedFact(
                    fact_id=str(uuid.uuid4()),
                    metric="outstanding",
                    metric_version="v1",
                    value=outstanding,
                    unit="amount",
                    currency="INR",
                    entity_id=pid,
                    entity_name=name_map.get(pid, "Unknown"),
                    as_of_date=as_of_date,
                    provenance={
                        "total_invoices": inv_total,
                        "total_payments": pay_total,
                        "party_id": str(pid),
                        "date_from": str(date_from) if date_from else None,
                        "date_to": str(as_of_date) if as_of_date else None,
                        "group_by": "party"
                    }
                ))
            return facts

        elif group_by == "time":
            # Month-over-month: split the date range into monthly buckets
            # Requires either party_id (single entity) or works across all parties
            range_start = date_from or date.today().replace(day=1)
            range_end = as_of_date or date.today()

            # Build list of (month_start, month_end) tuples covering the range
            monthly_buckets = []
            cur = range_start.replace(day=1)
            while cur <= range_end:
                last_day = monthrange(cur.year, cur.month)[1]
                month_end = min(date(cur.year, cur.month, last_day), range_end)
                monthly_buckets.append((cur, month_end))
                # Advance to first of next month
                if cur.month == 12:
                    cur = date(cur.year + 1, 1, 1)
                else:
                    cur = date(cur.year, cur.month + 1, 1)

            facts = []
            for (m_start, m_end) in monthly_buckets:
                period_label = m_start.strftime("%b %Y")  # e.g. "Jun 2026"

                # Invoices in this month
                inv_q = select(func.coalesce(func.sum(Invoice.gross_amount), 0))
                if party_id:
                    inv_q = inv_q.where(Invoice.customer_id == party_id)
                inv_q = _apply_date_filter(inv_q, Invoice.invoice_date, m_start, m_end)
                inv_result = await session.execute(inv_q)
                m_invoices = float(inv_result.scalar() or 0)

                # Payments in this month
                pay_q = select(func.coalesce(func.sum(Payment.amount), 0))
                if party_id:
                    pay_q = pay_q.where(Payment.customer_id == party_id)
                pay_q = _apply_date_filter(pay_q, Payment.payment_date, m_start, m_end)
                pay_result = await session.execute(pay_q)
                m_payments = float(pay_result.scalar() or 0)

                outstanding = m_invoices - m_payments

                facts.append(ComputedFact(
                    fact_id=str(uuid.uuid4()),
                    metric="outstanding",
                    metric_version="v1",
                    value=outstanding,
                    unit="amount",
                    currency="INR",
                    entity_id=party_id,
                    entity_name=period_label,   # use period as the display label
                    as_of_date=m_end,
                    provenance={
                        "total_invoices": m_invoices,
                        "total_payments": m_payments,
                        "period": period_label,
                        "date_from": str(m_start),
                        "date_to": str(m_end),
                        "group_by": "time"
                    }
                ))
            return facts

        elif group_by == "all":
            # Aggregate total outstanding across ALL customers
            inv_query = select(func.coalesce(func.sum(Invoice.gross_amount), 0))
            inv_query = _apply_date_filter(inv_query, Invoice.invoice_date, date_from, as_of_date)
            inv_result = await session.execute(inv_query)
            total_invoices = inv_result.scalar() or 0

            pay_query = select(func.coalesce(func.sum(Payment.amount), 0))
            pay_query = _apply_date_filter(pay_query, Payment.payment_date, date_from, as_of_date)
            pay_result = await session.execute(pay_query)
            total_payments = pay_result.scalar() or 0

            outstanding = float(total_invoices - total_payments)

            return ComputedFact(
                fact_id=str(uuid.uuid4()),
                metric="outstanding",
                metric_version="v1",
                value=outstanding,
                unit="amount",
                currency="INR",
                entity_id=None,
                entity_name="All Customers",
                as_of_date=as_of_date,
                provenance={
                    "total_invoices": float(total_invoices),
                    "total_payments": float(total_payments),
                    "scope": "all_customers",
                    "date_from": str(date_from) if date_from else None,
                    "date_to": str(as_of_date) if as_of_date else None,
                }
            )

        else:
            if not party_id:
                raise ValueError("party_id is required if group_by is not 'party' or 'all'")

            # 0. Fetch party name for entity_name on the fact
            name_result = await session.execute(select(Party.name).where(Party.id == party_id))
            party_name = name_result.scalar() or str(party_id)

            # 1. Total invoices for the party
            inv_query = select(func.coalesce(func.sum(Invoice.gross_amount), 0)).where(
                Invoice.customer_id == party_id)
            inv_query = _apply_date_filter(inv_query, Invoice.invoice_date, date_from, as_of_date)
            inv_result = await session.execute(inv_query)
            total_invoices = inv_result.scalar() or 0

            # 2. Total payments for the party
            pay_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.customer_id == party_id)
            pay_query = _apply_date_filter(pay_query, Payment.payment_date, date_from, as_of_date)
            pay_result = await session.execute(pay_query)
            total_payments = pay_result.scalar() or 0

            outstanding = float(total_invoices - total_payments)

            return ComputedFact(
                fact_id=str(uuid.uuid4()),
                metric="outstanding",
                metric_version="v1",
                value=outstanding,
                unit="amount",
                currency="INR",
                entity_id=party_id,
                entity_name=party_name,
                as_of_date=as_of_date,
                provenance={
                    "total_invoices": float(total_invoices),
                    "total_payments": float(total_payments),
                    "party_id": str(party_id),
                    "date_from": str(date_from) if date_from else None,
                    "date_to": str(as_of_date) if as_of_date else None,
                }
            )



