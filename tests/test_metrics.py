import pytest
import uuid
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.models.domain import Party, Invoice, Payment, SalesOrder, SalesOrderItem, Inventory
from app.metrics.outstanding import OutstandingV1
from app.metrics.delivery import OnTimeDeliveryV1
from app.metrics.inventory import StockInHandV1

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    Session = async_sessionmaker(engine)
    async with Session() as sess:
        yield sess
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_outstanding_calculation(session):
    party_id = uuid.uuid4()
    session.add(Party(id=party_id, name="Test Party", party_type="customer"))
    session.add(Invoice(invoice_number="INV-1", customer_id=party_id, invoice_date=date(2023, 1, 1), gross_amount=1000.0, status="open"))
    session.add(Invoice(invoice_number="INV-2", customer_id=party_id, invoice_date=date(2023, 1, 5), gross_amount=500.0, status="open"))
    session.add(Payment(payment_number="PAY-1", customer_id=party_id, payment_date=date(2023, 1, 10), amount=200.0))
    await session.commit()
    
    executor = OutstandingV1()
    fact = await executor.execute(session, party_id=party_id)
    
    assert fact.value == 1300.0
    assert fact.metric == "outstanding"

@pytest.mark.asyncio
async def test_on_time_delivery(session):
    party_id = uuid.uuid4()
    session.add(Party(id=party_id, name="Test Party", party_type="customer"))
    
    # On time (actual <= promised)
    session.add(SalesOrder(order_number="SO-1", customer_id=party_id, order_date=date(2023, 1, 1), promised_delivery_date=date(2023, 1, 10), actual_delivery_date=date(2023, 1, 9), status="fulfilled", total_amount=100.0))
    
    # Late (actual > revised)
    session.add(SalesOrder(order_number="SO-2", customer_id=party_id, order_date=date(2023, 1, 1), promised_delivery_date=date(2023, 1, 10), revised_delivery_date=date(2023, 1, 12), actual_delivery_date=date(2023, 1, 15), status="fulfilled", total_amount=100.0))
    
    await session.commit()
    
    executor = OnTimeDeliveryV1()
    fact = await executor.execute(session, party_id=party_id)
    
    assert fact.value == 50.0  # 1 out of 2 fulfilled is on time

@pytest.mark.asyncio
async def test_stock_in_hand(session):
    session.add(Inventory(material_code="MAT-1", material_name="Iron", quantity_on_hand=500.0, unit="kg"))
    
    party_id = uuid.uuid4()
    session.add(Party(id=party_id, name="Test Party", party_type="customer"))
    
    so1 = SalesOrder(id=uuid.uuid4(), order_number="SO-1", customer_id=party_id, order_date=date(2023, 1, 1), status="open", total_amount=100.0)
    session.add(so1)
    
    session.add(SalesOrderItem(sales_order_id=so1.id, material_code="MAT-1", material_name="Iron", quantity=100.0, unit="kg", unit_price=1.0, line_amount=100.0, quantity_delivered=20.0))
    
    await session.commit()
    
    executor = StockInHandV1()
    fact = await executor.execute(session, material_code="MAT-1")
    
    # physical (500) - committed (100 - 20 = 80) = 420
    assert fact.value == 420.0
